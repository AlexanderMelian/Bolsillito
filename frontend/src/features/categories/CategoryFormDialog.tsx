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
import { useCreateCategory } from '@/lib/api/categories'
import type { TransactionType } from '@/lib/api/types'
import { useUiStore } from '@/stores/uiStore'

const KINDS: { value: TransactionType; label: string }[] = [
  { value: 'expense', label: 'Gasto' },
  { value: 'income', label: 'Ingreso' },
  { value: 'transfer', label: 'Transferencia' },
]

export function CategoryFormDialog() {
  const isOpen = useUiStore((state) => state.isCategoryModalOpen)
  const close = useUiStore((state) => state.closeCategoryModal)
  const createCategory = useCreateCategory()

  const [name, setName] = useState('')
  const [kind, setKind] = useState<TransactionType>('expense')
  const [icon, setIcon] = useState('')

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    await createCategory.mutateAsync({ name, kind, icon: icon || null })
    setName('')
    setKind('expense')
    setIcon('')
    close()
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && close()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Nueva categoría</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="category-name">Nombre</Label>
            <Input
              id="category-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="category-kind">Tipo</Label>
              <Select value={kind} onValueChange={(value) => setKind(value as TransactionType)}>
                <SelectTrigger id="category-kind" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {KINDS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="category-icon">Ícono (opcional)</Label>
              <Input
                id="category-icon"
                value={icon}
                onChange={(event) => setIcon(event.target.value)}
                placeholder="🍔"
              />
            </div>
          </div>

          {createCategory.isError && (
            <p className="text-destructive text-sm">No se pudo crear la categoría.</p>
          )}

          <DialogFooter>
            <Button type="submit" disabled={createCategory.isPending}>
              {createCategory.isPending ? 'Guardando…' : 'Guardar'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
