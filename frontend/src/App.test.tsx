import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { renderWithProviders } from '@/test-utils'

import App from './App'

const summary = {
  reference_currency: 'ARS',
  month: '2026-09',
  total_balance: '0.00',
  month_income: '0.00',
  month_expenses: '0.00',
  unconverted_balances: [],
}
const cashFlow = {
  reference_currency: 'ARS',
  projection: [{ month: '2026-09', committed_amount: '0.00' }],
}

function stubFetch() {
  return vi.fn(async (url: string) => {
    if (url.includes('/dashboard/summary')) return new Response(JSON.stringify(summary), { status: 200 })
    if (url.includes('/dashboard/cash-flow-projection'))
      return new Response(JSON.stringify(cashFlow), { status: 200 })
    // el resto de los endpoints usados por las páginas son listados: [] es una respuesta válida
    return new Response(JSON.stringify([]), { status: 200 })
  })
}

describe('App routing', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', stubFetch())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the dashboard on the root route', async () => {
    renderWithProviders(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Patrimonio total')).toBeInTheDocument()
  })

  it('navigates between Resumen, Cuentas and Movimientos', async () => {
    renderWithProviders(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>,
    )
    await screen.findByText('Patrimonio total')

    await userEvent.click(screen.getAllByRole('link', { name: 'Cuentas' })[0])
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Cuentas' })).toBeInTheDocument()
    })

    await userEvent.click(screen.getAllByRole('link', { name: 'Movimientos' })[0])
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Movimientos' })).toBeInTheDocument()
    })
  })
})
