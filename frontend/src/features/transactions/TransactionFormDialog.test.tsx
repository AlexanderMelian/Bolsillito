import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { Account, Card, Category } from '@/lib/api/types'
import { useUiStore } from '@/stores/uiStore'
import { renderWithProviders } from '@/test-utils'

import { TransactionFormDialog } from './TransactionFormDialog'

const accounts: Account[] = [
  { id: 1, name: 'Cuenta Sueldo', type: 'bank', currency: 'ARS', balance: '0.00', is_archived: false },
  { id: 2, name: 'Efectivo', type: 'cash', currency: 'ARS', balance: '0.00', is_archived: false },
]
const cards: Card[] = [
  {
    id: 1,
    account_id: 1,
    payment_account_id: null,
    name: 'Débito',
    type: 'debit',
    credit_limit: null,
    closing_day: null,
    payment_day: null,
  },
]
const categories: Category[] = [{ id: 1, name: 'Sueldo', kind: 'income', icon: null }]

function stubFetch() {
  return vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith('/api/v1/accounts') && (!init || init.method === undefined)) {
      return new Response(JSON.stringify(accounts), { status: 200 })
    }
    if (url.endsWith('/api/v1/cards') && (!init || init.method === undefined)) {
      return new Response(JSON.stringify(cards), { status: 200 })
    }
    if (url.endsWith('/api/v1/categories') && (!init || init.method === undefined)) {
      return new Response(JSON.stringify(categories), { status: 200 })
    }
    if (url.endsWith('/api/v1/transactions') && init?.method === 'POST') {
      return new Response(JSON.stringify({ id: 1 }), { status: 201 })
    }
    throw new Error(`unhandled fetch: ${url} ${init?.method}`)
  })
}

describe('TransactionFormDialog', () => {
  beforeEach(() => {
    useUiStore.setState({ isTransactionModalOpen: true })
    vi.stubGlobal('fetch', stubFetch())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    useUiStore.setState({ isTransactionModalOpen: false })
  })

  it('creates an income transaction with the selected category', async () => {
    renderWithProviders(<TransactionFormDialog />)

    await userEvent.click(screen.getByRole('combobox', { name: /^tipo$/i }))
    await userEvent.click(await screen.findByRole('option', { name: 'Ingreso' }))

    await userEvent.click(screen.getByRole('combobox', { name: /^cuenta$/i }))
    await userEvent.click(await screen.findByRole('option', { name: 'Cuenta Sueldo' }))

    await userEvent.click(screen.getByRole('combobox', { name: /categoría/i }))
    await userEvent.click(await screen.findByRole('option', { name: 'Sueldo' }))

    await userEvent.type(screen.getByLabelText('Monto'), '1000')

    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    await waitFor(() => {
      const postCall = vi.mocked(fetch).mock.calls.find(([, init]) => init?.method === 'POST')
      expect(postCall).toBeDefined()
    })
    const postCall = vi.mocked(fetch).mock.calls.find(([, init]) => init?.method === 'POST')!
    const body = JSON.parse(postCall[1]!.body as string)
    expect(body).toMatchObject({ type: 'income', account_id: 1, category_id: 1, amount: '1000' })
  })

  it('shows the destination account selector only for transfers', async () => {
    renderWithProviders(<TransactionFormDialog />)

    expect(screen.queryByLabelText('Cuenta de destino')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('combobox', { name: /^tipo$/i }))
    await userEvent.click(await screen.findByRole('option', { name: 'Transferencia' }))

    expect(screen.getByLabelText('Cuenta de destino')).toBeInTheDocument()
  })

  it('disables submit for a transfer until a destination account is chosen', async () => {
    renderWithProviders(<TransactionFormDialog />)

    await userEvent.click(screen.getByRole('combobox', { name: /^tipo$/i }))
    await userEvent.click(await screen.findByRole('option', { name: 'Transferencia' }))
    await userEvent.click(screen.getByRole('combobox', { name: /cuenta de origen/i }))
    await userEvent.click(await screen.findByRole('option', { name: 'Cuenta Sueldo' }))

    expect(screen.getByRole('button', { name: 'Guardar' })).toBeDisabled()
  })

  it('shows the card selector for an expense on an account that has cards', async () => {
    renderWithProviders(<TransactionFormDialog />)

    await userEvent.click(screen.getByRole('combobox', { name: /^cuenta$/i }))
    await userEvent.click(await screen.findByRole('option', { name: 'Cuenta Sueldo' }))

    expect(await screen.findByLabelText('Tarjeta (opcional)')).toBeInTheDocument()
  })
})
