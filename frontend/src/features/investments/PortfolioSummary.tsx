import { Badge } from '@/components/ui/badge'
import { usePortfolio } from '@/lib/api/investments'
import { formatCurrency } from '@/lib/utils/currency'

function formatQuantity(value: string): string {
  return Number(value).toLocaleString('es-AR', { maximumFractionDigits: 8 })
}

export function PortfolioSummary() {
  const { data: portfolio, isLoading, isError } = usePortfolio()

  if (isLoading) return <p className="text-muted-foreground text-sm">Cargando portafolio…</p>
  if (isError || !portfolio)
    return <p className="text-destructive text-sm">No se pudo cargar el portafolio.</p>

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-medium">Portafolio</h2>
      <p className="text-muted-foreground text-xs">
        Costo de la posición y ganancia ya realizada de ventas concretadas -- esta app no
        integra ninguna cotización de mercado en tiempo real, así que no muestra valor actual ni
        ganancia "en papel".
      </p>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="border-border bg-card rounded-lg border p-4">
          <p className="text-muted-foreground text-sm">Costo total invertido</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">
            {formatCurrency(portfolio.total_cost, portfolio.reference_currency)}
          </p>
        </div>
        <div className="border-border bg-card rounded-lg border p-4">
          <p className="text-muted-foreground text-sm">Ganancia realizada</p>
          <p
            className={`mt-1 text-2xl font-semibold tabular-nums ${
              Number(portfolio.total_realized_gain) < 0 ? 'text-destructive' : 'text-[#0ca30c]'
            }`}
          >
            {formatCurrency(portfolio.total_realized_gain, portfolio.reference_currency)}
          </p>
        </div>
      </div>

      {portfolio.unconverted.length > 0 && (
        <p className="text-muted-foreground text-xs">
          No se pudo consolidar{' '}
          {portfolio.unconverted.map((entry) => formatCurrency(entry.amount, entry.currency)).join(', ')}{' '}
          — cargá la cotización en "Cotizaciones" (Resumen) para incluirlo en el total.
        </p>
      )}

      {portfolio.positions.length === 0 && (
        <p className="text-muted-foreground text-sm">
          Todavía no tenés ninguna posición cargada.
        </p>
      )}

      {portfolio.positions.length > 0 && (
        <ul className="divide-border bg-card divide-y rounded-lg border">
          {portfolio.positions.map((position) => (
            <li key={position.asset_id} className="flex items-center justify-between gap-3 p-3">
              <div>
                <p className="font-medium">
                  {position.ticker} <Badge variant="secondary">{position.type}</Badge>
                </p>
                <p className="text-muted-foreground text-xs">
                  {formatQuantity(position.quantity)} unidades · costo prom.{' '}
                  {formatCurrency(position.avg_cost, position.currency)}
                </p>
              </div>
              <div className="text-right">
                <p className="font-medium tabular-nums">
                  {formatCurrency(position.total_cost, position.currency)}
                </p>
                {Number(position.realized_gain) !== 0 && (
                  <p
                    className={`text-xs tabular-nums ${
                      Number(position.realized_gain) < 0 ? 'text-destructive' : 'text-[#0ca30c]'
                    }`}
                  >
                    {formatCurrency(position.realized_gain, position.currency)} realizado
                  </p>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
