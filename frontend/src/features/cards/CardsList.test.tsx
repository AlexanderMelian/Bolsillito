import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { Card } from '@/lib/api/types'
import { useUiStore } from '@/stores/uiStore'
import { renderWithProviders } from '@/test-utils'

import { CardsList } from './CardsList'

const cards: Card[] = [
  {
    id: 1,
    account_id: 1,
    payment_account_id: null,
    name: 'Débito Banco',
    type: 'debit',
    credit_limit: null,
    closing_day: null,
    payment_day: null,
  },
  {
    id: 2,
    account_id: 1,
    payment_account_id: null,
    name: 'Visa',
    type: 'credit',
    credit_limit: '500000.00',
    closing_day: 15,
    payment_day: 25,
  },
]

describe('CardsList', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.endsWith('/api/v1/cards') && (!init || init.method === undefined)) {
          return new Response(JSON.stringify(cards), { status: 200 })
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
    useUiStore.setState({ isCardModalOpen: false })
  })

  it('lists cards and shows the billing cycle only for credit cards', async () => {
    renderWithProviders(<CardsList />)

    expect(await screen.findByText('Débito Banco')).toBeInTheDocument()
    expect(screen.getByText('Visa')).toBeInTheDocument()
    expect(screen.getByText(/cierra el 15, paga el 25/)).toBeInTheDocument()
  })

  it('deletes a card when its remove button is clicked', async () => {
    renderWithProviders(<CardsList />)
    await screen.findByText('Visa')

    await userEvent.click(screen.getByRole('button', { name: 'Eliminar Visa' }))

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/cards/2'),
        expect.objectContaining({ method: 'DELETE' }),
      )
    })
  })

  it('opens the card modal when "Nueva tarjeta" is clicked', async () => {
    renderWithProviders(<CardsList />)
    await screen.findByText('Visa')

    await userEvent.click(screen.getByRole('button', { name: 'Nueva tarjeta' }))

    expect(useUiStore.getState().isCardModalOpen).toBe(true)
  })
})
