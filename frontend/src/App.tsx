import { AccountFormDialog } from '@/features/accounts/AccountFormDialog'
import { AccountsList } from '@/features/accounts/AccountsList'
import { CardFormDialog } from '@/features/cards/CardFormDialog'
import { CardsList } from '@/features/cards/CardsList'

function App() {
  return (
    <div className="mx-auto max-w-3xl space-y-8 p-4 sm:p-6">
      <header>
        <h1 className="text-2xl font-semibold">Bolsillito</h1>
        <p className="text-muted-foreground text-sm">Cuentas y tarjetas</p>
      </header>

      <AccountsList />
      <CardsList />

      <AccountFormDialog />
      <CardFormDialog />
    </div>
  )
}

export default App
