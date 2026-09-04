import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { Account } from '@/lib/api/types'
import { useUiStore } from '@/stores/uiStore'
import { renderWithProviders } from '@/test-utils'

import { AccountsList } from './AccountsList'

const accounts: Account[] = [
  { id: 1, name: 'Cuenta Sueldo', type: 'bank', currency: 'ARS', balance: '1500.50', is_archived: false },
  { id: 2, name: 'Billetera del día a día', type: 'cash', currency: 'ARS', balance: '200.00', is_archived: false },
]

describe('AccountsList', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.endsWith('/api/v1/accounts') && (!init || init.method === undefined)) {
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
    useUiStore.setState({ isAccountModalOpen: false, editingAccount: null })
  })

  it('lists accounts with their formatted balance', async () => {
    renderWithProviders(<AccountsList />)

    expect(await screen.findByText('Cuenta Sueldo')).toBeInTheDocument()
    expect(screen.getByText('Billetera del día a día')).toBeInTheDocument()
    expect(screen.getByText(/1\.500,50/)).toBeInTheDocument()
  })

  it('deletes an account when its remove button is clicked', async () => {
    renderWithProviders(<AccountsList />)
    await screen.findByText('Cuenta Sueldo')

    await userEvent.click(screen.getByRole('button', { name: 'Eliminar Cuenta Sueldo' }))

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/accounts/1'),
        expect.objectContaining({ method: 'DELETE' }),
      )
    })
  })

  it('opens the create-account modal in "create" mode', async () => {
    renderWithProviders(<AccountsList />)
    await screen.findByText('Cuenta Sueldo')

    await userEvent.click(screen.getByRole('button', { name: 'Nueva cuenta' }))

    expect(useUiStore.getState().isAccountModalOpen).toBe(true)
    expect(useUiStore.getState().editingAccount).toBeNull()
  })

  it('opens the edit modal with the clicked account', async () => {
    renderWithProviders(<AccountsList />)
    await screen.findByText('Cuenta Sueldo')

    await userEvent.click(screen.getByRole('button', { name: 'Editar Cuenta Sueldo' }))

    expect(useUiStore.getState().isAccountModalOpen).toBe(true)
    expect(useUiStore.getState().editingAccount).toEqual(accounts[0])
  })
})
