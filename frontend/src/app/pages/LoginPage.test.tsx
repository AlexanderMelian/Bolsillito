import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '@/stores/authStore'
import { renderWithProviders } from '@/test-utils'

import { LoginPage } from './LoginPage'

describe('LoginPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    useAuthStore.setState({ token: null, user: null })
  })

  it('logs in and stores the token on success', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              access_token: 'tok',
              token_type: 'bearer',
              user: { id: 1, username: 'ana' },
            }),
            { status: 200 },
          ),
      ),
    )

    renderWithProviders(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )

    await userEvent.type(screen.getByLabelText('Usuario'), 'ana')
    await userEvent.type(screen.getByLabelText('Contraseña'), 'password1')
    await userEvent.click(screen.getByRole('button', { name: 'Ingresar' }))

    await waitFor(() => expect(useAuthStore.getState().token).toBe('tok'))
    expect(useAuthStore.getState().user).toEqual({ id: 1, username: 'ana' })
  })

  it('shows an error message on invalid credentials', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(JSON.stringify({ detail: 'Usuario o contraseña incorrectos' }), {
            status: 401,
          }),
      ),
    )

    renderWithProviders(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )

    await userEvent.type(screen.getByLabelText('Usuario'), 'ana')
    await userEvent.type(screen.getByLabelText('Contraseña'), 'wrongpass')
    await userEvent.click(screen.getByRole('button', { name: 'Ingresar' }))

    expect(await screen.findByText('Usuario o contraseña incorrectos.')).toBeInTheDocument()
    expect(useAuthStore.getState().token).toBeNull()
  })
})
