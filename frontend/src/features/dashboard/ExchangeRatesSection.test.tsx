import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ExchangeRate } from '@/lib/api/types'
import { renderWithProviders } from '@/test-utils'

import { ExchangeRatesSection } from './ExchangeRatesSection'

const rates: ExchangeRate[] = [
  { id: 1, from_currency: 'USD', to_currency: 'ARS', rate: '1000.000000', date: '2026-09-01' },
]

describe('ExchangeRatesSection', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.endsWith('/api/v1/exchange-rates') && (!init || init.method === undefined)) {
          return new Response(JSON.stringify(rates), { status: 200 })
        }
        if (init?.method === 'POST') {
          return new Response(
            JSON.stringify({ id: 2, from_currency: 'USD', to_currency: 'ARS', rate: '1050.000000', date: '2026-09-02' }),
            { status: 201 },
          )
        }
        throw new Error(`unhandled fetch: ${url} ${init?.method}`)
      }),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('lists the loaded exchange rates', async () => {
    renderWithProviders(<ExchangeRatesSection />)

    expect(await screen.findByText(/USD → ARS: 1000.000000/)).toBeInTheDocument()
  })

  it('submits a new exchange rate', async () => {
    renderWithProviders(<ExchangeRatesSection />)
    await screen.findByText(/USD → ARS/)

    await userEvent.type(screen.getByLabelText('Cotización'), '1050')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/exchange-rates'),
        expect.objectContaining({ method: 'POST' }),
      )
    })
    const postCall = vi.mocked(fetch).mock.calls.find(([, init]) => init?.method === 'POST')!
    const body = JSON.parse(postCall[1]!.body as string)
    expect(body).toMatchObject({ from_currency: 'USD', to_currency: 'ARS', rate: '1050' })
  })
})
