import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { useAccounts } from '@/lib/api/accounts'
import { useCardStatements, usePayCardStatement } from '@/lib/api/cardStatements'
import type { StatementStatus } from '@/lib/api/types'
import { formatCurrency } from '@/lib/utils/currency'
import { useUiStore } from '@/stores/uiStore'

const STATUS_LABELS: Record<StatementStatus, string> = {
  open: 'Abierto',
  closed: 'Cerrado',
  paid: 'Pagado',
}

const STATUS_VARIANTS: Record<StatementStatus, 'secondary' | 'default' | 'outline'> = {
  open: 'secondary',
  closed: 'default',
  paid: 'outline',
}

export function CardStatementsDialog() {
  const card = useUiStore((state) => state.statementsCard)
  const close = useUiStore((state) => state.closeStatements)

  return (
    <Dialog open={card !== null} onOpenChange={(open) => !open && close()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Resúmenes {card ? `— ${card.name}` : ''}</DialogTitle>
        </DialogHeader>
        {card && <StatementsBody cardId={card.id} accountId={card.account_id} />}
      </DialogContent>
    </Dialog>
  )
}

function StatementsBody({ cardId, accountId }: { cardId: number; accountId: number }) {
  const { data: statements, isLoading, isError } = useCardStatements(cardId)
  const { data: accounts } = useAccounts({ includeArchived: true })
  const payStatement = usePayCardStatement(cardId)
  const currency = accounts?.find((account) => account.id === accountId)?.currency ?? 'ARS'

  if (isLoading) return <p className="text-muted-foreground text-sm">Cargando resúmenes…</p>
  if (isError)
    return <p className="text-destructive text-sm">No se pudieron cargar los resúmenes.</p>
  if (statements?.length === 0)
    return <p className="text-muted-foreground text-sm">Todavía no hay resúmenes para esta tarjeta.</p>

  return (
    <ul className="divide-border divide-y">
      {statements?.map((statement) => (
        <li key={statement.id} className="flex items-center justify-between gap-3 py-3">
          <div>
            <p className="font-medium">Cierra el {statement.closing_date}</p>
            <p className="text-muted-foreground text-xs">
              Vence el {statement.payment_due_date}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant={STATUS_VARIANTS[statement.status]}>
              {STATUS_LABELS[statement.status]}
            </Badge>
            <span className="font-medium tabular-nums">
              {formatCurrency(statement.total_amount, currency)}
            </span>
            {statement.status !== 'paid' && (
              <Button
                size="sm"
                disabled={payStatement.isPending || Number(statement.total_amount) <= 0}
                onClick={() =>
                  payStatement.mutate({
                    statementId: statement.id,
                    paymentDate: new Date().toISOString().slice(0, 10),
                  })
                }
              >
                Pagar
              </Button>
            )}
          </div>
        </li>
      ))}
    </ul>
  )
}
