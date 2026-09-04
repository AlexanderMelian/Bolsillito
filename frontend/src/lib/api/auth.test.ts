import { afterEach, describe, expect, it, vi } from 'vitest'

import { login, register } from './auth'

describe('auth api', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('register posts to /auth/register and returns the token', async () => {
    const token = {
      access_token: 'tok',
      token_type: 'bearer',
      user: { id: 1, username: 'ana' },
    }
    const fetchMock = vi.fn(
      async (_url: string, _init?: RequestInit) => new Response(JSON.stringify(token), { status: 201 }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(register({ username: 'ana', password: 'password1' })).resolves.toEqual(token)

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toContain('/api/v1/auth/register')
    expect(init?.method).toBe('POST')
    expect(JSON.parse(init!.body as string)).toEqual({ username: 'ana', password: 'password1' })
  })

  it('login posts to /auth/login and returns the token', async () => {
    const token = {
      access_token: 'tok',
      token_type: 'bearer',
      user: { id: 1, username: 'ana' },
    }
    const fetchMock = vi.fn(
      async (_url: string, _init?: RequestInit) => new Response(JSON.stringify(token), { status: 200 }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(login({ username: 'ana', password: 'password1' })).resolves.toEqual(token)

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toContain('/api/v1/auth/login')
    expect(init?.method).toBe('POST')
  })
})
