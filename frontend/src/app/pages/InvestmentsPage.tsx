import { AssetFormDialog } from '@/features/investments/AssetFormDialog'
import { AssetsList } from '@/features/investments/AssetsList'
import { InvestmentTransactionFormDialog } from '@/features/investments/InvestmentTransactionFormDialog'
import { PortfolioSummary } from '@/features/investments/PortfolioSummary'

export function InvestmentsPage() {
  return (
    <div className="space-y-8">
      <PortfolioSummary />
      <AssetsList />

      <AssetFormDialog />
      <InvestmentTransactionFormDialog />
    </div>
  )
}
