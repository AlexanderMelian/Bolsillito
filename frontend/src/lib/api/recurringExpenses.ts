import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiRequest } from '@/lib/api/client'
import type {
  RecurringExpense, RecurringExpenseCreateInput, RecurringExpenseSyncResult,
  RecurringExpenseUpdateInput,
} from '@/lib/api/types'

const recurringExpensesKey = ['recurring-expenses'] as const

export function listRecurringExpenses(): Promise<RecurringExpense[]> {
  return apiRequest<RecurringExpense[]>('/api/v1/recurring-expenses')
}

export function createRecurringExpense(
  input: RecurringExpenseCreateInput,
): Promise<RecurringExpense> {
  return apiRequest<RecurringExpense>('/api/v1/recurring-expenses', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function updateRecurringExpense(
  id: number,
  input: RecurringExpenseUpdateInput,
): Promise<RecurringExpense> {
  return apiRequest<RecurringExpense>(`/api/v1/recurring-expenses/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  })
}

export function deleteRecurringExpense(id: number): Promise<void> {
  return apiRequest<void>(`/api/v1/recurring-expenses/${id}`, { method: 'DELETE' })
}

export function syncRecurringExpenses(): Promise<RecurringExpenseSyncResult> {
  return apiRequest<RecurringExpenseSyncResult>('/api/v1/recurring-expenses/sync', {
    method: 'POST',
  })
}

export function useRecurringExpenses() {
  return useQuery({ queryKey: recurringExpensesKey, queryFn: listRecurringExpenses })
}

export function useCreateRecurringExpense() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createRecurringExpense,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: recurringExpensesKey }),
  })
}

export function useUpdateRecurringExpense() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: RecurringExpenseUpdateInput }) =>
      updateRecurringExpense(id, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: recurringExpensesKey }),
  })
}

export function useDeleteRecurringExpense() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteRecurringExpense,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: recurringExpensesKey }),
  })
}

export function useSyncRecurringExpenses() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: syncRecurringExpenses,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: recurringExpensesKey })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] })
      queryClient.invalidateQueries({ queryKey: ['spending-by-category'] })
      queryClient.invalidateQueries({ queryKey: ['cash-flow-projection'] })
    },
  })
}
