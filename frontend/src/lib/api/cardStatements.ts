import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiRequest } from '@/lib/api/client'
import type { CardStatement } from '@/lib/api/types'

function statementsKey(cardId: number) {
  return ['card-statements', cardId] as const
}

export function listCardStatements(cardId: number): Promise<CardStatement[]> {
  return apiRequest<CardStatement[]>(`/api/v1/cards/${cardId}/statements`)
}

export function payCardStatement(
  cardId: number,
  statementId: number,
  paymentDate: string,
): Promise<CardStatement> {
  return apiRequest<CardStatement>(`/api/v1/cards/${cardId}/statements/${statementId}/pay`, {
    method: 'POST',
    body: JSON.stringify({ payment_date: paymentDate }),
  })
}

export function useCardStatements(cardId: number) {
  return useQuery({ queryKey: statementsKey(cardId), queryFn: () => listCardStatements(cardId) })
}

export function usePayCardStatement(cardId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ statementId, paymentDate }: { statementId: number; paymentDate: string }) =>
      payCardStatement(cardId, statementId, paymentDate),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: statementsKey(cardId) })
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    },
  })
}
