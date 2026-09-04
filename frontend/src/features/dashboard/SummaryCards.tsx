import { useDashboardSummary } from '@/lib/api/dashboard'
import { formatCurrency } from '@/lib/utils/currency'

interface StatTileProps {
  label: string
  value: string
  tone?: 'default' | 'positive' | 'negative'
}

const TONE_CLASSES: Record<NonNullable<StatTileProps['tone']>, string> = {
  default: 'text-foreground',
  positive: 'text-[#0ca30c]',
  negative: 'text-destructive',
}

function StatTile({ label, value, tone = 'default' }: StatTileProps) {
  return (
    <div className="border-border bg-card rounded-lg border p-4">
      <p className="text-muted-foreground text-sm">{label}</p>
      <p className={`mt-1 text-2xl font-semibold tabular-nums ${TONE_CLASSES[tone]}`}>{value}</p>
    </div>
  )
}

export function SummaryCards() {
  const { data: summary, isLoading, isError } = useDashboardSummary()

  if (isLoading) return <p className="text-muted-foreground text-sm">Cargando resumen…</p>
  if (isError || !summary)
    return <p className="text-destructive text-sm">No se pudo cargar el resumen.</p>

  return (
    <section className="space-y-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <StatTile
          label="Patrimonio total"
          value={formatCurrency(summary.total_balance, summary.reference_currency)}
        />
        <StatTile
          label="Ingresos del mes"
          value={formatCurrency(summary.month_income, summary.reference_currency)}
          tone="positive"
        />
        <StatTile
          label="Gastos del mes"
          value={formatCurrency(summary.month_expenses, summary.reference_currency)}
          tone="negative"
        />
      </div>

      {summary.unconverted_balances.length > 0 && (
        <p className="text-muted-foreground text-xs">
          No se pudo consolidar{' '}
          {summary.unconverted_balances
            .map((entry) => formatCurrency(entry.amount, entry.currency))
            .join(', ')}{' '}
          — cargá la cotización en "Cotizaciones" para incluirlo en el total.
        </p>
      )}
    </section>
  )
}
