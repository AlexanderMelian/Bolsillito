import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { useAuthStore } from './authStore'

describe('authStore', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    useAuthStore.setState({ token: null, user: null })
  })

  it('stores the token and user on setAuth', () => {
    useAuthStore.getState().setAuth('a-token', { id: 1, username: 'ana' })

    expect(useAuthStore.getState().token).toBe('a-token')
    expect(useAuthStore.getState().user).toEqual({ id: 1, username: 'ana' })
  })

  it('clears the token and user on clearAuth', () => {
    useAuthStore.getState().setAuth('a-token', { id: 1, username: 'ana' })

    useAuthStore.getState().clearAuth()

    expect(useAuthStore.getState().token).toBeNull()
    expect(useAuthStore.getState().user).toBeNull()
  })
})
