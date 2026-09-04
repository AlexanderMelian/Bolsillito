import { useAuthStore } from '@/stores/authStore'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  status: number
  detail: unknown

  constructor(status: number, detail: unknown) {
    super(typeof detail === 'string' ? detail : `Error de API (HTTP ${status})`)
    this.status = status
    this.detail = detail
  }
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const token = useAuthStore.getState().token
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  })

  if (!response.ok) {
    // Token vencido/inválido: se cierra la sesión localmente para volver a mostrar el login.
    // Idempotente si ya estaba deslogueado (ej. un 401 de /auth/login por credenciales malas).
    if (response.status === 401) useAuthStore.getState().clearAuth()
    const body = await response.json().catch(() => null)
    throw new ApiError(response.status, body?.detail ?? null)
  }

  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}
