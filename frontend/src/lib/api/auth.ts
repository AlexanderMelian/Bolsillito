import { useMutation } from '@tanstack/react-query'

import { apiRequest } from '@/lib/api/client'
import type { LoginInput, RegisterInput, Token } from '@/lib/api/types'
import { useAuthStore } from '@/stores/authStore'

export function register(input: RegisterInput): Promise<Token> {
  return apiRequest<Token>('/api/v1/auth/register', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function login(input: LoginInput): Promise<Token> {
  return apiRequest<Token>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function useRegister() {
  const setAuth = useAuthStore((state) => state.setAuth)
  return useMutation({
    mutationFn: register,
    onSuccess: (token) => setAuth(token.access_token, token.user),
  })
}

export function useLogin() {
  const setAuth = useAuthStore((state) => state.setAuth)
  return useMutation({
    mutationFn: login,
    onSuccess: (token) => setAuth(token.access_token, token.user),
  })
}
