import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '@/stores/authStore'
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
const portfolio = {
  reference_currency: 'ARS',
  total_cost: '0.00',
  total_realized_gain: '0.00',
  unconverted: [],
  positions: [],
}

function stubFetch() {
  return vi.fn(async (url: string) => {
    if (url.includes('/dashboard/summary')) return new Response(JSON.stringify(summary), { status: 200 })
    if (url.includes('/dashboard/cash-flow-projection'))
      return new Response(JSON.stringify(cashFlow), { status: 200 })
    if (url.includes('/portfolio')) return new Response(JSON.stringify(portfolio), { status: 200 })
    // el resto de los endpoints usados por las páginas son listados: [] es una respuesta válida
    return new Response(JSON.stringify([]), { status: 200 })
  })
}

describe('App routing', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', stubFetch())
    useAuthStore.setState({ token: 'tok', user: { id: 1, username: 'ana' } })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    useAuthStore.setState({ token: null, user: null })
  })

  it('shows the login page when there is no session', async () => {
    useAuthStore.setState({ token: null, user: null })

    renderWithProviders(
      <MemoryRouter initialEntries={['/cuentas']}>
        <App />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Iniciá sesión para continuar')).toBeInTheDocument()
  })

  it('shows the dashboard on the root route', async () => {
    renderWithProviders(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Patrimonio total')).toBeInTheDocument()
  })

  it('logs out and shows the login page when "Salir" is clicked', async () => {
    renderWithProviders(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>,
    )
    await screen.findByText('Patrimonio total')

    await userEvent.click(screen.getByRole('button', { name: 'Salir' }))

    expect(await screen.findByText('Iniciá sesión para continuar')).toBeInTheDocument()
    expect(useAuthStore.getState().token).toBeNull()
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

    await userEvent.click(screen.getAllByRole('link', { name: 'Inversiones' })[0])
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Portafolio' })).toBeInTheDocument()
    })
  })
})
