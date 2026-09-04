import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiRequest } from '@/lib/api/client'
import type { Card, CardCreateInput } from '@/lib/api/types'

const cardsKey = ['cards'] as const

export function listCards(accountId?: number): Promise<Card[]> {
  const query = accountId ? `?account_id=${accountId}` : ''
  return apiRequest<Card[]>(`/api/v1/cards${query}`)
}

export function createCard(input: CardCreateInput): Promise<Card> {
  return apiRequest<Card>('/api/v1/cards', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function deleteCard(id: number): Promise<void> {
  return apiRequest<void>(`/api/v1/cards/${id}`, { method: 'DELETE' })
}

export function useCards(accountId?: number) {
  return useQuery({ queryKey: [...cardsKey, accountId ?? 'all'], queryFn: () => listCards(accountId) })
}

export function useCreateCard() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createCard,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cardsKey }),
  })
}

export function useDeleteCard() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteCard,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cardsKey }),
  })
}
