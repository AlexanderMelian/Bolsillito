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
import { useCreateAccount, useUpdateAccount } from '@/lib/api/accounts'
import type { Account, AccountType } from '@/lib/api/types'
import { useUiStore } from '@/stores/uiStore'

const ACCOUNT_TYPES: { value: AccountType; label: string }[] = [
  { value: 'bank', label: 'Cuenta bancaria' },
  { value: 'cash', label: 'Efectivo' },
  { value: 'wallet', label: 'Billetera virtual' },
  { value: 'investment', label: 'Cuenta de inversión' },
]

interface AccountFormProps {
  editingAccount: Account | null
  onDone: () => void
}

/** Se remonta (vía `key` en AccountFormDialog) cada vez que cambia `editingAccount`, así el
 * estado inicial del form se deriva directamente de las props en vez de sincronizarse con un
 * `useEffect` -- evita el round-trip extra de render que implica un efecto. */
function AccountForm({ editingAccount, onDone }: AccountFormProps) {
  const createAccount = useCreateAccount()
  const updateAccount = useUpdateAccount()
  const mutation = editingAccount ? updateAccount : createAccount

  const [name, setName] = useState(editingAccount?.name ?? '')
  const [type, setType] = useState<AccountType>(editingAccount?.type ?? 'bank')
  const [currency, setCurrency] = useState(editingAccount?.currency ?? 'ARS')
  const [balance, setBalance] = useState(editingAccount?.balance ?? '0.00')

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (editingAccount) {
      await updateAccount.mutateAsync({
        id: editingAccount.id,
        input: { name, type, currency, balance },
      })
    } else {
      await createAccount.mutateAsync({ name, type, currency, balance })
    }
    onDone()
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1.5">
        <Label htmlFor="account-name">Nombre</Label>
        <Input
          id="account-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          required
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="account-type">Tipo</Label>
        <Select value={type} onValueChange={(value) => setType(value as AccountType)}>
          <SelectTrigger id="account-type" className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {ACCOUNT_TYPES.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <Label htmlFor="account-currency">Moneda</Label>
          <Input
            id="account-currency"
            value={currency}
            onChange={(event) => setCurrency(event.target.value.toUpperCase())}
            maxLength={3}
            required
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="account-balance">{editingAccount ? 'Saldo' : 'Saldo inicial'}</Label>
          <Input
            id="account-balance"
            type="number"
            step="0.01"
            value={balance}
            onChange={(event) => setBalance(event.target.value)}
          />
        </div>
      </div>

      {mutation.isError && (
        <p className="text-destructive text-sm">No se pudo guardar la cuenta.</p>
      )}

      <DialogFooter>
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? 'Guardando…' : 'Guardar'}
        </Button>
      </DialogFooter>
    </form>
  )
}

export function AccountFormDialog() {
  const isOpen = useUiStore((state) => state.isAccountModalOpen)
  const editingAccount = useUiStore((state) => state.editingAccount)
  const close = useUiStore((state) => state.closeAccountModal)

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && close()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{editingAccount ? 'Editar cuenta' : 'Nueva cuenta'}</DialogTitle>
        </DialogHeader>
        <AccountForm key={editingAccount?.id ?? 'new'} editingAccount={editingAccount} onDone={close} />
      </DialogContent>
    </Dialog>
  )
}
