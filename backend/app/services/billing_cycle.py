"""Lógica de ciclos de facturación y generación de cuotas de tarjetas de crédito.

Ver docs/architecture.md → sección "Ciclos de facturación y cuotas" para el razonamiento
completo y ejemplos. Este módulo no depende de la sesión de DB: recibe y devuelve objetos de
dominio para que sea fácilmente testeable con pytest.
"""

import calendar
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal


def _safe_day(year: int, month: int, day: int) -> int:
    """Recorta `day` al último día real del mes (ej. 31 en febrero -> 28 o 29)."""
    last_day_of_month = calendar.monthrange(year, month)[1]
    return min(day, last_day_of_month)


def get_statement_closing_date(purchase_date: date, closing_day: int) -> date:
    """Determina a qué ciclo (fecha de cierre) pertenece una compra.

    Regla: si el día de la compra es <= closing_day, pertenece al ciclo que cierra ese mismo
    mes; si no, pertenece al ciclo que cierra el mes siguiente.
    """
    year, month = purchase_date.year, purchase_date.month
    if purchase_date.day > closing_day:
        month += 1
        if month > 12:
            month, year = 1, year + 1
    return date(year, month, _safe_day(year, month, closing_day))


def get_payment_due_date(closing_date: date, payment_day: int) -> date:
    """Determina la fecha de vencimiento de pago de un resumen ya cerrado."""
    year, month = closing_date.year, closing_date.month
    # Si el día de pago cae "antes" del día de cierre dentro del mes, el vencimiento
    # es al mes siguiente del cierre (caso típico: cierra el 15, paga el 5).
    if payment_day <= closing_date.day:
        month += 1
        if month > 12:
            month, year = 1, year + 1
    return date(year, month, _safe_day(year, month, payment_day))


def build_installment_amounts(total_amount: Decimal, total_installments: int) -> list[Decimal]:
    """Divide `total_amount` en `total_installments` cuotas de igual monto, ajustando el
    residuo de redondeo en la última cuota para que la suma sea exacta."""
    base = (total_amount / total_installments).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    remainder = total_amount - base * total_installments
    amounts = [base] * total_installments
    amounts[-1] += remainder
    return amounts


def build_installment_closing_dates(
    purchase_date: date, closing_day: int, total_installments: int
) -> list[date]:
    """Devuelve, en orden, la fecha de cierre del ciclo al que pertenece cada cuota
    (cuota 1 -> ciclo de la compra, cuota 2 -> ciclo siguiente, etc.)."""
    dates = []
    closing = get_statement_closing_date(purchase_date, closing_day)
    for _ in range(total_installments):
        dates.append(closing)
        closing = get_statement_closing_date(closing + timedelta(days=1), closing_day)
    return dates
