import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { Card, Category } from '@/lib/api/types'
import { useUiStore } from '@/stores/uiStore'
import { renderWithProviders } from '@/test-utils'

import { InstallmentPurchaseDialog } from './InstallmentPurchaseDialog'

const cards: Card[] = [
  {
    id: 1,
    account_id: 1,
    payment_account_id: null,
    name: 'Visa',
    type: 'credit',
    credit_limit: null,
    closing_day: 15,
    payment_day: 25,
  },
  {
    id: 2,
    account_id: 1,
    payment_account_id: null,
    name: 'Débito',
    type: 'debit',
    credit_limit: null,
    closing_day: null,
    payment_day: null,
  },
]
const categories: Category[] = [{ id: 1, name: 'Tecnología', kind: 'expense', icon: '💻' }]

function stubFetch() {
  return vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith('/api/v1/cards') && (!init || init.method === undefined)) {
      return new Response(JSON.stringify(cards), { status: 200 })
    }
    if (url.endsWith('/api/v1/categories') && (!init || init.method === undefined)) {
      return new Response(JSON.stringify(categories), { status: 200 })
    }
    if (url.endsWith('/api/v1/installment-plans') && init?.method === 'POST') {
      return new Response(JSON.stringify({ id: 1 }), { status: 201 })
    }
    throw new Error(`unhandled fetch: ${url} ${init?.method}`)
  })
}

describe('InstallmentPurchaseDialog', () => {
  beforeEach(() => {
    useUiStore.setState({ isInstallmentModalOpen: true })
    vi.stubGlobal('fetch', stubFetch())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    useUiStore.setState({ isInstallmentModalOpen: false })
  })

  it('only lists credit cards for the card selector', async () => {
    renderWithProviders(<InstallmentPurchaseDialog />)

    await userEvent.click(await screen.findByRole('combobox', { name: /tarjeta de crédito/i }))

    expect(await screen.findByRole('option', { name: 'Visa' })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: 'Débito' })).not.toBeInTheDocument()
  })

  it('submits the purchase split across the given number of installments', async () => {
    renderWithProviders(<InstallmentPurchaseDialog />)

    await userEvent.click(await screen.findByRole('combobox', { name: /tarjeta de crédito/i }))
    await userEvent.click(await screen.findByRole('option', { name: 'Visa' }))
    await userEvent.type(screen.getByLabelText('Descripción'), 'Notebook')
    await userEvent.type(screen.getByLabelText('Monto total'), '300000')
    const installmentsInput = screen.getByLabelText('Cuotas')
    await userEvent.clear(installmentsInput)
    await userEvent.type(installmentsInput, '3')

    expect(screen.getByText(/3 cuotas de aproximadamente \$100000\.00/)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    await waitFor(() => {
      const postCall = vi.mocked(fetch).mock.calls.find(([, init]) => init?.method === 'POST')
      expect(postCall).toBeDefined()
    })
    const postCall = vi.mocked(fetch).mock.calls.find(([, init]) => init?.method === 'POST')!
    const body = JSON.parse(postCall[1]!.body as string)
    expect(body).toMatchObject({
      card_id: 1,
      description: 'Notebook',
      total_amount: '300000',
      total_installments: 3,
    })
  })

  it('shows a message when there are no credit cards yet', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        if (url.endsWith('/api/v1/cards')) return new Response(JSON.stringify([]), { status: 200 })
        if (url.endsWith('/api/v1/categories'))
          return new Response(JSON.stringify([]), { status: 200 })
        throw new Error(`unhandled fetch: ${url}`)
      }),
    )
    renderWithProviders(<InstallmentPurchaseDialog />)

    expect(
      await screen.findByText('Todavía no tenés ninguna tarjeta de crédito cargada.'),
    ).toBeInTheDocument()
  })
})
