import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Portfolio } from '@/lib/api/types'
import { renderWithProviders } from '@/test-utils'

import { PortfolioSummary } from './PortfolioSummary'

const portfolio: Portfolio = {
  reference_currency: 'ARS',
  total_cost: '150000.00',
  total_realized_gain: '2000.00',
  unconverted: [],
  positions: [
    {
      asset_id: 1,
      ticker: 'AAPL',
      name: 'Apple',
      type: 'stock',
      currency: 'USD',
      quantity: '10.00000000',
      avg_cost: '150.00000000',
      total_cost: '1500.00',
      realized_gain: '0.00',
    },
  ],
}

describe('PortfolioSummary', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders the consolidated totals and the position list', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(portfolio), { status: 200 })))
    renderWithProviders(<PortfolioSummary />)

    expect(await screen.findByText('$ 150.000,00')).toBeInTheDocument()
    expect(screen.getByText('$ 2.000,00')).toBeInTheDocument()
    expect(screen.getByText(/AAPL/)).toBeInTheDocument()
  })

  it('shows a warning for positions that could not be converted', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({ ...portfolio, unconverted: [{ currency: 'USD', amount: '1500.00' }] }),
            { status: 200 },
          ),
      ),
    )
    renderWithProviders(<PortfolioSummary />)

    expect(await screen.findByText(/No se pudo consolidar/)).toBeInTheDocument()
  })

  it('shows a message when there are no positions', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(JSON.stringify({ ...portfolio, positions: [] }), { status: 200 }),
      ),
    )
    renderWithProviders(<PortfolioSummary />)

    expect(
      await screen.findByText('Todavía no tenés ninguna posición cargada.'),
    ).toBeInTheDocument()
  })

  it('shows an error message when the request fails', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('error', { status: 500 })))
    renderWithProviders(<PortfolioSummary />)

    expect(await screen.findByText('No se pudo cargar el portafolio.')).toBeInTheDocument()
  })
})
