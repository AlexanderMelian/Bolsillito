import { InstallmentPurchaseDialog } from '@/features/transactions/InstallmentPurchaseDialog'
import { TransactionFormDialog } from '@/features/transactions/TransactionFormDialog'
import { TransactionsList } from '@/features/transactions/TransactionsList'

export function TransactionsPage() {
  return (
    <div className="space-y-8">
      <TransactionsList />

      <TransactionFormDialog />
      <InstallmentPurchaseDialog />
    </div>
  )
}
