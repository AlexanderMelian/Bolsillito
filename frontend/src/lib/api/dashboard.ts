import { useQuery } from '@tanstack/react-query'

import { apiRequest } from '@/lib/api/client'
import type { CashFlowProjection, CategorySpending, DashboardSummary } from '@/lib/api/types'

export function getDashboardSummary(month?: string): Promise<DashboardSummary> {
  const query = month ? `?month=${month}` : ''
  return apiRequest<DashboardSummary>(`/api/v1/dashboard/summary${query}`)
}

export function getSpendingByCategory(month?: string): Promise<CategorySpending[]> {
  const query = month ? `?month=${month}` : ''
  return apiRequest<CategorySpending[]>(`/api/v1/dashboard/spending-by-category${query}`)
}

export function getCashFlowProjection(months = 6): Promise<CashFlowProjection> {
  return apiRequest<CashFlowProjection>(`/api/v1/dashboard/cash-flow-projection?months=${months}`)
}

export function useDashboardSummary(month?: string) {
  return useQuery({
    queryKey: ['dashboard-summary', month ?? 'current'],
    queryFn: () => getDashboardSummary(month),
  })
}

export function useSpendingByCategory(month?: string) {
  return useQuery({
    queryKey: ['spending-by-category', month ?? 'current'],
    queryFn: () => getSpendingByCategory(month),
  })
}

export function useCashFlowProjection(months = 6) {
  return useQuery({
    queryKey: ['cash-flow-projection', months],
    queryFn: () => getCashFlowProjection(months),
  })
}
