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
import { useAssets } from '@/lib/api/assets'
import { useCreateInvestmentTransaction } from '@/lib/api/investments'
import type { InvestmentTxType } from '@/lib/api/types'
import { useUiStore } from '@/stores/uiStore'

const TYPES: { value: InvestmentTxType; label: string }[] = [
  { value: 'buy', label: 'Compra' },
  { value: 'sell', label: 'Venta' },
  { value: 'dividend', label: 'Dividendo' },
]

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

export function InvestmentTransactionFormDialog() {
  const isOpen = useUiStore((state) => state.isInvestmentModalOpen)
  const close = useUiStore((state) => state.closeInvestmentModal)
  const { data: assets } = useAssets()
  const { data: accounts } = useAccounts()
  const createTransaction = useCreateInvestmentTransaction()

  const [assetId, setAssetId] = useState('')
  const [accountId, setAccountId] = useState('')
  const [type, setType] = useState<InvestmentTxType>('buy')
  const [quantity, setQuantity] = useState('')
  const [price, setPrice] = useState('')
  const [fee, setFee] = useState('0.00')
  const [date, setDate] = useState(today())

  const resetForm = () => {
    setAssetId('')
    setAccountId('')
    setType('buy')
    setQuantity('')
    setPrice('')
    setFee('0.00')
    setDate(today())
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    await createTransaction.mutateAsync({
      asset_id: Number(assetId),
      account_id: accountId ? Number(accountId) : undefined,
      type,
      quantity,
      price,
      fee,
      date,
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
          <DialogTitle>Nueva transacción de inversión</DialogTitle>
        </DialogHeader>
        {assets?.length === 0 ? (
          <p className="text-muted-foreground text-sm">
            Todavía no cargaste ningún activo. Creá uno primero.
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="itx-asset">Activo</Label>
              <Select value={assetId} onValueChange={setAssetId}>
                <SelectTrigger id="itx-asset" className="w-full">
                  <SelectValue placeholder="Elegí un activo" />
                </SelectTrigger>
                <SelectContent>
                  {assets?.map((asset) => (
                    <SelectItem key={asset.id} value={String(asset.id)}>
                      {asset.ticker} — {asset.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="itx-type">Tipo</Label>
              <Select value={type} onValueChange={(value) => setType(value as InvestmentTxType)}>
                <SelectTrigger id="itx-type" className="w-full">
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
              <Label htmlFor="itx-account">Cuenta (opcional)</Label>
              <Select value={accountId} onValueChange={setAccountId}>
                <SelectTrigger id="itx-account" className="w-full">
                  <SelectValue placeholder="No afectar ninguna cuenta" />
                </SelectTrigger>
                <SelectContent>
                  {accounts?.map((account) => (
                    <SelectItem key={account.id} value={String(account.id)}>
                      {account.name} ({account.currency})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="itx-quantity">Cantidad</Label>
                <Input
                  id="itx-quantity"
                  type="number"
                  step="0.00000001"
                  min="0.00000001"
                  value={quantity}
                  onChange={(event) => setQuantity(event.target.value)}
                  required
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="itx-price">Precio</Label>
                <Input
                  id="itx-price"
                  type="number"
                  step="0.00000001"
                  min="0.00000001"
                  value={price}
                  onChange={(event) => setPrice(event.target.value)}
                  required
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="itx-fee">Comisión</Label>
                <Input
                  id="itx-fee"
                  type="number"
                  step="0.01"
                  min="0"
                  value={fee}
                  onChange={(event) => setFee(event.target.value)}
                />
              </div>
            </div>

            {type === 'dividend' && (
              <p className="text-muted-foreground text-xs">
                Para un dividendo, cargá cantidad&nbsp;=&nbsp;1 y precio&nbsp;=&nbsp;el monto
                total percibido.
              </p>
            )}

            <div className="space-y-1.5">
              <Label htmlFor="itx-date">Fecha</Label>
              <Input
                id="itx-date"
                type="date"
                value={date}
                onChange={(event) => setDate(event.target.value)}
                required
              />
            </div>

            {createTransaction.isError && (
              <p className="text-destructive text-sm">No se pudo registrar la transacción.</p>
            )}

            <DialogFooter>
              <Button type="submit" disabled={createTransaction.isPending || !assetId}>
                {createTransaction.isPending ? 'Guardando…' : 'Guardar'}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
