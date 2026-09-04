import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiRequest } from '@/lib/api/client'
import type { InvestmentTransaction, InvestmentTransactionCreateInput, Portfolio } from '@/lib/api/types'

const investmentTransactionsKey = ['investment-transactions'] as const
const portfolioKey = ['portfolio'] as const
// Una transacción de inversión puede tocar el saldo de una cuenta -- invalidar todo lo
// relacionado es más simple que rastrear cada caso (mismo criterio que en lib/api/transactions.ts).
const affectedKeys = [investmentTransactionsKey, portfolioKey, ['accounts']] as const

export function listInvestmentTransactions(assetId?: number): Promise<InvestmentTransaction[]> {
  const query = assetId ? `?asset_id=${assetId}` : ''
  return apiRequest<InvestmentTransaction[]>(`/api/v1/investment-transactions${query}`)
}

export function createInvestmentTransaction(
  input: InvestmentTransactionCreateInput,
): Promise<InvestmentTransaction> {
  return apiRequest<InvestmentTransaction>('/api/v1/investment-transactions', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function deleteInvestmentTransaction(id: number): Promise<void> {
  return apiRequest<void>(`/api/v1/investment-transactions/${id}`, { method: 'DELETE' })
}

export function getPortfolio(): Promise<Portfolio> {
  return apiRequest<Portfolio>('/api/v1/portfolio')
}

export function useInvestmentTransactions(assetId?: number) {
  return useQuery({
    queryKey: [...investmentTransactionsKey, assetId ?? 'all'],
    queryFn: () => listInvestmentTransactions(assetId),
  })
}

export function usePortfolio() {
  return useQuery({ queryKey: portfolioKey, queryFn: getPortfolio })
}

export function useCreateInvestmentTransaction() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createInvestmentTransaction,
    onSuccess: () => affectedKeys.forEach((key) => queryClient.invalidateQueries({ queryKey: key })),
  })
}

export function useDeleteInvestmentTransaction() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteInvestmentTransaction,
    onSuccess: () => affectedKeys.forEach((key) => queryClient.invalidateQueries({ queryKey: key })),
  })
}
