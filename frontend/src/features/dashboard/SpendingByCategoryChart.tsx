import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { useDashboardSummary, useSpendingByCategory } from '@/lib/api/dashboard'
import { formatCurrency } from '@/lib/utils/currency'

const MAX_CATEGORIES = 8

interface TooltipPayload {
  active?: boolean
  payload?: readonly { payload?: { category_name: string; icon: string | null; total: number } }[]
  currency: string
}

function ChartTooltip({ active, payload, currency }: TooltipPayload) {
  const point = payload?.[0]?.payload
  if (!active || !point) return null
  const { category_name, icon, total } = point
  return (
    <div className="border-border bg-card rounded-md border px-3 py-2 text-sm shadow-sm">
      <p className="font-medium">
        {icon} {category_name}
      </p>
      <p className="text-muted-foreground tabular-nums">{formatCurrency(String(total), currency)}</p>
    </div>
  )
}

export function SpendingByCategoryChart() {
  const { data: categories, isLoading, isError } = useSpendingByCategory()
  const { data: summary } = useDashboardSummary()
  const currency = summary?.reference_currency ?? 'ARS'

  const chartData = (categories ?? [])
    .map((entry) => ({
      category_name: entry.category_name,
      icon: entry.icon,
      total: Number(entry.total),
    }))
    .filter((entry) => entry.total > 0)
    .slice(0, MAX_CATEGORIES)

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-medium">Gasto por categoría (este mes)</h2>

      {isLoading && <p className="text-muted-foreground text-sm">Cargando…</p>}
      {isError && <p className="text-destructive text-sm">No se pudo cargar el gasto por categoría.</p>}
      {categories?.length === 0 && (
        <p className="text-muted-foreground text-sm">Todavía no hay gastos este mes.</p>
      )}

      {chartData.length > 0 && (
        <div className="border-border bg-card h-72 rounded-lg border p-4">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 24 }}>
              <CartesianGrid horizontal={false} stroke="var(--border)" />
              <XAxis
                type="number"
                tickFormatter={(value: number) => formatCurrency(String(value), currency)}
                tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }}
                axisLine={{ stroke: 'var(--border)' }}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="category_name"
                width={110}
                tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }}
                axisLine={{ stroke: 'var(--border)' }}
                tickLine={false}
              />
              <Tooltip
                cursor={{ fill: 'var(--muted)' }}
                content={(props) => <ChartTooltip {...props} currency={currency} />}
              />
              <Bar dataKey="total" radius={[0, 4, 4, 0]} barSize={22}>
                {chartData.map((entry) => (
                  <Cell key={entry.category_name} fill="var(--chart-1)" />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  )
}
