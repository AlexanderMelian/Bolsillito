import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiRequest } from '@/lib/api/client'
import type { Transaction, TransactionCreateInput } from '@/lib/api/types'

const transactionsKey = ['transactions'] as const
// Un movimiento nuevo puede afectar el saldo de una o dos cuentas y (si es a crédito) el
// resumen de una tarjeta -- más simple invalidar todo lo relacionado que rastrear cada caso.
const affectedKeys = [transactionsKey, ['accounts'], ['cards']] as const

export interface TransactionFilters {
  account_id?: number
  category_id?: number
  type?: Transaction['type']
  date_from?: string
  date_to?: string
}

function toQueryString(filters: TransactionFilters): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined) params.set(key, String(value))
  }
  const query = params.toString()
  return query ? `?${query}` : ''
}

export function listTransactions(filters: TransactionFilters = {}): Promise<Transaction[]> {
  return apiRequest<Transaction[]>(`/api/v1/transactions${toQueryString(filters)}`)
}

export function createTransaction(input: TransactionCreateInput): Promise<Transaction> {
  return apiRequest<Transaction>('/api/v1/transactions', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function deleteTransaction(id: number): Promise<void> {
  return apiRequest<void>(`/api/v1/transactions/${id}`, { method: 'DELETE' })
}

export function useTransactions(filters: TransactionFilters = {}) {
  return useQuery({
    queryKey: [...transactionsKey, filters],
    queryFn: () => listTransactions(filters),
  })
}

export function useCreateTransaction() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createTransaction,
    onSuccess: () => affectedKeys.forEach((key) => queryClient.invalidateQueries({ queryKey: key })),
  })
}

export function useDeleteTransaction() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteTransaction,
    onSuccess: () => affectedKeys.forEach((key) => queryClient.invalidateQueries({ queryKey: key })),
  })
}
