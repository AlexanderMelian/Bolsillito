import { useMutation, useQueryClient } from '@tanstack/react-query'

import { apiRequest } from '@/lib/api/client'
import type { InstallmentPlan, InstallmentPlanCreateInput } from '@/lib/api/types'

export function createInstallmentPlan(input: InstallmentPlanCreateInput): Promise<InstallmentPlan> {
  return apiRequest<InstallmentPlan>('/api/v1/installment-plans', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function deleteInstallmentPlan(id: number): Promise<void> {
  return apiRequest<void>(`/api/v1/installment-plans/${id}`, { method: 'DELETE' })
}

export function useCreateInstallmentPlan() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createInstallmentPlan,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['card-statements'] })
    },
  })
}
