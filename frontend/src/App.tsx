import { useEffect } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'

import { Nav } from '@/app/Nav'
import { AccountsPage } from '@/app/pages/AccountsPage'
import { DashboardPage } from '@/app/pages/DashboardPage'
import { InvestmentsPage } from '@/app/pages/InvestmentsPage'
import { LandingPage } from '@/app/pages/LandingPage'
import { LoginPage } from '@/app/pages/LoginPage'
import { RecurringExpensesPage } from '@/app/pages/RecurringExpensesPage'
import { RegisterPage } from '@/app/pages/RegisterPage'
import { TransactionsPage } from '@/app/pages/TransactionsPage'
import { ThemeToggle } from '@/app/ThemeToggle'
import { Button } from '@/components/ui/button'
import { useSyncRecurringExpenses } from '@/lib/api/recurringExpenses'
import { useAuthStore } from '@/stores/authStore'

function App() {
  const navigate = useNavigate()
  const token = useAuthStore((state) => state.token)
  const user = useAuthStore((state) => state.user)
  const clearAuth = useAuthStore((state) => state.clearAuth)
  const syncRecurringExpenses = useSyncRecurringExpenses()

  const handleLogout = () => {
    clearAuth()
    navigate('/login')
  }

  // No hay scheduler/cron en el backend -- los gastos fijos se generan de forma perezosa acá,
  // una vez por sesión autenticada (ver services/recurring_expenses.py, idempotente).
  useEffect(() => {
    if (token) syncRecurringExpenses.mutate()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- disparar una vez por sesión logueada
  }, [token])

  if (!token) {
    return (
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/registro" element={<RegisterPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    )
  }

  return (
    <div className="bg-background min-h-screen pb-16 sm:pb-0">
      <header className="border-border bg-background/80 sticky top-0 z-40 flex items-start justify-between gap-3 border-b p-4 backdrop-blur sm:p-6">
        <div className="min-w-0">
          <h1 className="font-jakarta truncate text-2xl font-bold tracking-tight">Bolsillito</h1>
          <p className="text-muted-foreground text-sm">Tus finanzas personales, sin planillas</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className="text-muted-foreground hidden max-w-[10rem] truncate text-sm sm:inline">
            {user?.username}
          </span>
          <ThemeToggle />
          <Button variant="ghost" size="sm" onClick={handleLogout}>
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
            <Route path="/gastos-fijos" element={<RecurringExpensesPage />} />
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
