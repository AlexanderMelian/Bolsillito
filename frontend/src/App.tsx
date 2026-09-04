import { Route, Routes } from 'react-router-dom'

import { Nav } from '@/app/Nav'
import { AccountsPage } from '@/app/pages/AccountsPage'
import { DashboardPage } from '@/app/pages/DashboardPage'
import { InvestmentsPage } from '@/app/pages/InvestmentsPage'
import { TransactionsPage } from '@/app/pages/TransactionsPage'

function App() {
  return (
    <div className="pb-16 sm:pb-0">
      <header className="border-border border-b p-4 sm:p-6">
        <h1 className="text-2xl font-semibold">Bolsillito</h1>
        <p className="text-muted-foreground text-sm">Tus finanzas personales, sin planillas</p>
      </header>

      <div className="sm:hidden">
        <Nav />
      </div>

      <div className="mx-auto flex max-w-5xl gap-6 p-4 sm:p-6">
        <div className="hidden shrink-0 sm:block">
          <Nav />
        </div>
        <main className="max-w-3xl flex-1 space-y-8">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/cuentas" element={<AccountsPage />} />
            <Route path="/movimientos" element={<TransactionsPage />} />
            <Route path="/inversiones" element={<InvestmentsPage />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default App
