import { afterEach, describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '@/stores/authStore'

import { apiRequest, ApiError } from './client'

describe('apiRequest', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    useAuthStore.setState({ token: null, user: null })
  })

  it('returns the parsed JSON body on success', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
    )

    await expect(apiRequest('/api/v1/health')).resolves.toEqual({ ok: true })
  })

  it('returns undefined for a 204 response', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 204 })))

    await expect(apiRequest('/api/v1/accounts/1')).resolves.toBeUndefined()
  })

  it('throws an ApiError with the backend detail on a non-ok response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(JSON.stringify({ detail: 'Cuenta no encontrada' }), { status: 404 }),
      ),
    )

    try {
      await apiRequest('/api/v1/accounts/999')
      expect.unreachable('apiRequest debía rechazar la promesa')
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError)
      expect((error as ApiError).status).toBe(404)
      expect((error as ApiError).message).toBe('Cuenta no encontrada')
    }
  })

  it('falls back to a generic message when the error body is not JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response('not json', { status: 500 })),
    )

    try {
      await apiRequest('/api/v1/accounts')
      expect.unreachable('apiRequest debía rechazar la promesa')
    } catch (error) {
      expect((error as ApiError).status).toBe(500)
      expect((error as ApiError).message).toBe('Error de API (HTTP 500)')
    }
  })

  it('attaches the Authorization header when a token is stored', async () => {
    useAuthStore.setState({ token: 'my-token', user: { id: 1, username: 'ana' } })
    const fetchMock = vi.fn(
      async (_url: string, _init?: RequestInit) => new Response(JSON.stringify({}), { status: 200 }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await apiRequest('/api/v1/accounts')

    const [, init] = fetchMock.mock.calls[0]
    expect((init!.headers as Record<string, string>).Authorization).toBe('Bearer my-token')
  })

  it('does not attach an Authorization header when there is no token', async () => {
    const fetchMock = vi.fn(
      async (_url: string, _init?: RequestInit) => new Response(JSON.stringify({}), { status: 200 }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await apiRequest('/api/v1/accounts')

    const [, init] = fetchMock.mock.calls[0]
    expect((init!.headers as Record<string, string>).Authorization).toBeUndefined()
  })

  it('logs out locally when the backend returns 401', async () => {
    useAuthStore.setState({ token: 'stale-token', user: { id: 1, username: 'ana' } })
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify({ detail: 'No autenticado' }), { status: 401 })),
    )

    await expect(apiRequest('/api/v1/accounts')).rejects.toBeInstanceOf(ApiError)

    expect(useAuthStore.getState().token).toBeNull()
    expect(useAuthStore.getState().user).toBeNull()
  })
})
