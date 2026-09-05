"""Modelos SQLAlchemy 2.0 de Bolsillito.

Referencia de diseño: docs/architecture.md y db/schema.sql. Este archivo se usa como base
para la primera migración de Alembic en Fase 1 — no se ejecuta código de negocio todavía.
"""

import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String,
    UniqueConstraint, func,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def pg_enum(enum_cls: type[enum.Enum], name: str) -> SQLEnum:
    """SQLEnum que persiste el `.value` del enum (ej. "debit") en vez del `.name`
    (ej. "DEBIT", el default de SQLAlchemy) -- así el tipo Postgres queda alineado con los
    `CheckConstraint` en minúscula usados en este archivo y en db/schema.sql."""
    return SQLEnum(enum_cls, name=name, values_callable=lambda obj: [e.value for e in obj])


class AccountType(str, enum.Enum):
    BANK = "bank"
    CASH = "cash"
    WALLET = "wallet"          # billetera virtual (Mercado Pago, etc.)
    INVESTMENT = "investment"  # cuenta comitente / broker (opcional)


class CardType(str, enum.Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class TransactionType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class StatementStatus(str, enum.Enum):
    OPEN = "open"      # ciclo actual, todavía acumulando gastos
    CLOSED = "closed"  # cerrado, pendiente de pago
    PAID = "paid"


class AssetType(str, enum.Enum):
    STOCK = "stock"
    BOND = "bond"
    CRYPTO = "crypto"
    FUND = "fund"
    OTHER = "other"


class InvestmentTxType(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    type: Mapped[AccountType] = mapped_column(pg_enum(AccountType, name="account_type"))
    currency: Mapped[str] = mapped_column(String(3), default="ARS")  # ISO 4217
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    is_archived: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Hora del evento en el dispositivo que lo originó, no de inserción en el servidor -- ver
    # nota de "timestamp vs. created_at" en docs/architecture.md. Hoy siempre coincide con
    # created_at (todo se crea online, vía este mismo servidor); cuando exista un cliente móvil
    # offline-first, éste la setea con el reloj local al momento de la carga, y la sincronización
    # ordena por esta columna para preservar el orden real en que el usuario cargó los datos.
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # passive_deletes=True: al borrar la cuenta, dejamos que Postgres borre las tarjetas vía
    # el ON DELETE CASCADE de la FK (más abajo) en vez de que el ORM intente poner
    # account_id=NULL primero (lo cual violaría la constraint NOT NULL de esa columna).
    cards: Mapped[list["Card"]] = relationship(
        back_populates="account", foreign_keys="Card.account_id", passive_deletes=True
    )


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"))
    # Para tarjetas de crédito: cuenta desde la que se paga el resumen (normalmente == account_id,
    # pero se separa por si el usuario paga la tarjeta desde otra cuenta).
    payment_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(80))
    type: Mapped[CardType] = mapped_column(pg_enum(CardType, name="card_type"))
    credit_limit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    closing_day: Mapped[int | None] = mapped_column(nullable=True)  # 1-31, solo crédito
    payment_day: Mapped[int | None] = mapped_column(nullable=True)  # 1-31, solo crédito
    # Hora del evento en el dispositivo, no de inserción en el servidor -- ver Account.timestamp.
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    account: Mapped["Account"] = relationship(
        back_populates="cards", foreign_keys=[account_id]
    )
    payment_account: Mapped["Account | None"] = relationship(foreign_keys=[payment_account_id])

    __table_args__ = (
        CheckConstraint(
            "closing_day IS NULL OR closing_day BETWEEN 1 AND 31", name="ck_card_closing_day"
        ),
        CheckConstraint(
            "payment_day IS NULL OR payment_day BETWEEN 1 AND 31", name="ck_card_payment_day"
        ),
        CheckConstraint(
            "type = 'debit' OR (closing_day IS NOT NULL AND payment_day IS NOT NULL)",
            name="ck_credit_card_needs_cycle",
        ),
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(50))
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    kind: Mapped[TransactionType] = mapped_column(pg_enum(TransactionType, name="category_kind"))
    # Hora del evento en el dispositivo, no de inserción en el servidor -- ver Account.timestamp.
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_category_user_name"),)


class RecurringExpense(Base):
    """Plantilla de un gasto fijo mensual (alquiler, internet, etc.). No tiene fecha de fin --
    `services/recurring_expenses.py` genera una Transaction por cada período vencido cada vez
    que se sincroniza (no hay scheduler/cron en esta app), y avanza `last_generated_on` para no
    volver a generar (ni "resucitar" tras un borrado) un período ya cubierto."""

    __tablename__ = "recurring_expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # Nullable a propósito: un gasto fijo puede cargarse sin cuenta para el usuario al que solo
    # le importa el total de ingresos/egresos, sin llevar detalle de billetera/banco -- en ese
    # caso no afecta ningún saldo (ver services/balances.py::apply_transaction_balance_effect).
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    description: Mapped[str] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="ARS")
    day_of_month: Mapped[int] = mapped_column()  # 1-31, recortado a fin de mes si no existe
    start_date: Mapped[date] = mapped_column(Date)
    last_generated_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Hora del evento en el dispositivo, no de inserción en el servidor -- ver Account.timestamp.
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    __table_args__ = (
        CheckConstraint("day_of_month BETWEEN 1 AND 31", name="ck_recurring_expense_day"),
        CheckConstraint("amount > 0", name="ck_recurring_expense_amount_positive"),
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[TransactionType] = mapped_column(
        pg_enum(TransactionType, name="transaction_type")
    )
    # Nullable solo para instancias generadas por un RecurringExpense sin cuenta -- la carga
    # manual (schemas.TransactionCreate) sigue exigiendo account_id, esto no cambia eso.
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    destination_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id"), nullable=True
    )
    card_id: Mapped[int | None] = mapped_column(ForeignKey("cards.id"), nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    installment_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("installment_plans.id"), nullable=True
    )
    investment_transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("investment_transactions.id"), nullable=True
    )
    recurring_expense_id: Mapped[int | None] = mapped_column(
        ForeignKey("recurring_expenses.id", ondelete="SET NULL"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))  # siempre positivo; el signo lo da `type`
    currency: Mapped[str] = mapped_column(String(3), default="ARS")
    date: Mapped[date] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Hora del evento en el dispositivo, no de inserción en el servidor -- ver Account.timestamp.
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_transaction_amount_positive"),
        CheckConstraint(
            "(type != 'transfer') OR "
            "(destination_account_id IS NOT NULL AND destination_account_id != account_id)",
            name="ck_transfer_needs_destination",
        ),
        # Múltiples NULL no chocan entre sí en Postgres -- no afecta transacciones normales
        # (recurring_expense_id IS NULL), solo evita generar dos veces el mismo período.
        UniqueConstraint(
            "recurring_expense_id", "date", name="uq_recurring_expense_period"
        ),
        Index("ix_transactions_date", "date"),
        Index("ix_transactions_account_date", "account_id", "date"),
    )


class InstallmentPlan(Base):
    """Cabecera de una compra en cuotas (la 'compra madre')."""

    __tablename__ = "installment_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    description: Mapped[str] = mapped_column(String(255))
    purchase_date: Mapped[date] = mapped_column(Date)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total_installments: Mapped[int] = mapped_column()
    # Hora del evento en el dispositivo, no de inserción en el servidor -- ver Account.timestamp.
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # passive_deletes=True: mismo motivo que Account.cards -- delega el borrado en cascada al
    # ON DELETE CASCADE de installment_items.plan_id en vez de que el ORM intente nullearla.
    items: Mapped[list["InstallmentItem"]] = relationship(
        back_populates="plan", order_by="InstallmentItem.number", passive_deletes=True
    )

    __table_args__ = (
        CheckConstraint("total_installments > 0", name="ck_plan_installments_positive"),
        CheckConstraint("total_amount > 0", name="ck_plan_amount_positive"),
    )


class InstallmentItem(Base):
    """Una cuota individual (1/N, 2/N, ...), asignada a un resumen (CardStatement)."""

    __tablename__ = "installment_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("installment_plans.id", ondelete="CASCADE"))
    statement_id: Mapped[int | None] = mapped_column(
        ForeignKey("card_statements.id"), nullable=True
    )
    number: Mapped[int] = mapped_column()  # 1..N
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    plan: Mapped["InstallmentPlan"] = relationship(back_populates="items")
    statement: Mapped["CardStatement | None"] = relationship(back_populates="items")

    __table_args__ = (
        UniqueConstraint("plan_id", "number", name="uq_plan_installment_number"),
    )


class CardStatement(Base):
    """Un ciclo de facturación / resumen mensual de una tarjeta de crédito."""

    __tablename__ = "card_statements"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"))
    closing_date: Mapped[date] = mapped_column(Date)
    payment_due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[StatementStatus] = mapped_column(
        pg_enum(StatementStatus, name="statement_status"), default=StatementStatus.OPEN
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    # Se completa cuando el usuario registra el pago del resumen.
    payment_transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id"), nullable=True
    )

    items: Mapped[list["InstallmentItem"]] = relationship(back_populates="statement")

    __table_args__ = (
        UniqueConstraint("card_id", "closing_date", name="uq_card_statement_period"),
    )


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    ticker: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(120))
    type: Mapped[AssetType] = mapped_column(pg_enum(AssetType, name="asset_type"))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    # Hora del evento en el dispositivo, no de inserción en el servidor -- ver Account.timestamp.
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    __table_args__ = (
        UniqueConstraint("user_id", "ticker", "type", name="uq_asset_user_ticker_type"),
    )


class InvestmentTransaction(Base):
    """Movimientos de compra/venta; el precio promedio se calcula a partir de estos, no se
    guarda como campo fijo (evita que quede desincronizado)."""

    __tablename__ = "investment_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    type: Mapped[InvestmentTxType] = mapped_column(
        pg_enum(InvestmentTxType, name="investment_tx_type")
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    price: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    date: Mapped[date] = mapped_column(Date)
    # Hora del evento en el dispositivo, no de inserción en el servidor -- ver Account.timestamp.
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    __table_args__ = (CheckConstraint("quantity > 0", name="ck_inv_qty_positive"),)


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id: Mapped[int] = mapped_column(primary_key=True)
    from_currency: Mapped[str] = mapped_column(String(3))
    to_currency: Mapped[str] = mapped_column(String(3))
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    date: Mapped[date] = mapped_column(Date)
    # Hora del evento en el dispositivo, no de inserción en el servidor -- ver Account.timestamp.
    # Además de la carga móvil offline, sirve para desempatar un upsert concurrente: si dos
    # dispositivos cargan (o corrigen) la cotización del mismo día mientras ambos están
    # offline, al sincronizar gana la que tenga el `timestamp` más reciente.
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    __table_args__ = (
        UniqueConstraint("from_currency", "to_currency", "date", name="uq_fx_rate_day"),
    )
