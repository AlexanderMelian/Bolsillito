import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiRequest } from '@/lib/api/client'
import type { Account, AccountCreateInput, AccountUpdateInput } from '@/lib/api/types'

const accountsKey = ['accounts'] as const

export function listAccounts(options: { includeArchived?: boolean } = {}): Promise<Account[]> {
  const query = options.includeArchived ? '?include_archived=true' : ''
  return apiRequest<Account[]>(`/api/v1/accounts${query}`)
}

export function createAccount(input: AccountCreateInput): Promise<Account> {
  return apiRequest<Account>('/api/v1/accounts', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function updateAccount(id: number, input: AccountUpdateInput): Promise<Account> {
  return apiRequest<Account>(`/api/v1/accounts/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  })
}

export function deleteAccount(id: number): Promise<Account> {
  return apiRequest<Account>(`/api/v1/accounts/${id}`, { method: 'DELETE' })
}

export function useAccounts(options: { includeArchived?: boolean } = {}) {
  return useQuery({
    queryKey: [...accountsKey, options.includeArchived ?? false],
    queryFn: () => listAccounts(options),
  })
}

export function useCreateAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createAccount,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: accountsKey }),
  })
}

export function useUpdateAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: AccountUpdateInput }) =>
      updateAccount(id, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: accountsKey }),
  })
}

export function useDeleteAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteAccount,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: accountsKey }),
  })
}
