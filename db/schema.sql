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

CREATE TABLE accounts (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(80) NOT NULL,
    type          account_type NOT NULL,
    currency      CHAR(3) NOT NULL DEFAULT 'ARS',
    balance       NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    is_archived   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cards (
    id                  SERIAL PRIMARY KEY,
    account_id          INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    payment_account_id  INTEGER REFERENCES accounts(id),
    name                VARCHAR(80) NOT NULL,
    type                card_type NOT NULL,
    credit_limit        NUMERIC(12, 2),
    closing_day         SMALLINT,
    payment_day         SMALLINT,
    CONSTRAINT ck_card_closing_day CHECK (closing_day IS NULL OR closing_day BETWEEN 1 AND 31),
    CONSTRAINT ck_card_payment_day CHECK (payment_day IS NULL OR payment_day BETWEEN 1 AND 31),
    CONSTRAINT ck_credit_card_needs_cycle CHECK (
        type = 'debit' OR (closing_day IS NOT NULL AND payment_day IS NOT NULL)
    )
);

CREATE TABLE categories (
    id      SERIAL PRIMARY KEY,
    name    VARCHAR(50) NOT NULL UNIQUE,
    icon    VARCHAR(50),
    kind    category_kind NOT NULL
);

CREATE TABLE installment_plans (
    id                  SERIAL PRIMARY KEY,
    card_id             INTEGER NOT NULL REFERENCES cards(id),
    category_id         INTEGER REFERENCES categories(id),
    description         VARCHAR(255) NOT NULL,
    purchase_date       DATE NOT NULL,
    total_amount        NUMERIC(12, 2) NOT NULL,
    total_installments  INTEGER NOT NULL,
    CONSTRAINT ck_plan_installments_positive CHECK (total_installments > 0),
    CONSTRAINT ck_plan_amount_positive CHECK (total_amount > 0)
);

CREATE TABLE card_statements (
    id                      SERIAL PRIMARY KEY,
    card_id                 INTEGER NOT NULL REFERENCES cards(id),
    closing_date            DATE NOT NULL,
    payment_due_date        DATE NOT NULL,
    status                  statement_status NOT NULL DEFAULT 'open',
    total_amount            NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    payment_transaction_id  INTEGER, -- FK agregada luego de crear `transactions` (ver abajo)
    CONSTRAINT uq_card_statement_period UNIQUE (card_id, closing_date)
);

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
    type                     transaction_type NOT NULL,
    account_id               INTEGER NOT NULL REFERENCES accounts(id),
    destination_account_id   INTEGER REFERENCES accounts(id),
    card_id                  INTEGER REFERENCES cards(id),
    category_id              INTEGER REFERENCES categories(id),
    installment_plan_id      INTEGER REFERENCES installment_plans(id),
    amount                   NUMERIC(12, 2) NOT NULL,
    currency                 CHAR(3) NOT NULL DEFAULT 'ARS',
    date                     DATE NOT NULL,
    description              VARCHAR(255),
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_transaction_amount_positive CHECK (amount > 0),
    CONSTRAINT ck_transfer_needs_destination CHECK (
        type <> 'transfer' OR (destination_account_id IS NOT NULL AND destination_account_id <> account_id)
    )
);

ALTER TABLE card_statements
    ADD CONSTRAINT fk_statement_payment_transaction
    FOREIGN KEY (payment_transaction_id) REFERENCES transactions(id);

CREATE TABLE assets (
    id        SERIAL PRIMARY KEY,
    ticker    VARCHAR(20) NOT NULL,
    name      VARCHAR(120) NOT NULL,
    type      asset_type NOT NULL,
    currency  CHAR(3) NOT NULL DEFAULT 'USD',
    CONSTRAINT uq_asset_ticker_type UNIQUE (ticker, type)
);

CREATE TABLE investment_transactions (
    id          SERIAL PRIMARY KEY,
    asset_id    INTEGER NOT NULL REFERENCES assets(id),
    account_id  INTEGER REFERENCES accounts(id),
    type        investment_tx_type NOT NULL,
    quantity    NUMERIC(20, 8) NOT NULL,
    price       NUMERIC(20, 8) NOT NULL,
    fee         NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    date        DATE NOT NULL,
    CONSTRAINT ck_inv_qty_positive CHECK (quantity > 0)
);

CREATE TABLE exchange_rates (
    id             SERIAL PRIMARY KEY,
    from_currency  CHAR(3) NOT NULL,
    to_currency    CHAR(3) NOT NULL,
    rate           NUMERIC(18, 6) NOT NULL,
    date           DATE NOT NULL,
    CONSTRAINT uq_fx_rate_day UNIQUE (from_currency, to_currency, date)
);

-- Índices de consulta frecuente
CREATE INDEX ix_transactions_date ON transactions (date);
CREATE INDEX ix_transactions_account_date ON transactions (account_id, date);
CREATE INDEX ix_installment_items_statement ON installment_items (statement_id);
CREATE INDEX ix_card_statements_card_status ON card_statements (card_id, status);
CREATE INDEX ix_investment_tx_asset_date ON investment_transactions (asset_id, date);
