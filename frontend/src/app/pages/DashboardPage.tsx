import { CashFlowChart } from '@/features/dashboard/CashFlowChart'
import { ExchangeRatesSection } from '@/features/dashboard/ExchangeRatesSection'
import { SpendingByCategoryChart } from '@/features/dashboard/SpendingByCategoryChart'
import { SummaryCards } from '@/features/dashboard/SummaryCards'

export function DashboardPage() {
  return (
    <div className="space-y-8">
      <SummaryCards />
      <SpendingByCategoryChart />
      <CashFlowChart />
      <ExchangeRatesSection />
    </div>
  )
}
