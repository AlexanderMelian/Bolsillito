import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { Category } from '@/lib/api/types'
import { useUiStore } from '@/stores/uiStore'
import { renderWithProviders } from '@/test-utils'

import { CategoriesList } from './CategoriesList'

const categories: Category[] = [
  { id: 1, name: 'Comida', kind: 'expense', icon: '🍔' },
  { id: 2, name: 'Sueldo', kind: 'income', icon: null },
]

describe('CategoriesList', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.endsWith('/api/v1/categories') && (!init || init.method === undefined)) {
          return new Response(JSON.stringify(categories), { status: 200 })
        }
        if (init?.method === 'DELETE') {
          return new Response(null, { status: 204 })
        }
        throw new Error(`unhandled fetch: ${url}`)
      }),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    useUiStore.setState({ isCategoryModalOpen: false })
  })

  it('lists categories with their kind', async () => {
    renderWithProviders(<CategoriesList />)

    expect(await screen.findByText(/Comida/)).toBeInTheDocument()
    expect(screen.getByText(/Sueldo/)).toBeInTheDocument()
  })

  it('deletes a category', async () => {
    renderWithProviders(<CategoriesList />)
    await screen.findByText(/Comida/)

    await userEvent.click(screen.getByRole('button', { name: 'Eliminar Comida' }))

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/categories/1'),
        expect.objectContaining({ method: 'DELETE' }),
      )
    })
  })

  it('opens the create-category modal', async () => {
    renderWithProviders(<CategoriesList />)
    await screen.findByText(/Comida/)

    await userEvent.click(screen.getByRole('button', { name: 'Nueva categoría' }))

    expect(useUiStore.getState().isCategoryModalOpen).toBe(true)
  })
})
