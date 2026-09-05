-- Bolsillito — Esquema de base de datos (PostgreSQL)
-- Generado a partir del modelo SQLAlchemy 2.0 documentado en docs/architecture.md.
-- Este script es de referencia/lectura; las migraciones reales se gestionan con Alembic
-- (backend/migrations) a partir de Fase 1.

CREATE TYPE account_type AS ENUM ('bank', 'cash', 'wallet', 'investment');
CREATE TYPE card_type AS ENUM ('debit', 'credit');
CREATE TYPE transaction_type AS ENUM ('income', 'expense', 'transfer');
CREATE TYPE statement_status AS ENUM ('open', 'closed', 'paid');
CREATE TYPE category_kind AS ENUM ('income', 'expense', 'transfer');
CREATE TYPE asset_type AS ENUM ('stock', 'bond', 'crypto', 'fund', 'other');
CREATE TYPE investment_tx_type AS ENUM ('buy', 'sell', 'dividend');

CREATE TABLE users (
    id                SERIAL PRIMARY KEY,
    username          VARCHAR(50) NOT NULL UNIQUE,
    hashed_password   VARCHAR(255) NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Multi-tenant: casi todo lo demás cuelga de un usuario. `exchange_rates` es la única
-- excepción a propósito -- una cotización de mercado no es información personal, se comparte
-- entre todos los usuarios (ver agents.md § Decisiones de negocio).

CREATE TABLE accounts (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id),
    name          VARCHAR(80) NOT NULL,
    type          account_type NOT NULL,
    currency      CHAR(3) NOT NULL DEFAULT 'ARS',
    balance       NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    is_archived   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Hora del evento en el dispositivo, no de inserción en el servidor -- reservada para
    -- cuando exista un cliente móvil offline-first, que sincroniza ordenando por esta columna.
    timestamp     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_accounts_user_id ON accounts (user_id);
CREATE INDEX ix_accounts_timestamp ON accounts (timestamp);

CREATE TABLE cards (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER NOT NULL REFERENCES users(id),
    account_id          INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    payment_account_id  INTEGER REFERENCES accounts(id),
    name                VARCHAR(80) NOT NULL,
    type                card_type NOT NULL,
    credit_limit        NUMERIC(12, 2),
    closing_day         SMALLINT,
    payment_day         SMALLINT,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT now(), -- ver nota en accounts.timestamp
    CONSTRAINT ck_card_closing_day CHECK (closing_day IS NULL OR closing_day BETWEEN 1 AND 31),
    CONSTRAINT ck_card_payment_day CHECK (payment_day IS NULL OR payment_day BETWEEN 1 AND 31),
    CONSTRAINT ck_credit_card_needs_cycle CHECK (
        type = 'debit' OR (closing_day IS NOT NULL AND payment_day IS NOT NULL)
    )
);
CREATE INDEX ix_cards_user_id ON cards (user_id);
CREATE INDEX ix_cards_timestamp ON cards (timestamp);

CREATE TABLE categories (
    id       SERIAL PRIMARY KEY,
    user_id  INTEGER NOT NULL REFERENCES users(id),
    name     VARCHAR(50) NOT NULL,
    icon     VARCHAR(50),
    kind     category_kind NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(), -- ver nota en accounts.timestamp
    CONSTRAINT uq_category_user_name UNIQUE (user_id, name)
);
CREATE INDEX ix_categories_user_id ON categories (user_id);
CREATE INDEX ix_categories_timestamp ON categories (timestamp);

CREATE TABLE installment_plans (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER NOT NULL REFERENCES users(id),
    card_id             INTEGER NOT NULL REFERENCES cards(id),
    category_id         INTEGER REFERENCES categories(id),
    description         VARCHAR(255) NOT NULL,
    purchase_date       DATE NOT NULL,
    total_amount        NUMERIC(12, 2) NOT NULL,
    total_installments  INTEGER NOT NULL,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT now(), -- ver nota en accounts.timestamp
    CONSTRAINT ck_plan_installments_positive CHECK (total_installments > 0),
    CONSTRAINT ck_plan_amount_positive CHECK (total_amount > 0)
);
CREATE INDEX ix_installment_plans_user_id ON installment_plans (user_id);
CREATE INDEX ix_installment_plans_timestamp ON installment_plans (timestamp);

-- Plantilla de un gasto fijo mensual (alquiler, internet, etc.), sin fecha de fin. No hay
-- scheduler en esta app: `POST /recurring-expenses/sync` genera los movimientos vencidos de
-- forma perezosa cada vez que el frontend carga, usando `last_generated_on` (no un exists-check
-- contra `transactions`) para no "resucitar" un período cuya transacción se borró a mano.
CREATE TABLE recurring_expenses (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER NOT NULL REFERENCES users(id),
    account_id          INTEGER REFERENCES accounts(id), -- NULL: gasto fijo sin cuenta, no afecta saldos
    category_id         INTEGER REFERENCES categories(id),
    description         VARCHAR(255) NOT NULL,
    amount              NUMERIC(12, 2) NOT NULL,
    currency            CHAR(3) NOT NULL DEFAULT 'ARS',
    day_of_month        INTEGER NOT NULL,
    start_date          DATE NOT NULL,
    last_generated_on   DATE,
    is_active           BOOLEAN NOT NULL DEFAULT true,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT now(), -- ver nota en accounts.timestamp
    CONSTRAINT ck_recurring_expense_day CHECK (day_of_month BETWEEN 1 AND 31),
    CONSTRAINT ck_recurring_expense_amount_positive CHECK (amount > 0)
);
CREATE INDEX ix_recurring_expenses_user_id ON recurring_expenses (user_id);
CREATE INDEX ix_recurring_expenses_timestamp ON recurring_expenses (timestamp);

CREATE TABLE card_statements (
    id                      SERIAL PRIMARY KEY,
    user_id                 INTEGER NOT NULL REFERENCES users(id),
    card_id                 INTEGER NOT NULL REFERENCES cards(id),
    closing_date            DATE NOT NULL,
    payment_due_date        DATE NOT NULL,
    status                  statement_status NOT NULL DEFAULT 'open',
    total_amount            NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    payment_transaction_id  INTEGER, -- FK agregada luego de crear `transactions` (ver abajo)
    CONSTRAINT uq_card_statement_period UNIQUE (card_id, closing_date)
);
CREATE INDEX ix_card_statements_user_id ON card_statements (user_id);

CREATE TABLE installment_items (
    id             SERIAL PRIMARY KEY,
    plan_id        INTEGER NOT NULL REFERENCES installment_plans(id) ON DELETE CASCADE,
    statement_id   INTEGER REFERENCES card_statements(id),
    number         INTEGER NOT NULL,
    amount         NUMERIC(12, 2) NOT NULL,
    CONSTRAINT uq_plan_installment_number UNIQUE (plan_id, number)
);

CREATE TABLE transactions (
    id                       SERIAL PRIMARY KEY,
    user_id                  INTEGER NOT NULL REFERENCES users(id),
    type                     transaction_type NOT NULL,
    account_id               INTEGER REFERENCES accounts(id), -- NULL: instancia de un gasto fijo sin cuenta
    destination_account_id   INTEGER REFERENCES accounts(id),
    card_id                  INTEGER REFERENCES cards(id),
    category_id              INTEGER REFERENCES categories(id),
    installment_plan_id      INTEGER REFERENCES installment_plans(id),
    investment_transaction_id INTEGER, -- FK agregada luego de crear `investment_transactions` (ver abajo)
    recurring_expense_id     INTEGER REFERENCES recurring_expenses(id) ON DELETE SET NULL,
    amount                   NUMERIC(12, 2) NOT NULL,
    currency                 CHAR(3) NOT NULL DEFAULT 'ARS',
    date                     DATE NOT NULL,
    description              VARCHAR(255),
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    timestamp                TIMESTAMPTZ NOT NULL DEFAULT now(), -- ver nota en accounts.timestamp
    CONSTRAINT ck_transaction_amount_positive CHECK (amount > 0),
    CONSTRAINT ck_transfer_needs_destination CHECK (
        type <> 'transfer' OR (destination_account_id IS NOT NULL AND destination_account_id <> account_id)
    ),
    -- NULL no choca contra NULL en Postgres -- no afecta transacciones normales, solo evita
    -- generar dos veces el mismo período de un mismo gasto fijo.
    CONSTRAINT uq_recurring_expense_period UNIQUE (recurring_expense_id, date)
);
CREATE INDEX ix_transactions_user_id ON transactions (user_id);
CREATE INDEX ix_transactions_timestamp ON transactions (timestamp);

ALTER TABLE card_statements
    ADD CONSTRAINT fk_statement_payment_transaction
    FOREIGN KEY (payment_transaction_id) REFERENCES transactions(id);

CREATE TABLE assets (
    id        SERIAL PRIMARY KEY,
    user_id   INTEGER NOT NULL REFERENCES users(id),
    ticker    VARCHAR(20) NOT NULL,
    name      VARCHAR(120) NOT NULL,
    type      asset_type NOT NULL,
    currency  CHAR(3) NOT NULL DEFAULT 'USD',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(), -- ver nota en accounts.timestamp
    CONSTRAINT uq_asset_user_ticker_type UNIQUE (user_id, ticker, type)
);
CREATE INDEX ix_assets_user_id ON assets (user_id);
CREATE INDEX ix_assets_timestamp ON assets (timestamp);

CREATE TABLE investment_transactions (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    asset_id    INTEGER NOT NULL REFERENCES assets(id),
    account_id  INTEGER REFERENCES accounts(id),
    type        investment_tx_type NOT NULL,
    quantity    NUMERIC(20, 8) NOT NULL,
    price       NUMERIC(20, 8) NOT NULL,
    fee         NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    date        DATE NOT NULL,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT now(), -- ver nota en accounts.timestamp
    CONSTRAINT ck_inv_qty_positive CHECK (quantity > 0)
);
CREATE INDEX ix_investment_transactions_user_id ON investment_transactions (user_id);
CREATE INDEX ix_investment_transactions_timestamp ON investment_transactions (timestamp);

ALTER TABLE transactions
    ADD CONSTRAINT transactions_investment_transaction_id_fkey
    FOREIGN KEY (investment_transaction_id) REFERENCES investment_transactions(id);

-- Sin user_id: una cotización de mercado es un dato compartido, no personal (ver arriba).
CREATE TABLE exchange_rates (
    id             SERIAL PRIMARY KEY,
    from_currency  CHAR(3) NOT NULL,
    to_currency    CHAR(3) NOT NULL,
    rate           NUMERIC(18, 6) NOT NULL,
    date           DATE NOT NULL,
    -- Ver nota en accounts.timestamp. Además, desempata un upsert concurrente offline: si dos
    -- dispositivos cargan la cotización del mismo día mientras ambos están sin conexión, al
    -- sincronizar gana la que tenga el timestamp más reciente.
    timestamp      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_fx_rate_day UNIQUE (from_currency, to_currency, date)
);
CREATE INDEX ix_exchange_rates_timestamp ON exchange_rates (timestamp);

-- Índices de consulta frecuente
CREATE INDEX ix_transactions_date ON transactions (date);
CREATE INDEX ix_transactions_account_date ON transactions (account_id, date);
CREATE INDEX ix_installment_items_statement ON installment_items (statement_id);
CREATE INDEX ix_card_statements_card_status ON card_statements (card_id, status);
CREATE INDEX ix_investment_tx_asset_date ON investment_transactions (asset_id, date);
