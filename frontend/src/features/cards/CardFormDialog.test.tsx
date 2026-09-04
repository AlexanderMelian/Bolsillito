import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { Account } from '@/lib/api/types'
import { useUiStore } from '@/stores/uiStore'
import { renderWithProviders } from '@/test-utils'

import { CardFormDialog } from './CardFormDialog'

const accounts: Account[] = [
  { id: 1, name: 'Cuenta Sueldo', type: 'bank', currency: 'ARS', balance: '0.00', is_archived: false },
]

function mockFetch() {
  return vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith('/api/v1/accounts') && init?.method === undefined) {
      return new Response(JSON.stringify(accounts), { status: 200 })
    }
    if (url.endsWith('/api/v1/cards') && init?.method === 'POST') {
      return new Response(JSON.stringify({ id: 10 }), { status: 201 })
    }
    throw new Error(`unhandled fetch: ${url} ${init?.method}`)
  })
}

describe('CardFormDialog', () => {
  beforeEach(() => {
    useUiStore.setState({ isCardModalOpen: true })
    vi.stubGlobal('fetch', mockFetch())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    useUiStore.setState({ isCardModalOpen: false })
  })

  it('does not ask for closing/payment day when the card is debit (default)', async () => {
    renderWithProviders(<CardFormDialog />)

    expect(screen.queryByLabelText('Día de cierre')).not.toBeInTheDocument()
  })

  it('creates a debit card with null cycle fields', async () => {
    renderWithProviders(<CardFormDialog />)

    await userEvent.click(await screen.findByRole('combobox', { name: /cuenta/i }))
    await userEvent.click(await screen.findByRole('option', { name: 'Cuenta Sueldo' }))
    await userEvent.type(screen.getByLabelText('Nombre'), 'Débito Banco')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/cards'),
        expect.objectContaining({ method: 'POST' }),
      )
    })
    const postCall = vi.mocked(fetch).mock.calls.find(([, init]) => init?.method === 'POST')!
    expect(JSON.parse(postCall[1]!.body as string)).toEqual({
      account_id: 1,
      name: 'Débito Banco',
      type: 'debit',
      closing_day: null,
      payment_day: null,
    })
  })

  it('shows and submits closing/payment day when switching to credit', async () => {
    renderWithProviders(<CardFormDialog />)

    await userEvent.click(await screen.findByRole('combobox', { name: /cuenta/i }))
    await userEvent.click(await screen.findByRole('option', { name: 'Cuenta Sueldo' }))
    await userEvent.type(screen.getByLabelText('Nombre'), 'Visa')

    await userEvent.click(screen.getByRole('combobox', { name: /tipo/i }))
    await userEvent.click(await screen.findByRole('option', { name: 'Crédito' }))

    const closingDayInput = await screen.findByLabelText('Día de cierre')
    expect(closingDayInput).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    await waitFor(() => {
      const postCall = vi.mocked(fetch).mock.calls.find(([, init]) => init?.method === 'POST')
      expect(postCall).toBeDefined()
    })
    const postCall = vi.mocked(fetch).mock.calls.find(([, init]) => init?.method === 'POST')!
    const body = JSON.parse(postCall[1]!.body as string)
    expect(body.type).toBe('credit')
    expect(body.closing_day).toBe(15)
    expect(body.payment_day).toBe(25)
  })
})
