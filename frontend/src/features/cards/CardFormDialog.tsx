import { useState, type FormEvent } from 'react'

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
import { useCreateCard } from '@/lib/api/cards'
import type { CardType } from '@/lib/api/types'
import { useUiStore } from '@/stores/uiStore'

export function CardFormDialog() {
  const isOpen = useUiStore((state) => state.isCardModalOpen)
  const close = useUiStore((state) => state.closeCardModal)
  const { data: accounts } = useAccounts()
  const createCard = useCreateCard()

  const [accountId, setAccountId] = useState<string>('')
  const [name, setName] = useState('')
  const [type, setType] = useState<CardType>('debit')
  const [closingDay, setClosingDay] = useState('15')
  const [paymentDay, setPaymentDay] = useState('25')

  const resetForm = () => {
    setAccountId('')
    setName('')
    setType('debit')
    setClosingDay('15')
    setPaymentDay('25')
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    await createCard.mutateAsync({
      account_id: Number(accountId),
      name,
      type,
      closing_day: type === 'credit' ? Number(closingDay) : null,
      payment_day: type === 'credit' ? Number(paymentDay) : null,
    })
    resetForm()
    close()
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && close()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Nueva tarjeta</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="card-account">Cuenta</Label>
            <Select value={accountId} onValueChange={setAccountId}>
              <SelectTrigger id="card-account" className="w-full">
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

          <div className="space-y-1.5">
            <Label htmlFor="card-name">Nombre</Label>
            <Input
              id="card-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="card-type">Tipo</Label>
            <Select value={type} onValueChange={(value) => setType(value as CardType)}>
              <SelectTrigger id="card-type" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="debit">Débito</SelectItem>
                <SelectItem value="credit">Crédito</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {type === 'credit' && (
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="card-closing-day">Día de cierre</Label>
                <Input
                  id="card-closing-day"
                  type="number"
                  min={1}
                  max={31}
                  value={closingDay}
                  onChange={(event) => setClosingDay(event.target.value)}
                  required
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="card-payment-day">Día de pago</Label>
                <Input
                  id="card-payment-day"
                  type="number"
                  min={1}
                  max={31}
                  value={paymentDay}
                  onChange={(event) => setPaymentDay(event.target.value)}
                  required
                />
              </div>
            </div>
          )}

          {createCard.isError && (
            <p className="text-destructive text-sm">No se pudo crear la tarjeta.</p>
          )}

          <DialogFooter>
            <Button type="submit" disabled={createCard.isPending || !accountId}>
              {createCard.isPending ? 'Guardando…' : 'Guardar'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
