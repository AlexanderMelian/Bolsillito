import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { Account, Transaction } from '@/lib/api/types'
import { useUiStore } from '@/stores/uiStore'
import { renderWithProviders } from '@/test-utils'

import { TransactionsList } from './TransactionsList'

const accounts: Account[] = [
  { id: 1, name: 'Cuenta Sueldo', type: 'bank', currency: 'ARS', balance: '0.00', is_archived: false },
]

const transactions: Transaction[] = [
  {
    id: 1,
    type: 'income',
    account_id: 1,
    destination_account_id: null,
    card_id: null,
    category_id: null,
    installment_plan_id: null,
    recurring_expense_id: null,
    amount: '1000.00',
    currency: 'ARS',
    date: '2026-03-01',
    description: 'Sueldo',
  },
  {
    id: 2,
    type: 'expense',
    account_id: 1,
    destination_account_id: null,
    card_id: null,
    category_id: null,
    installment_plan_id: 5,
    recurring_expense_id: null,
    amount: '300.00',
    currency: 'ARS',
    date: '2026-03-02',
    description: 'Notebook',
  },
]

describe('TransactionsList', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.includes('/api/v1/transactions') && (!init || init.method === undefined)) {
          return new Response(JSON.stringify(transactions), { status: 200 })
        }
        if (url.includes('/api/v1/accounts')) {
          return new Response(JSON.stringify(accounts), { status: 200 })
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
    useUiStore.setState({ isTransactionModalOpen: false, isInstallmentModalOpen: false })
  })

  it('lists transactions resolving the account name', async () => {
    renderWithProviders(<TransactionsList />)

    expect(await screen.findByText('Sueldo')).toBeInTheDocument()
    expect(screen.getAllByText(/Cuenta Sueldo/)).toHaveLength(2)
    expect(screen.getByText(/1\.000,00/)).toBeInTheDocument()
  })

  it('disables the delete button for a transaction linked to an installment plan', async () => {
    renderWithProviders(<TransactionsList />)
    await screen.findByText('Notebook')

    expect(screen.getByRole('button', { name: 'Eliminar movimiento del 2026-03-02' })).toBeDisabled()
  })

  it('deletes a regular transaction', async () => {
    renderWithProviders(<TransactionsList />)
    await screen.findByText('Sueldo')

    await userEvent.click(screen.getByRole('button', { name: 'Eliminar movimiento del 2026-03-01' }))

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/transactions/1'),
        expect.objectContaining({ method: 'DELETE' }),
      )
    })
  })

  it('opens the transaction and installment modals from their buttons', async () => {
    renderWithProviders(<TransactionsList />)
    await screen.findByText('Sueldo')

    await userEvent.click(screen.getByRole('button', { name: 'Nuevo movimiento' }))
    expect(useUiStore.getState().isTransactionModalOpen).toBe(true)

    await userEvent.click(screen.getByRole('button', { name: 'Comprar en cuotas' }))
    expect(useUiStore.getState().isInstallmentModalOpen).toBe(true)
  })
})
