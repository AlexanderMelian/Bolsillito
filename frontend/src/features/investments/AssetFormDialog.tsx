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
import { useCreateAsset } from '@/lib/api/assets'
import type { AssetType } from '@/lib/api/types'
import { useUiStore } from '@/stores/uiStore'

const TYPES: { value: AssetType; label: string }[] = [
  { value: 'stock', label: 'Acción' },
  { value: 'bond', label: 'Bono' },
  { value: 'crypto', label: 'Cripto' },
  { value: 'fund', label: 'Fondo' },
  { value: 'other', label: 'Otro' },
]

export function AssetFormDialog() {
  const isOpen = useUiStore((state) => state.isAssetModalOpen)
  const close = useUiStore((state) => state.closeAssetModal)
  const createAsset = useCreateAsset()

  const [ticker, setTicker] = useState('')
  const [name, setName] = useState('')
  const [type, setType] = useState<AssetType>('stock')
  const [currency, setCurrency] = useState('USD')

  const resetForm = () => {
    setTicker('')
    setName('')
    setType('stock')
    setCurrency('USD')
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    await createAsset.mutateAsync({ ticker: ticker.toUpperCase(), name, type, currency })
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
          <DialogTitle>Nuevo activo</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="asset-ticker">Ticker</Label>
              <Input
                id="asset-ticker"
                value={ticker}
                onChange={(event) => setTicker(event.target.value.toUpperCase())}
                placeholder="AAPL"
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="asset-currency">Moneda</Label>
              <Input
                id="asset-currency"
                value={currency}
                onChange={(event) => setCurrency(event.target.value.toUpperCase())}
                maxLength={3}
                required
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="asset-name">Nombre</Label>
            <Input
              id="asset-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Apple Inc."
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="asset-type">Tipo</Label>
            <Select value={type} onValueChange={(value) => setType(value as AssetType)}>
              <SelectTrigger id="asset-type" className="w-full">
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

          {createAsset.isError && (
            <p className="text-destructive text-sm">No se pudo crear el activo.</p>
          )}

          <DialogFooter>
            <Button type="submit" disabled={createAsset.isPending}>
              {createAsset.isPending ? 'Guardando…' : 'Guardar'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
