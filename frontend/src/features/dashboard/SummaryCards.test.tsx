import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { DashboardSummary } from '@/lib/api/types'
import { renderWithProviders } from '@/test-utils'

import { SummaryCards } from './SummaryCards'

const summary: DashboardSummary = {
  reference_currency: 'ARS',
  month: '2026-09',
  total_balance: '15000.00',
  month_income: '5000.00',
  month_expenses: '2000.00',
  unconverted_balances: [],
}

describe('SummaryCards', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders the totals from the summary endpoint', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(summary), { status: 200 })))
    renderWithProviders(<SummaryCards />)

    expect(await screen.findByText('$ 15.000,00')).toBeInTheDocument()
    expect(screen.getByText('$ 5.000,00')).toBeInTheDocument()
    expect(screen.getByText('$ 2.000,00')).toBeInTheDocument()
  })

  it('shows a warning for balances that could not be converted', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({ ...summary, unconverted_balances: [{ currency: 'USD', amount: '10.00' }] }),
            { status: 200 },
          ),
      ),
    )
    renderWithProviders(<SummaryCards />)

    expect(await screen.findByText(/No se pudo consolidar/)).toBeInTheDocument()
  })

  it('shows an error message when the request fails', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('error', { status: 500 })))
    renderWithProviders(<SummaryCards />)

    expect(await screen.findByText('No se pudo cargar el resumen.')).toBeInTheDocument()
  })
})
