import { create } from 'zustand'

import type { Account, Card } from '@/lib/api/types'

interface UiState {
  isAccountModalOpen: boolean
  editingAccount: Account | null
  openAccountModal: (account?: Account) => void
  closeAccountModal: () => void

  isCardModalOpen: boolean
  openCardModal: () => void
  closeCardModal: () => void

  isCategoryModalOpen: boolean
  openCategoryModal: () => void
  closeCategoryModal: () => void

  isTransactionModalOpen: boolean
  openTransactionModal: () => void
  closeTransactionModal: () => void

  isInstallmentModalOpen: boolean
  openInstallmentModal: () => void
  closeInstallmentModal: () => void

  statementsCard: Card | null
  openStatements: (card: Card) => void
  closeStatements: () => void

  isAssetModalOpen: boolean
  openAssetModal: () => void
  closeAssetModal: () => void

  isInvestmentModalOpen: boolean
  openInvestmentModal: () => void
  closeInvestmentModal: () => void
}

export const useUiStore = create<UiState>((set) => ({
  isAccountModalOpen: false,
  editingAccount: null,
  openAccountModal: (account) =>
    set({ isAccountModalOpen: true, editingAccount: account ?? null }),
  closeAccountModal: () => set({ isAccountModalOpen: false, editingAccount: null }),

  isCardModalOpen: false,
  openCardModal: () => set({ isCardModalOpen: true }),
  closeCardModal: () => set({ isCardModalOpen: false }),

  isCategoryModalOpen: false,
  openCategoryModal: () => set({ isCategoryModalOpen: true }),
  closeCategoryModal: () => set({ isCategoryModalOpen: false }),

  isTransactionModalOpen: false,
  openTransactionModal: () => set({ isTransactionModalOpen: true }),
  closeTransactionModal: () => set({ isTransactionModalOpen: false }),

  isInstallmentModalOpen: false,
  openInstallmentModal: () => set({ isInstallmentModalOpen: true }),
  closeInstallmentModal: () => set({ isInstallmentModalOpen: false }),

  statementsCard: null,
  openStatements: (card) => set({ statementsCard: card }),
  closeStatements: () => set({ statementsCard: null }),

  isAssetModalOpen: false,
  openAssetModal: () => set({ isAssetModalOpen: true }),
  closeAssetModal: () => set({ isAssetModalOpen: false }),

  isInvestmentModalOpen: false,
  openInvestmentModal: () => set({ isInvestmentModalOpen: true }),
  closeInvestmentModal: () => set({ isInvestmentModalOpen: false }),
}))
