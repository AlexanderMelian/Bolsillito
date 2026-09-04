import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '@/stores/authStore'
import { renderWithProviders } from '@/test-utils'

import { RegisterPage } from './RegisterPage'

describe('RegisterPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    useAuthStore.setState({ token: null, user: null })
  })

  it('registers and stores the token on success', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              access_token: 'tok',
              token_type: 'bearer',
              user: { id: 2, username: 'beto' },
            }),
            { status: 201 },
          ),
      ),
    )

    renderWithProviders(
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>,
    )

    await userEvent.type(screen.getByLabelText('Usuario'), 'beto')
    await userEvent.type(screen.getByLabelText('Contraseña'), 'password1')
    await userEvent.click(screen.getByRole('button', { name: 'Crear cuenta' }))

    await waitFor(() => expect(useAuthStore.getState().token).toBe('tok'))
    expect(useAuthStore.getState().user).toEqual({ id: 2, username: 'beto' })
  })

  it('shows a duplicate-username message on 409', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify({ detail: 'Ese usuario ya existe' }), { status: 409 })),
    )

    renderWithProviders(
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>,
    )

    await userEvent.type(screen.getByLabelText('Usuario'), 'ana')
    await userEvent.type(screen.getByLabelText('Contraseña'), 'password1')
    await userEvent.click(screen.getByRole('button', { name: 'Crear cuenta' }))

    expect(await screen.findByText('Ese usuario ya existe.')).toBeInTheDocument()
  })
})
