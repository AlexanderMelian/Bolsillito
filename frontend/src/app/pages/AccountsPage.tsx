import { AccountFormDialog } from '@/features/accounts/AccountFormDialog'
import { AccountsList } from '@/features/accounts/AccountsList'
import { CardFormDialog } from '@/features/cards/CardFormDialog'
import { CardsList } from '@/features/cards/CardsList'
import { CardStatementsDialog } from '@/features/cards/CardStatementsDialog'
import { CategoriesList } from '@/features/categories/CategoriesList'
import { CategoryFormDialog } from '@/features/categories/CategoryFormDialog'

export function AccountsPage() {
  return (
    <div className="space-y-8">
      <AccountsList />
      <CardsList />
      <CategoriesList />

      <AccountFormDialog />
      <CardFormDialog />
      <CardStatementsDialog />
      <CategoryFormDialog />
    </div>
  )
}
