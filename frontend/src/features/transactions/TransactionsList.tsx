import { Button } from '@/components/ui/button'
import { useAccounts } from '@/lib/api/accounts'
import { useDeleteTransaction, useTransactions } from '@/lib/api/transactions'
import type { Transaction } from '@/lib/api/types'
import { formatCurrency } from '@/lib/utils/currency'
import { useUiStore } from '@/stores/uiStore'

const TYPE_SIGN: Record<Transaction['type'], string> = {
  income: '+',
  expense: '−',
  transfer: '⇄',
}

export function TransactionsList() {
  const { data: transactions, isLoading, isError } = useTransactions()
  const { data: accounts } = useAccounts({ includeArchived: true })
  const deleteTransaction = useDeleteTransaction()
  const openTransactionModal = useUiStore((state) => state.openTransactionModal)
  const openInstallmentModal = useUiStore((state) => state.openInstallmentModal)

  const accountName = (accountId: number | null) =>
    accountId === null
      ? 'Sin cuenta'
      : (accounts?.find((account) => account.id === accountId)?.name ?? `Cuenta #${accountId}`)

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-medium">Movimientos</h2>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={openInstallmentModal}>
            Comprar en cuotas
          </Button>
          <Button size="sm" onClick={openTransactionModal}>
            Nuevo movimiento
          </Button>
        </div>
      </div>

      {isLoading && <p className="text-muted-foreground text-sm">Cargando movimientos…</p>}
      {isError && (
        <p className="text-destructive text-sm">No se pudieron cargar los movimientos.</p>
      )}
      {transactions?.length === 0 && (
        <p className="text-muted-foreground text-sm">Todavía no cargaste ningún movimiento.</p>
      )}

      <ul className="divide-border bg-card divide-y rounded-lg border">
        {transactions?.map((transaction) => (
          <li key={transaction.id} className="flex items-center justify-between gap-3 p-3">
            <div className="min-w-0">
              <p className="truncate font-medium">
                {transaction.description ||
                  (transaction.type === 'transfer' ? 'Transferencia' : 'Movimiento')}
                {transaction.recurring_expense_id !== null && (
                  <span className="bg-primary/10 text-primary ml-2 rounded px-1.5 py-0.5 text-xs">
                    Fijo
                  </span>
                )}
              </p>
              <p className="text-muted-foreground truncate text-xs">
                {accountName(transaction.account_id)}
                {transaction.destination_account_id
                  ? ` → ${accountName(transaction.destination_account_id)}`
                  : ''}
                {' · '}
                {transaction.date}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-3">
              <span className="font-medium tabular-nums">
                {TYPE_SIGN[transaction.type]}{' '}
                {formatCurrency(transaction.amount, transaction.currency)}
              </span>
              <Button
                size="icon-sm"
                variant="ghost"
                aria-label={`Eliminar movimiento del ${transaction.date}`}
                disabled={transaction.installment_plan_id !== null}
                onClick={() => deleteTransaction.mutate(transaction.id)}
              >
                ×
              </Button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
