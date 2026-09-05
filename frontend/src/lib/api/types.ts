export interface UserRead {
  id: number
  username: string
}

export interface Token {
  access_token: string
  token_type: string
  user: UserRead
}

export interface RegisterInput {
  username: string
  password: string
}

export interface LoginInput {
  username: string
  password: string
}

export type AccountType = 'bank' | 'cash' | 'wallet' | 'investment'
export type CardType = 'debit' | 'credit'
export type TransactionType = 'income' | 'expense' | 'transfer'
export type StatementStatus = 'open' | 'closed' | 'paid'

export interface Account {
  id: number
  name: string
  type: AccountType
  currency: string
  balance: string
  is_archived: boolean
}

export interface AccountCreateInput {
  name: string
  type: AccountType
  currency?: string
  balance?: string
}

export interface AccountUpdateInput {
  name?: string
  type?: AccountType
  currency?: string
  balance?: string
}

export interface Card {
  id: number
  account_id: number
  payment_account_id: number | null
  name: string
  type: CardType
  credit_limit: string | null
  closing_day: number | null
  payment_day: number | null
}

export interface CardCreateInput {
  account_id: number
  payment_account_id?: number | null
  name: string
  type: CardType
  credit_limit?: string | null
  closing_day?: number | null
  payment_day?: number | null
}

export interface Category {
  id: number
  name: string
  kind: TransactionType
  icon: string | null
}

export interface CategoryCreateInput {
  name: string
  kind: TransactionType
  icon?: string | null
}

export interface Transaction {
  id: number
  type: TransactionType
  // null: instancia generada por un RecurringExpense sin cuenta asociada.
  account_id: number | null
  destination_account_id: number | null
  card_id: number | null
  category_id: number | null
  installment_plan_id: number | null
  recurring_expense_id: number | null
  amount: string
  currency: string
  date: string
  description: string | null
}

export interface TransactionCreateInput {
  type: TransactionType
  account_id: number
  destination_account_id?: number | null
  card_id?: number | null
  category_id?: number | null
  amount: string
  currency?: string
  date: string
  description?: string | null
}

export interface RecurringExpense {
  id: number
  account_id: number | null
  category_id: number | null
  description: string
  amount: string
  currency: string
  day_of_month: number
  start_date: string
  last_generated_on: string | null
  is_active: boolean
}

export interface RecurringExpenseCreateInput {
  account_id?: number | null
  category_id?: number | null
  description: string
  amount: string
  currency?: string
  day_of_month: number
  start_date: string
}

export interface RecurringExpenseUpdateInput {
  account_id?: number | null
  category_id?: number | null
  description?: string
  amount?: string
  day_of_month?: number
  is_active?: boolean
}

export interface RecurringExpenseSyncResult {
  generated_count: number
}

export interface InstallmentItem {
  number: number
  amount: string
  statement_id: number | null
}

export interface InstallmentPlan {
  id: number
  card_id: number
  category_id: number | null
  description: string
  purchase_date: string
  total_amount: string
  total_installments: number
  items: InstallmentItem[]
}

export interface InstallmentPlanCreateInput {
  card_id: number
  category_id?: number | null
  description: string
  purchase_date: string
  total_amount: string
  total_installments: number
}

export interface CardStatement {
  id: number
  card_id: number
  closing_date: string
  payment_due_date: string
  status: StatementStatus
  total_amount: string
  payment_transaction_id: number | null
}

export interface ExchangeRate {
  id: number
  from_currency: string
  to_currency: string
  rate: string
  date: string
}

export interface ExchangeRateCreateInput {
  from_currency: string
  to_currency: string
  rate: string
  date: string
}

export interface UnconvertedAmount {
  currency: string
  amount: string
}

export interface DashboardSummary {
  reference_currency: string
  month: string
  total_balance: string
  month_income: string
  month_expenses: string
  unconverted_balances: UnconvertedAmount[]
}

export interface CategorySpending {
  category_id: number | null
  category_name: string
  icon: string | null
  total: string
}

export interface CashFlowMonth {
  month: string
  committed_amount: string
}

export interface CashFlowProjection {
  reference_currency: string
  projection: CashFlowMonth[]
}

export type AssetType = 'stock' | 'bond' | 'crypto' | 'fund' | 'other'
export type InvestmentTxType = 'buy' | 'sell' | 'dividend'

export interface Asset {
  id: number
  ticker: string
  name: string
  type: AssetType
  currency: string
}

export interface AssetCreateInput {
  ticker: string
  name: string
  type: AssetType
  currency?: string
}

export interface InvestmentTransaction {
  id: number
  asset_id: number
  account_id: number | null
  type: InvestmentTxType
  quantity: string
  price: string
  fee: string
  date: string
}

export interface InvestmentTransactionCreateInput {
  asset_id: number
  account_id?: number | null
  type: InvestmentTxType
  quantity: string
  price: string
  fee?: string
  date: string
}

export interface AssetPosition {
  asset_id: number
  ticker: string
  name: string
  type: AssetType
  currency: string
  quantity: string
  avg_cost: string
  total_cost: string
  realized_gain: string
}

export interface Portfolio {
  reference_currency: string
  total_cost: string
  total_realized_gain: string
  unconverted: UnconvertedAmount[]
  positions: AssetPosition[]
}
