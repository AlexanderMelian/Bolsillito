import { useMemo, useState, type FormEvent } from 'react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useAccounts } from '@/lib/api/accounts'
import { useCategories } from '@/lib/api/categories'
import { useCreateRecurringExpense, useUpdateRecurringExpense } from '@/lib/api/recurringExpenses'
import type { RecurringExpense } from '@/lib/api/types'
import { formatCurrency } from '@/lib/utils/currency'
import { useUiStore } from '@/stores/uiStore'

const NO_ACCOUNT = '__none__'

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

interface RecurringExpenseFormProps {
  editingExpense: RecurringExpense | null
  onDone: () => void
}

/** Se remonta (vía `key` en RecurringExpenseFormDialog) cada vez que cambia `editingExpense`,
 * mismo criterio que AccountFormDialog -- el estado inicial se deriva de las props en vez de
 * sincronizarse con un useEffect. */
function RecurringExpenseForm({ editingExpense, onDone }: RecurringExpenseFormProps) {
  const { data: accounts } = useAccounts()
  const { data: categories } = useCategories()
  const createExpense = useCreateRecurringExpense()
  const updateExpense = useUpdateRecurringExpense()
  const mutation = editingExpense ? updateExpense : createExpense

  const expenseCategories = useMemo(
    () => categories?.filter((category) => category.kind === 'expense') ?? [],
    [categories],
  )

  const [accountId, setAccountId] = useState(
    editingExpense?.account_id != null ? String(editingExpense.account_id) : NO_ACCOUNT,
  )
  const [categoryId, setCategoryId] = useState(
    editingExpense?.category_id != null ? String(editingExpense.category_id) : '',
  )
  const [description, setDescription] = useState(editingExpense?.description ?? '')
  const [amount, setAmount] = useState(editingExpense?.amount ?? '')
  const [currency, setCurrency] = useState(editingExpense?.currency ?? 'ARS')
  const [dayOfMonth, setDayOfMonth] = useState(String(editingExpense?.day_of_month ?? '1'))
  const [startDate, setStartDate] = useState(editingExpense?.start_date ?? today())

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    const account_id = accountId === NO_ACCOUNT ? null : Number(accountId)
    if (editingExpense) {
      await updateExpense.mutateAsync({
        id: editingExpense.id,
        input: {
          account_id,
          category_id: categoryId ? Number(categoryId) : null,
          description,
          amount,
          day_of_month: Number(dayOfMonth),
        },
      })
    } else {
      await createExpense.mutateAsync({
        account_id,
        category_id: categoryId ? Number(categoryId) : undefined,
        description,
        amount,
        currency: account_id === null ? currency : undefined,
        day_of_month: Number(dayOfMonth),
        start_date: startDate,
      })
    }
    onDone()
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1.5">
        <Label htmlFor="recurring-description">Descripción</Label>
        <Input
          id="recurring-description"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="Alquiler"
          required
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="recurring-account">Cuenta</Label>
        <Select value={accountId} onValueChange={setAccountId}>
          <SelectTrigger id="recurring-account" className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={NO_ACCOUNT}>Sin cuenta (no afecta ningún saldo)</SelectItem>
            {accounts?.map((account) => (
              <SelectItem key={account.id} value={String(account.id)}>
                {account.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {expenseCategories.length > 0 && (
          <div className="space-y-1.5">
            <Label htmlFor="recurring-category">Categoría (opcional)</Label>
            <Select value={categoryId} onValueChange={setCategoryId}>
              <SelectTrigger id="recurring-category" className="w-full">
                <SelectValue placeholder="Sin categoría" />
              </SelectTrigger>
              <SelectContent>
                {expenseCategories.map((category) => (
                  <SelectItem key={category.id} value={String(category.id)}>
                    {category.icon} {category.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
        {accountId === NO_ACCOUNT && (
          <div className="space-y-1.5">
            <Label htmlFor="recurring-currency">Moneda</Label>
            <Input
              id="recurring-currency"
              value={currency}
              onChange={(event) => setCurrency(event.target.value.toUpperCase())}
              maxLength={3}
              required
            />
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <Label htmlFor="recurring-amount">Monto</Label>
          <Input
            id="recurring-amount"
            type="number"
            step="0.01"
            min="0.01"
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            required
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="recurring-day">Día del mes</Label>
          <Input
            id="recurring-day"
            type="number"
            min={1}
            max={31}
            value={dayOfMonth}
            onChange={(event) => setDayOfMonth(event.target.value)}
            required
          />
        </div>
      </div>

      {!editingExpense && (
        <div className="space-y-1.5">
          <Label htmlFor="recurring-start">Empieza a generarse desde</Label>
          <Input
            id="recurring-start"
            type="date"
            value={startDate}
            onChange={(event) => setStartDate(event.target.value)}
            required
          />
          <p className="text-muted-foreground text-xs">
            Si es una fecha pasada, se generan los movimientos de los meses ya transcurridos.
          </p>
        </div>
      )}

      {Number(dayOfMonth) > 0 && Number(amount) > 0 && (
        <p className="text-muted-foreground text-sm">
          Se va a generar el día {dayOfMonth} de cada mes, por {formatCurrency(amount, currency)}.
        </p>
      )}

      {mutation.isError && (
        <p className="text-destructive text-sm">No se pudo guardar el gasto fijo.</p>
      )}

      <DialogFooter>
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? 'Guardando…' : 'Guardar'}
        </Button>
      </DialogFooter>
    </form>
  )
}

export function RecurringExpenseFormDialog() {
  const isOpen = useUiStore((state) => state.isRecurringExpenseModalOpen)
  const editingExpense = useUiStore((state) => state.editingRecurringExpense)
  const close = useUiStore((state) => state.closeRecurringExpenseModal)

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && close()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{editingExpense ? 'Editar gasto fijo' : 'Nuevo gasto fijo'}</DialogTitle>
        </DialogHeader>
        <RecurringExpenseForm
          key={editingExpense?.id ?? 'new'}
          editingExpense={editingExpense}
          onDone={close}
        />
      </DialogContent>
    </Dialog>
  )
}
