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
import { useCards } from '@/lib/api/cards'
import { useCategories } from '@/lib/api/categories'
import { useCreateInstallmentPlan } from '@/lib/api/installmentPlans'
import { useUiStore } from '@/stores/uiStore'

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

export function InstallmentPurchaseDialog() {
  const isOpen = useUiStore((state) => state.isInstallmentModalOpen)
  const close = useUiStore((state) => state.closeInstallmentModal)
  const { data: cards } = useCards()
  const { data: categories } = useCategories()
  const createPlan = useCreateInstallmentPlan()

  const creditCards = useMemo(() => cards?.filter((card) => card.type === 'credit') ?? [], [cards])
  const expenseCategories = useMemo(
    () => categories?.filter((category) => category.kind === 'expense') ?? [],
    [categories],
  )

  const [cardId, setCardId] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [description, setDescription] = useState('')
  const [purchaseDate, setPurchaseDate] = useState(today())
  const [totalAmount, setTotalAmount] = useState('')
  const [totalInstallments, setTotalInstallments] = useState('1')

  const resetForm = () => {
    setCardId('')
    setCategoryId('')
    setDescription('')
    setPurchaseDate(today())
    setTotalAmount('')
    setTotalInstallments('1')
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    await createPlan.mutateAsync({
      card_id: Number(cardId),
      category_id: categoryId ? Number(categoryId) : undefined,
      description,
      purchase_date: purchaseDate,
      total_amount: totalAmount,
      total_installments: Number(totalInstallments),
    })
    resetForm()
    close()
  }

  const installmentPreview =
    Number(totalAmount) > 0 && Number(totalInstallments) > 0
      ? (Number(totalAmount) / Number(totalInstallments)).toFixed(2)
      : null

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
          <DialogTitle>Comprar en cuotas</DialogTitle>
        </DialogHeader>
        {creditCards.length === 0 ? (
          <p className="text-muted-foreground text-sm">
            Todavía no tenés ninguna tarjeta de crédito cargada.
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="plan-card">Tarjeta de crédito</Label>
              <Select value={cardId} onValueChange={setCardId}>
                <SelectTrigger id="plan-card" className="w-full">
                  <SelectValue placeholder="Elegí una tarjeta" />
                </SelectTrigger>
                <SelectContent>
                  {creditCards.map((card) => (
                    <SelectItem key={card.id} value={String(card.id)}>
                      {card.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="plan-description">Descripción</Label>
              <Input
                id="plan-description"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Notebook"
                required
              />
            </div>

            {expenseCategories.length > 0 && (
              <div className="space-y-1.5">
                <Label htmlFor="plan-category">Categoría (opcional)</Label>
                <Select value={categoryId} onValueChange={setCategoryId}>
                  <SelectTrigger id="plan-category" className="w-full">
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

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="plan-amount">Monto total</Label>
                <Input
                  id="plan-amount"
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={totalAmount}
                  onChange={(event) => setTotalAmount(event.target.value)}
                  required
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="plan-installments">Cuotas</Label>
                <Input
                  id="plan-installments"
                  type="number"
                  min={1}
                  value={totalInstallments}
                  onChange={(event) => setTotalInstallments(event.target.value)}
                  required
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="plan-date">Fecha de compra</Label>
              <Input
                id="plan-date"
                type="date"
                value={purchaseDate}
                onChange={(event) => setPurchaseDate(event.target.value)}
                required
              />
            </div>

            {installmentPreview && (
              <p className="text-muted-foreground text-sm">
                {totalInstallments} cuotas de aproximadamente ${installmentPreview}
              </p>
            )}

            {createPlan.isError && (
              <p className="text-destructive text-sm">No se pudo registrar la compra.</p>
            )}

            <DialogFooter>
              <Button type="submit" disabled={createPlan.isPending || !cardId}>
                {createPlan.isPending ? 'Guardando…' : 'Guardar'}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
