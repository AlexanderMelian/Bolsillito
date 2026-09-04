import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { Account, Asset } from '@/lib/api/types'
import { useUiStore } from '@/stores/uiStore'
import { renderWithProviders } from '@/test-utils'

import { InvestmentTransactionFormDialog } from './InvestmentTransactionFormDialog'

const assets: Asset[] = [{ id: 1, ticker: 'AAPL', name: 'Apple', type: 'stock', currency: 'USD' }]
const accounts: Account[] = [
  { id: 1, name: 'Broker', type: 'investment', currency: 'USD', balance: '0.00', is_archived: false },
]

function stubFetch() {
  return vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith('/api/v1/assets') && (!init || init.method === undefined)) {
      return new Response(JSON.stringify(assets), { status: 200 })
    }
    if (url.endsWith('/api/v1/accounts') && (!init || init.method === undefined)) {
      return new Response(JSON.stringify(accounts), { status: 200 })
    }
    if (url.endsWith('/api/v1/investment-transactions') && init?.method === 'POST') {
      return new Response(JSON.stringify({ id: 1 }), { status: 201 })
    }
    throw new Error(`unhandled fetch: ${url} ${init?.method}`)
  })
}

describe('InvestmentTransactionFormDialog', () => {
  beforeEach(() => {
    useUiStore.setState({ isInvestmentModalOpen: true })
    vi.stubGlobal('fetch', stubFetch())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    useUiStore.setState({ isInvestmentModalOpen: false })
  })

  it('creates a buy without an account', async () => {
    renderWithProviders(<InvestmentTransactionFormDialog />)

    await userEvent.click(await screen.findByRole('combobox', { name: /activo/i }))
    await userEvent.click(await screen.findByRole('option', { name: /AAPL/ }))
    await userEvent.type(screen.getByLabelText('Cantidad'), '10')
    await userEvent.type(screen.getByLabelText('Precio'), '150')

    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    await waitFor(() => {
      const postCall = vi.mocked(fetch).mock.calls.find(([, init]) => init?.method === 'POST')
      expect(postCall).toBeDefined()
    })
    const postCall = vi.mocked(fetch).mock.calls.find(([, init]) => init?.method === 'POST')!
    const body = JSON.parse(postCall[1]!.body as string)
    expect(body).toMatchObject({ asset_id: 1, type: 'buy', quantity: '10', price: '150' })
    expect(body.account_id).toBeUndefined()
  })

  it('shows the dividend convention hint only for dividends', async () => {
    renderWithProviders(<InvestmentTransactionFormDialog />)

    expect(
      screen.queryByText(/cargá cantidad.*1 y precio.*el monto total/),
    ).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('combobox', { name: /^tipo$/i }))
    await userEvent.click(await screen.findByRole('option', { name: 'Dividendo' }))

    expect(screen.getByText(/cargá cantidad.*1 y precio.*el monto total/)).toBeInTheDocument()
  })

  it('shows a message when there are no assets yet', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        if (url.endsWith('/api/v1/assets')) return new Response(JSON.stringify([]), { status: 200 })
        if (url.endsWith('/api/v1/accounts')) return new Response(JSON.stringify([]), { status: 200 })
        throw new Error(`unhandled fetch: ${url}`)
      }),
    )
    renderWithProviders(<InvestmentTransactionFormDialog />)

    expect(
      await screen.findByText('Todavía no cargaste ningún activo. Creá uno primero.'),
    ).toBeInTheDocument()
  })
})
