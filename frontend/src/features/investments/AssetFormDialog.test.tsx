import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useUiStore } from '@/stores/uiStore'
import { renderWithProviders } from '@/test-utils'

import { AssetFormDialog } from './AssetFormDialog'

describe('AssetFormDialog', () => {
  beforeEach(() => {
    useUiStore.setState({ isAssetModalOpen: true })
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_url: string, init?: RequestInit) => {
        if (init?.method === 'POST') {
          return new Response(
            JSON.stringify({ id: 1, ticker: 'AAPL', name: 'Apple', type: 'stock', currency: 'USD' }),
            { status: 201 },
          )
        }
        throw new Error('unhandled fetch')
      }),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    useUiStore.setState({ isAssetModalOpen: false })
  })

  it('submits the asset and closes the dialog', async () => {
    renderWithProviders(<AssetFormDialog />)

    await userEvent.type(screen.getByLabelText('Ticker'), 'aapl')
    await userEvent.type(screen.getByLabelText('Nombre'), 'Apple')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/assets'),
        expect.objectContaining({ method: 'POST' }),
      )
    })
    const [, init] = vi.mocked(fetch).mock.calls[0]
    expect(JSON.parse(init!.body as string)).toEqual({
      ticker: 'AAPL',
      name: 'Apple',
      type: 'stock',
      currency: 'USD',
    })

    await waitFor(() => expect(useUiStore.getState().isAssetModalOpen).toBe(false))
  })
})
