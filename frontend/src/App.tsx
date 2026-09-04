import { Navigate, Route, Routes } from 'react-router-dom'

import { Nav } from '@/app/Nav'
import { AccountsPage } from '@/app/pages/AccountsPage'
import { DashboardPage } from '@/app/pages/DashboardPage'
import { InvestmentsPage } from '@/app/pages/InvestmentsPage'
import { LoginPage } from '@/app/pages/LoginPage'
import { RegisterPage } from '@/app/pages/RegisterPage'
import { TransactionsPage } from '@/app/pages/TransactionsPage'
import { ThemeToggle } from '@/app/ThemeToggle'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/stores/authStore'

function App() {
  const token = useAuthStore((state) => state.token)
  const user = useAuthStore((state) => state.user)
  const clearAuth = useAuthStore((state) => state.clearAuth)

  if (!token) {
    return (
      <Routes>
        <Route path="/registro" element={<RegisterPage />} />
        <Route path="*" element={<LoginPage />} />
      </Routes>
    )
  }

  return (
    <div className="pb-16 sm:pb-0">
      <header className="border-border flex items-start justify-between border-b p-4 sm:p-6">
        <div>
          <h1 className="text-2xl font-semibold">Bolsillito</h1>
          <p className="text-muted-foreground text-sm">Tus finanzas personales, sin planillas</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground hidden text-sm sm:inline">{user?.username}</span>
          <ThemeToggle />
          <Button variant="ghost" size="sm" onClick={clearAuth}>
            Salir
          </Button>
        </div>
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
            <Route path="/login" element={<Navigate to="/" replace />} />
            <Route path="/registro" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default App
