import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { CategorySpending, DashboardSummary } from '@/lib/api/types'
import { renderWithProviders } from '@/test-utils'

import { SpendingByCategoryChart } from './SpendingByCategoryChart'

const summary: DashboardSummary = {
  reference_currency: 'ARS',
  month: '2026-09',
  total_balance: '0.00',
  month_income: '0.00',
  month_expenses: '0.00',
  unconverted_balances: [],
}

function stubFetch(categories: CategorySpending[]) {
  return vi.fn(async (url: string) => {
    if (url.includes('/dashboard/spending-by-category')) {
      return new Response(JSON.stringify(categories), { status: 200 })
    }
    if (url.includes('/dashboard/summary')) {
      return new Response(JSON.stringify(summary), { status: 200 })
    }
    throw new Error(`unhandled fetch: ${url}`)
  })
}

describe('SpendingByCategoryChart', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows a message when there is no spending this month', async () => {
    vi.stubGlobal('fetch', stubFetch([]))
    renderWithProviders(<SpendingByCategoryChart />)

    expect(await screen.findByText('Todavía no hay gastos este mes.')).toBeInTheDocument()
  })

  it('renders the chart title when there is spending data', async () => {
    vi.stubGlobal(
      'fetch',
      stubFetch([{ category_id: 1, category_name: 'Comida', icon: '🍔', total: '500.00' }]),
    )
    renderWithProviders(<SpendingByCategoryChart />)

    expect(await screen.findByText('Gasto por categoría (este mes)')).toBeInTheDocument()
    expect(screen.queryByText('Todavía no hay gastos este mes.')).not.toBeInTheDocument()
  })

  it('shows an error message when the request fails', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('error', { status: 500 })))
    renderWithProviders(<SpendingByCategoryChart />)

    expect(
      await screen.findByText('No se pudo cargar el gasto por categoría.'),
    ).toBeInTheDocument()
  })
})
