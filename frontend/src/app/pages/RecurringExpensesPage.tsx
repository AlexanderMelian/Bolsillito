import { RecurringExpenseFormDialog } from '@/features/recurring-expenses/RecurringExpenseFormDialog'
import { RecurringExpensesList } from '@/features/recurring-expenses/RecurringExpensesList'

export function RecurringExpensesPage() {
  return (
    <div className="space-y-8">
      <RecurringExpensesList />
      <RecurringExpenseFormDialog />
    </div>
  )
}
