import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiRequest } from '@/lib/api/client'
import type { Category, CategoryCreateInput } from '@/lib/api/types'

const categoriesKey = ['categories'] as const

export function listCategories(): Promise<Category[]> {
  return apiRequest<Category[]>('/api/v1/categories')
}

export function createCategory(input: CategoryCreateInput): Promise<Category> {
  return apiRequest<Category>('/api/v1/categories', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function deleteCategory(id: number): Promise<void> {
  return apiRequest<void>(`/api/v1/categories/${id}`, { method: 'DELETE' })
}

export function useCategories() {
  return useQuery({ queryKey: categoriesKey, queryFn: listCategories })
}

export function useCreateCategory() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createCategory,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: categoriesKey }),
  })
}

export function useDeleteCategory() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteCategory,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: categoriesKey }),
  })
}
