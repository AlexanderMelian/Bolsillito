import { useState, type FormEvent } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useExchangeRates, useUpsertExchangeRate } from '@/lib/api/exchangeRates'

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

export function ExchangeRatesSection() {
  const { data: rates } = useExchangeRates()
  const upsertRate = useUpsertExchangeRate()

  const [fromCurrency, setFromCurrency] = useState('USD')
  const [toCurrency, setToCurrency] = useState('ARS')
  const [rate, setRate] = useState('')
  const [date, setDate] = useState(today())

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    await upsertRate.mutateAsync({
      from_currency: fromCurrency.toUpperCase(),
      to_currency: toCurrency.toUpperCase(),
      rate,
      date,
    })
    setRate('')
  }

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-medium">Cotizaciones</h2>
      <p className="text-muted-foreground text-sm">
        Cargá la cotización del día para consolidar cuentas en otra moneda en el patrimonio total.
      </p>

      <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-2">
        <div className="w-20 space-y-1.5">
          <Label htmlFor="fx-from">De</Label>
          <Input
            id="fx-from"
            value={fromCurrency}
            onChange={(event) => setFromCurrency(event.target.value.toUpperCase())}
            maxLength={3}
            required
          />
        </div>
        <div className="w-20 space-y-1.5">
          <Label htmlFor="fx-to">A</Label>
          <Input
            id="fx-to"
            value={toCurrency}
            onChange={(event) => setToCurrency(event.target.value.toUpperCase())}
            maxLength={3}
            required
          />
        </div>
        <div className="w-32 space-y-1.5">
          <Label htmlFor="fx-rate">Cotización</Label>
          <Input
            id="fx-rate"
            type="number"
            step="0.000001"
            min="0"
            value={rate}
            onChange={(event) => setRate(event.target.value)}
            required
          />
        </div>
        <div className="w-40 space-y-1.5">
          <Label htmlFor="fx-date">Fecha</Label>
          <Input
            id="fx-date"
            type="date"
            value={date}
            onChange={(event) => setDate(event.target.value)}
            required
          />
        </div>
        <Button type="submit" disabled={upsertRate.isPending}>
          {upsertRate.isPending ? 'Guardando…' : 'Guardar'}
        </Button>
      </form>

      {rates && rates.length > 0 && (
        <ul className="text-muted-foreground space-y-1 text-sm">
          {rates.slice(0, 5).map((entry) => (
            <li key={entry.id} className="tabular-nums">
              {entry.from_currency} → {entry.to_currency}: {entry.rate} ({entry.date})
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
