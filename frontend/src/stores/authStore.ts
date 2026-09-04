import { create } from 'zustand'
import { persist } from 'zustand/middleware'

import type { UserRead } from '@/lib/api/types'

interface AuthState {
  token: string | null
  user: UserRead | null
  setAuth: (token: string, user: UserRead) => void
  clearAuth: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setAuth: (token, user) => set({ token, user }),
      clearAuth: () => set({ token: null, user: null }),
    }),
    { name: 'bolsillito-auth' },
  ),
)
