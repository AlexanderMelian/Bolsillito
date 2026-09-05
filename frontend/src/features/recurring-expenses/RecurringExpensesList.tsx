import { Button } from '@/components/ui/button'
import { useAccounts } from '@/lib/api/accounts'
import {
  useDeleteRecurringExpense, useRecurringExpenses, useUpdateRecurringExpense,
} from '@/lib/api/recurringExpenses'
import { formatCurrency } from '@/lib/utils/currency'
import { useUiStore } from '@/stores/uiStore'

export function RecurringExpensesList() {
  const { data: expenses, isLoading, isError } = useRecurringExpenses()
  const { data: accounts } = useAccounts({ includeArchived: true })
  const updateExpense = useUpdateRecurringExpense()
  const deleteExpense = useDeleteRecurringExpense()
  const openRecurringExpenseModal = useUiStore((state) => state.openRecurringExpenseModal)

  const accountName = (accountId: number | null) =>
    accountId === null
      ? 'Sin cuenta'
      : (accounts?.find((account) => account.id === accountId)?.name ?? `Cuenta #${accountId}`)

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-medium">Gastos fijos</h2>
        <Button size="sm" onClick={() => openRecurringExpenseModal()}>
          Nuevo gasto fijo
        </Button>
      </div>

      {isLoading && <p className="text-muted-foreground text-sm">Cargando gastos fijos…</p>}
      {isError && (
        <p className="text-destructive text-sm">No se pudieron cargar los gastos fijos.</p>
      )}
      {expenses?.length === 0 && (
        <p className="text-muted-foreground text-sm">Todavía no cargaste ningún gasto fijo.</p>
      )}

      <ul className="divide-border bg-card divide-y rounded-lg border">
        {expenses?.map((expense) => (
          <li
            key={expense.id}
            className={`flex items-center justify-between gap-3 p-3 ${
              expense.is_active ? '' : 'opacity-60'
            }`}
          >
            <div className="min-w-0">
              <p className="truncate font-medium">
                {expense.description}
                {!expense.is_active && (
                  <span className="text-muted-foreground ml-2 text-xs">(pausado)</span>
                )}
              </p>
              <p className="text-muted-foreground truncate text-xs">
                {accountName(expense.account_id)} · día {expense.day_of_month}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-3">
              <span className="font-medium tabular-nums">
                {formatCurrency(expense.amount, expense.currency)}
              </span>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => openRecurringExpenseModal(expense)}
              >
                Editar
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() =>
                  updateExpense.mutate({
                    id: expense.id,
                    input: { is_active: !expense.is_active },
                  })
                }
              >
                {expense.is_active ? 'Pausar' : 'Reanudar'}
              </Button>
              <Button
                size="icon-sm"
                variant="ghost"
                aria-label={`Eliminar gasto fijo ${expense.description}`}
                onClick={() => deleteExpense.mutate(expense.id)}
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
