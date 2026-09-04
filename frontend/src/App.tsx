import { AccountFormDialog } from '@/features/accounts/AccountFormDialog'
import { AccountsList } from '@/features/accounts/AccountsList'
import { CardFormDialog } from '@/features/cards/CardFormDialog'
import { CardsList } from '@/features/cards/CardsList'
import { CardStatementsDialog } from '@/features/cards/CardStatementsDialog'
import { CategoriesList } from '@/features/categories/CategoriesList'
import { CategoryFormDialog } from '@/features/categories/CategoryFormDialog'
import { InstallmentPurchaseDialog } from '@/features/transactions/InstallmentPurchaseDialog'
import { TransactionFormDialog } from '@/features/transactions/TransactionFormDialog'
import { TransactionsList } from '@/features/transactions/TransactionsList'

function App() {
  return (
    <div className="mx-auto max-w-3xl space-y-8 p-4 sm:p-6">
      <header>
        <h1 className="text-2xl font-semibold">Bolsillito</h1>
        <p className="text-muted-foreground text-sm">Cuentas, tarjetas y movimientos</p>
      </header>

      <AccountsList />
      <CardsList />
      <CategoriesList />
      <TransactionsList />

      <AccountFormDialog />
      <CardFormDialog />
      <CardStatementsDialog />
      <CategoryFormDialog />
      <TransactionFormDialog />
      <InstallmentPurchaseDialog />
    </div>
  )
}

export default App
