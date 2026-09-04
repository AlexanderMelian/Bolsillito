import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useUiStore } from '@/stores/uiStore'
import { renderWithProviders } from '@/test-utils'

import { CategoryFormDialog } from './CategoryFormDialog'

describe('CategoryFormDialog', () => {
  beforeEach(() => {
    useUiStore.setState({ isCategoryModalOpen: true })
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_url: string, init?: RequestInit) => {
        if (init?.method === 'POST') {
          return new Response(JSON.stringify({ id: 1, name: 'Comida', kind: 'expense', icon: null }), {
            status: 201,
          })
        }
        throw new Error('unhandled fetch')
      }),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    useUiStore.setState({ isCategoryModalOpen: false })
  })

  it('submits the category and closes the dialog', async () => {
    renderWithProviders(<CategoryFormDialog />)

    await userEvent.type(screen.getByLabelText('Nombre'), 'Comida')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/categories'),
        expect.objectContaining({ method: 'POST' }),
      )
    })
    const [, init] = vi.mocked(fetch).mock.calls[0]
    expect(JSON.parse(init!.body as string)).toEqual({ name: 'Comida', kind: 'expense', icon: null })

    await waitFor(() => expect(useUiStore.getState().isCategoryModalOpen).toBe(false))
  })
})
