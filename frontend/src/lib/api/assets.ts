import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiRequest } from '@/lib/api/client'
import type { Asset, AssetCreateInput } from '@/lib/api/types'

const assetsKey = ['assets'] as const

export function listAssets(): Promise<Asset[]> {
  return apiRequest<Asset[]>('/api/v1/assets')
}

export function createAsset(input: AssetCreateInput): Promise<Asset> {
  return apiRequest<Asset>('/api/v1/assets', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function deleteAsset(id: number): Promise<void> {
  return apiRequest<void>(`/api/v1/assets/${id}`, { method: 'DELETE' })
}

export function useAssets() {
  return useQuery({ queryKey: assetsKey, queryFn: listAssets })
}

export function useCreateAsset() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createAsset,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: assetsKey }),
  })
}

export function useDeleteAsset() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteAsset,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: assetsKey }),
  })
}
