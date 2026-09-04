import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { useCashFlowProjection } from '@/lib/api/dashboard'
import { formatCurrency } from '@/lib/utils/currency'

function monthLabel(month: string): string {
  const [year, monthNum] = month.split('-').map(Number)
  return new Date(year, monthNum - 1, 1).toLocaleDateString('es-AR', { month: 'short' })
}

interface TooltipPayload {
  active?: boolean
  payload?: readonly { payload?: { month: string; committed_amount: number } }[]
  currency: string
}

function ChartTooltip({ active, payload, currency }: TooltipPayload) {
  const point = payload?.[0]?.payload
  if (!active || !point) return null
  const { month, committed_amount } = point
  return (
    <div className="border-border bg-card rounded-md border px-3 py-2 text-sm shadow-sm">
      <p className="font-medium capitalize">{monthLabel(month)}</p>
      <p className="text-muted-foreground tabular-nums">
        {formatCurrency(String(committed_amount), currency)}
      </p>
    </div>
  )
}

export function CashFlowChart() {
  const { data, isLoading, isError } = useCashFlowProjection(6)

  const chartData = (data?.projection ?? []).map((entry) => ({
    month: entry.month,
    committed_amount: Number(entry.committed_amount),
  }))
  const currency = data?.reference_currency ?? 'ARS'
  const hasCommitments = chartData.some((entry) => entry.committed_amount > 0)

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-medium">Cuotas comprometidas (próximos 6 meses)</h2>

      {isLoading && <p className="text-muted-foreground text-sm">Cargando…</p>}
      {isError && <p className="text-destructive text-sm">No se pudo cargar la proyección.</p>}
      {!isLoading && !hasCommitments && (
        <p className="text-muted-foreground text-sm">
          No tenés cuotas pendientes de pago en los próximos 6 meses.
        </p>
      )}

      {chartData.length > 0 && (
        <div className="border-border bg-card h-64 rounded-lg border p-4">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ left: 8, right: 8 }}>
              <CartesianGrid vertical={false} stroke="var(--border)" />
              <XAxis
                dataKey="month"
                tickFormatter={monthLabel}
                tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }}
                axisLine={{ stroke: 'var(--border)' }}
                tickLine={false}
              />
              <YAxis
                tickFormatter={(value: number) => formatCurrency(String(value), currency)}
                tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }}
                axisLine={false}
                tickLine={false}
                width={80}
              />
              <Tooltip
                cursor={{ fill: 'var(--muted)' }}
                content={(props) => <ChartTooltip {...props} currency={currency} />}
              />
              <Bar dataKey="committed_amount" fill="var(--chart-1)" radius={[4, 4, 0, 0]} barSize={32} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  )
}
