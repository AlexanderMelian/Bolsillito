import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useAccounts, useDeleteAccount } from '@/lib/api/accounts'
import type { AccountType } from '@/lib/api/types'
import { formatCurrency } from '@/lib/utils/currency'
import { useUiStore } from '@/stores/uiStore'

const TYPE_LABELS: Record<AccountType, string> = {
  bank: 'Banco',
  cash: 'Efectivo',
  wallet: 'Billetera',
  investment: 'Inversión',
}

export function AccountsList() {
  const { data: accounts, isLoading, isError } = useAccounts()
  const deleteAccount = useDeleteAccount()
  const openAccountModal = useUiStore((state) => state.openAccountModal)

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-medium">Cuentas</h2>
        <Button size="sm" onClick={() => openAccountModal()}>
          Nueva cuenta
        </Button>
      </div>

      {isLoading && <p className="text-muted-foreground text-sm">Cargando cuentas…</p>}
      {isError && (
        <p className="text-destructive text-sm">No se pudieron cargar las cuentas.</p>
      )}
      {accounts?.length === 0 && (
        <p className="text-muted-foreground text-sm">Todavía no cargaste ninguna cuenta.</p>
      )}

      <ul className="grid gap-2 sm:grid-cols-2">
        {accounts?.map((account) => (
          <li
            key={account.id}
            className="border-border bg-card flex items-center justify-between rounded-lg border p-3"
          >
            <button
              type="button"
              className="space-y-1 text-left"
              aria-label={`Editar ${account.name}`}
              onClick={() => openAccountModal(account)}
            >
              <p className="font-medium">{account.name}</p>
              <Badge variant="secondary">{TYPE_LABELS[account.type]}</Badge>
            </button>
            <div className="flex items-center gap-3">
              <span className="font-medium tabular-nums">
                {formatCurrency(account.balance, account.currency)}
              </span>
              <Button
                size="icon-sm"
                variant="ghost"
                aria-label={`Eliminar ${account.name}`}
                onClick={() => deleteAccount.mutate(account.id)}
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
