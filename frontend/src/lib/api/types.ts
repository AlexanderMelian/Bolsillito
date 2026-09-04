export type AccountType = 'bank' | 'cash' | 'wallet' | 'investment'
export type CardType = 'debit' | 'credit'

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
