import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useCards, useDeleteCard } from '@/lib/api/cards'
import { useUiStore } from '@/stores/uiStore'

export function CardsList() {
  const { data: cards, isLoading, isError } = useCards()
  const deleteCard = useDeleteCard()
  const openCardModal = useUiStore((state) => state.openCardModal)
  const openStatements = useUiStore((state) => state.openStatements)

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-medium">Tarjetas</h2>
        <Button size="sm" onClick={openCardModal}>
          Nueva tarjeta
        </Button>
      </div>

      {isLoading && <p className="text-muted-foreground text-sm">Cargando tarjetas…</p>}
      {isError && <p className="text-destructive text-sm">No se pudieron cargar las tarjetas.</p>}
      {cards?.length === 0 && (
        <p className="text-muted-foreground text-sm">Todavía no cargaste ninguna tarjeta.</p>
      )}

      <ul className="grid gap-2 sm:grid-cols-2">
        {cards?.map((card) => (
          <li
            key={card.id}
            className="border-border bg-card flex items-center justify-between rounded-lg border p-3"
          >
            <div className="space-y-1">
              <p className="font-medium">{card.name}</p>
              <div className="flex items-center gap-2">
                <Badge variant={card.type === 'credit' ? 'default' : 'secondary'}>
                  {card.type === 'credit' ? 'Crédito' : 'Débito'}
                </Badge>
                {card.type === 'credit' && (
                  <span className="text-muted-foreground text-xs">
                    cierra el {card.closing_day}, paga el {card.payment_day}
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-1">
              {card.type === 'credit' && (
                <Button size="sm" variant="outline" onClick={() => openStatements(card)}>
                  Resúmenes
                </Button>
              )}
              <Button
                size="icon-sm"
                variant="ghost"
                aria-label={`Eliminar ${card.name}`}
                onClick={() => deleteCard.mutate(card.id)}
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
