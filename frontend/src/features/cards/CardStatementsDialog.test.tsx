import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { Account, Card, CardStatement } from '@/lib/api/types'
import { useUiStore } from '@/stores/uiStore'
import { renderWithProviders } from '@/test-utils'

import { CardStatementsDialog } from './CardStatementsDialog'

const card: Card = {
  id: 1,
  account_id: 1,
  payment_account_id: null,
  name: 'Visa',
  type: 'credit',
  credit_limit: null,
  closing_day: 15,
  payment_day: 25,
}
const accounts: Account[] = [
  { id: 1, name: 'Cuenta', type: 'bank', currency: 'ARS', balance: '0.00', is_archived: false },
]
const statements: CardStatement[] = [
  {
    id: 10,
    card_id: 1,
    closing_date: '2026-03-15',
    payment_due_date: '2026-03-25',
    status: 'closed',
    total_amount: '1000.00',
    payment_transaction_id: null,
  },
  {
    id: 11,
    card_id: 1,
    closing_date: '2026-04-15',
    payment_due_date: '2026-04-25',
    status: 'paid',
    total_amount: '500.00',
    payment_transaction_id: 99,
  },
]

function stubFetch() {
  return vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith('/api/v1/cards/1/statements') && (!init || init.method === undefined)) {
      return new Response(JSON.stringify(statements), { status: 200 })
    }
    if (url.includes('/api/v1/accounts')) {
      return new Response(JSON.stringify(accounts), { status: 200 })
    }
    if (url.includes('/pay') && init?.method === 'POST') {
      return new Response(
        JSON.stringify({ ...statements[0], status: 'paid', payment_transaction_id: 100 }),
        { status: 200 },
      )
    }
    throw new Error(`unhandled fetch: ${url} ${init?.method}`)
  })
}

describe('CardStatementsDialog', () => {
  beforeEach(() => {
    useUiStore.setState({ statementsCard: card })
    vi.stubGlobal('fetch', stubFetch())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    useUiStore.setState({ statementsCard: null })
  })

  it('lists statements with their status and total', async () => {
    renderWithProviders(<CardStatementsDialog />)

    expect(await screen.findByText('Cierra el 2026-03-15')).toBeInTheDocument()
    expect(screen.getByText('Cerrado')).toBeInTheDocument()
    expect(screen.getByText('Pagado')).toBeInTheDocument()
  })

  it('does not show a pay button for an already-paid statement', async () => {
    renderWithProviders(<CardStatementsDialog />)
    await screen.findByText('Cierra el 2026-04-15')

    const paidRow = screen.getByText('Cierra el 2026-04-15').closest('li')!
    expect(paidRow.querySelector('button')).toBeNull()
  })

  it('pays an unpaid statement', async () => {
    renderWithProviders(<CardStatementsDialog />)
    await screen.findByText('Cierra el 2026-03-15')

    await userEvent.click(screen.getAllByRole('button', { name: 'Pagar' })[0])

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/cards/1/statements/10/pay'),
        expect.objectContaining({ method: 'POST' }),
      )
    })
  })

  it('renders nothing when there is no selected card', () => {
    useUiStore.setState({ statementsCard: null })
    renderWithProviders(<CardStatementsDialog />)

    expect(screen.queryByText(/Resúmenes/)).not.toBeInTheDocument()
  })
})
