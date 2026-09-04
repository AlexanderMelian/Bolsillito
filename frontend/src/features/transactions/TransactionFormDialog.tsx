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
import { useCards } from '@/lib/api/cards'
import { useCategories } from '@/lib/api/categories'
import { useCreateTransaction } from '@/lib/api/transactions'
import type { TransactionType } from '@/lib/api/types'
import { useUiStore } from '@/stores/uiStore'

const TYPES: { value: TransactionType; label: string }[] = [
  { value: 'expense', label: 'Gasto' },
  { value: 'income', label: 'Ingreso' },
  { value: 'transfer', label: 'Transferencia' },
]

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

export function TransactionFormDialog() {
  const isOpen = useUiStore((state) => state.isTransactionModalOpen)
  const close = useUiStore((state) => state.closeTransactionModal)
  const { data: accounts } = useAccounts()
  const { data: cards } = useCards()
  const { data: categories } = useCategories()
  const createTransaction = useCreateTransaction()

  const [type, setType] = useState<TransactionType>('expense')
  const [accountId, setAccountId] = useState('')
  const [destinationAccountId, setDestinationAccountId] = useState('')
  const [cardId, setCardId] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [amount, setAmount] = useState('')
  const [date, setDate] = useState(today())
  const [description, setDescription] = useState('')

  const accountCards = useMemo(
    () => cards?.filter((card) => card.account_id === Number(accountId)) ?? [],
    [cards, accountId],
  )
  const matchingCategories = useMemo(
    () => categories?.filter((category) => category.kind === type) ?? [],
    [categories, type],
  )

  const resetForm = () => {
    setType('expense')
    setAccountId('')
    setDestinationAccountId('')
    setCardId('')
    setCategoryId('')
    setAmount('')
    setDate(today())
    setDescription('')
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    await createTransaction.mutateAsync({
      type,
      account_id: Number(accountId),
      destination_account_id: type === 'transfer' ? Number(destinationAccountId) : undefined,
      card_id: type === 'expense' && cardId ? Number(cardId) : undefined,
      category_id: categoryId ? Number(categoryId) : undefined,
      amount,
      date,
      description: description || undefined,
    })
    resetForm()
    close()
  }

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => {
        if (!open) {
          resetForm()
          close()
        }
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Nuevo movimiento</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="tx-type">Tipo</Label>
            <Select
              value={type}
              onValueChange={(value) => {
                setType(value as TransactionType)
                setCardId('')
                setCategoryId('')
              }}
            >
              <SelectTrigger id="tx-type" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TYPES.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="tx-account">{type === 'transfer' ? 'Cuenta de origen' : 'Cuenta'}</Label>
            <Select value={accountId} onValueChange={setAccountId}>
              <SelectTrigger id="tx-account" className="w-full">
                <SelectValue placeholder="Elegí una cuenta" />
              </SelectTrigger>
              <SelectContent>
                {accounts?.map((account) => (
                  <SelectItem key={account.id} value={String(account.id)}>
                    {account.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {type === 'transfer' && (
            <div className="space-y-1.5">
              <Label htmlFor="tx-destination">Cuenta de destino</Label>
              <Select value={destinationAccountId} onValueChange={setDestinationAccountId}>
                <SelectTrigger id="tx-destination" className="w-full">
                  <SelectValue placeholder="Elegí una cuenta" />
                </SelectTrigger>
                <SelectContent>
                  {accounts
                    ?.filter((account) => String(account.id) !== accountId)
                    .map((account) => (
                      <SelectItem key={account.id} value={String(account.id)}>
                        {account.name}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {type === 'expense' && accountCards.length > 0 && (
            <div className="space-y-1.5">
              <Label htmlFor="tx-card">Tarjeta (opcional)</Label>
              <Select value={cardId} onValueChange={setCardId}>
                <SelectTrigger id="tx-card" className="w-full">
                  <SelectValue placeholder="Sin tarjeta (efectivo/débito directo)" />
                </SelectTrigger>
                <SelectContent>
                  {accountCards.map((card) => (
                    <SelectItem key={card.id} value={String(card.id)}>
                      {card.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {type !== 'transfer' && matchingCategories.length > 0 && (
            <div className="space-y-1.5">
              <Label htmlFor="tx-category">Categoría (opcional)</Label>
              <Select value={categoryId} onValueChange={setCategoryId}>
                <SelectTrigger id="tx-category" className="w-full">
                  <SelectValue placeholder="Sin categoría" />
                </SelectTrigger>
                <SelectContent>
                  {matchingCategories.map((category) => (
                    <SelectItem key={category.id} value={String(category.id)}>
                      {category.icon} {category.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="tx-amount">Monto</Label>
              <Input
                id="tx-amount"
                type="number"
                step="0.01"
                min="0.01"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="tx-date">Fecha</Label>
              <Input
                id="tx-date"
                type="date"
                value={date}
                onChange={(event) => setDate(event.target.value)}
                required
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="tx-description">Descripción (opcional)</Label>
            <Input
              id="tx-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </div>

          {createTransaction.isError && (
            <p className="text-destructive text-sm">No se pudo registrar el movimiento.</p>
          )}

          <DialogFooter>
            <Button
              type="submit"
              disabled={
                createTransaction.isPending ||
                !accountId ||
                (type === 'transfer' && !destinationAccountId)
              }
            >
              {createTransaction.isPending ? 'Guardando…' : 'Guardar'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
