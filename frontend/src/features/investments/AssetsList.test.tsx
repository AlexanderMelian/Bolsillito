import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { Asset } from '@/lib/api/types'
import { useUiStore } from '@/stores/uiStore'
import { renderWithProviders } from '@/test-utils'

import { AssetsList } from './AssetsList'

const assets: Asset[] = [{ id: 1, ticker: 'AAPL', name: 'Apple', type: 'stock', currency: 'USD' }]

describe('AssetsList', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.endsWith('/api/v1/assets') && (!init || init.method === undefined)) {
          return new Response(JSON.stringify(assets), { status: 200 })
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
    useUiStore.setState({ isAssetModalOpen: false, isInvestmentModalOpen: false })
  })

  it('lists assets', async () => {
    renderWithProviders(<AssetsList />)
    expect(await screen.findByText(/AAPL/)).toBeInTheDocument()
  })

  it('deletes an asset', async () => {
    renderWithProviders(<AssetsList />)
    await screen.findByText(/AAPL/)

    await userEvent.click(screen.getByRole('button', { name: 'Eliminar AAPL' }))

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/assets/1'),
        expect.objectContaining({ method: 'DELETE' }),
      )
    })
  })

  it('opens the asset and investment-transaction modals', async () => {
    renderWithProviders(<AssetsList />)
    await screen.findByText(/AAPL/)

    await userEvent.click(screen.getByRole('button', { name: 'Nuevo activo' }))
    expect(useUiStore.getState().isAssetModalOpen).toBe(true)

    await userEvent.click(screen.getByRole('button', { name: 'Nueva transacción' }))
    expect(useUiStore.getState().isInvestmentModalOpen).toBe(true)
  })
})
