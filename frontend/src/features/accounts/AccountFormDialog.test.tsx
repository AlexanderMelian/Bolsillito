import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { Account } from '@/lib/api/types'
import { useUiStore } from '@/stores/uiStore'
import { renderWithProviders } from '@/test-utils'

import { AccountFormDialog } from './AccountFormDialog'

const existingAccount: Account = {
  id: 5,
  name: 'Cuenta vieja',
  type: 'cash',
  currency: 'ARS',
  balance: '10.00',
  is_archived: false,
}

describe('AccountFormDialog', () => {
  beforeEach(() => {
    useUiStore.setState({ isAccountModalOpen: true, editingAccount: null })
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (init?.method === 'POST') {
          return new Response(
            JSON.stringify({
              id: 1,
              name: 'Nueva cuenta',
              type: 'bank',
              currency: 'ARS',
              balance: '0.00',
              is_archived: false,
            }),
            { status: 201 },
          )
        }
        if (init?.method === 'PATCH') {
          return new Response(JSON.stringify({ ...existingAccount, name: 'Cuenta renombrada' }), {
            status: 200,
          })
        }
        throw new Error(`unhandled fetch: ${url} ${init?.method}`)
      }),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    useUiStore.setState({ isAccountModalOpen: false, editingAccount: null })
  })

  it('submits the form data and closes the dialog on success', async () => {
    renderWithProviders(<AccountFormDialog />)

    await userEvent.type(screen.getByLabelText('Nombre'), 'Nueva cuenta')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/accounts'),
        expect.objectContaining({ method: 'POST' }),
      )
    })
    const [, init] = vi.mocked(fetch).mock.calls[0]
    expect(JSON.parse(init!.body as string)).toEqual({
      name: 'Nueva cuenta',
      type: 'bank',
      currency: 'ARS',
      balance: '0.00',
    })

    await waitFor(() => expect(useUiStore.getState().isAccountModalOpen).toBe(false))
  })

  it('does not render when the modal is closed', () => {
    useUiStore.setState({ isAccountModalOpen: false })
    renderWithProviders(<AccountFormDialog />)

    expect(screen.queryByText('Nueva cuenta')).not.toBeInTheDocument()
  })

  it('prefills the form and sends a PATCH when editing an existing account', async () => {
    useUiStore.setState({ isAccountModalOpen: true, editingAccount: existingAccount })
    renderWithProviders(<AccountFormDialog />)

    expect(screen.getByText('Editar cuenta')).toBeInTheDocument()
    expect(screen.getByLabelText('Nombre')).toHaveValue('Cuenta vieja')

    await userEvent.clear(screen.getByLabelText('Nombre'))
    await userEvent.type(screen.getByLabelText('Nombre'), 'Cuenta renombrada')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/accounts/5'),
        expect.objectContaining({ method: 'PATCH' }),
      )
    })
    const [, init] = vi
      .mocked(fetch)
      .mock.calls.find(([, callInit]) => callInit?.method === 'PATCH')!
    expect(JSON.parse(init!.body as string)).toEqual({
      name: 'Cuenta renombrada',
      type: 'cash',
      currency: 'ARS',
      balance: '10.00',
    })
  })
})
