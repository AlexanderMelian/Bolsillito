import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiRequest } from '@/lib/api/client'
import type { ExchangeRate, ExchangeRateCreateInput } from '@/lib/api/types'

const exchangeRatesKey = ['exchange-rates'] as const

export function listExchangeRates(): Promise<ExchangeRate[]> {
  return apiRequest<ExchangeRate[]>('/api/v1/exchange-rates')
}

export function upsertExchangeRate(input: ExchangeRateCreateInput): Promise<ExchangeRate> {
  return apiRequest<ExchangeRate>('/api/v1/exchange-rates', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function useExchangeRates() {
  return useQuery({ queryKey: exchangeRatesKey, queryFn: listExchangeRates })
}

export function useUpsertExchangeRate() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: upsertExchangeRate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: exchangeRatesKey })
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] })
      queryClient.invalidateQueries({ queryKey: ['spending-by-category'] })
      queryClient.invalidateQueries({ queryKey: ['cash-flow-projection'] })
    },
  })
}
