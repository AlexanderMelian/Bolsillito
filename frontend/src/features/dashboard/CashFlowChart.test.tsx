import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { CashFlowProjection } from '@/lib/api/types'
import { renderWithProviders } from '@/test-utils'

import { CashFlowChart } from './CashFlowChart'

describe('CashFlowChart', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows a message when there are no upcoming commitments', async () => {
    const empty: CashFlowProjection = {
      reference_currency: 'ARS',
      projection: [
        { month: '2026-09', committed_amount: '0.00' },
        { month: '2026-10', committed_amount: '0.00' },
      ],
    }
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(empty), { status: 200 })))

    renderWithProviders(<CashFlowChart />)

    expect(
      await screen.findByText('No tenés cuotas pendientes de pago en los próximos 6 meses.'),
    ).toBeInTheDocument()
  })

  it('renders the chart container when there are committed amounts', async () => {
    const withData: CashFlowProjection = {
      reference_currency: 'ARS',
      projection: [
        { month: '2026-09', committed_amount: '15000.00' },
        { month: '2026-10', committed_amount: '0.00' },
      ],
    }
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(withData), { status: 200 })))

    renderWithProviders(<CashFlowChart />)

    expect(
      await screen.findByText('Cuotas comprometidas (próximos 6 meses)'),
    ).toBeInTheDocument()
    expect(
      screen.queryByText('No tenés cuotas pendientes de pago en los próximos 6 meses.'),
    ).not.toBeInTheDocument()
  })

  it('shows an error message when the request fails', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('error', { status: 500 })))
    renderWithProviders(<CashFlowChart />)

    expect(await screen.findByText('No se pudo cargar la proyección.')).toBeInTheDocument()
  })
})
