import { create } from 'zustand'

import type { Account } from '@/lib/api/types'

interface UiState {
  isAccountModalOpen: boolean
  editingAccount: Account | null
  isCardModalOpen: boolean
  openAccountModal: (account?: Account) => void
  closeAccountModal: () => void
  openCardModal: () => void
  closeCardModal: () => void
}

export const useUiStore = create<UiState>((set) => ({
  isAccountModalOpen: false,
  editingAccount: null,
  isCardModalOpen: false,
  openAccountModal: (account) =>
    set({ isAccountModalOpen: true, editingAccount: account ?? null }),
  closeAccountModal: () => set({ isAccountModalOpen: false, editingAccount: null }),
  openCardModal: () => set({ isCardModalOpen: true }),
  closeCardModal: () => set({ isCardModalOpen: false }),
}))
