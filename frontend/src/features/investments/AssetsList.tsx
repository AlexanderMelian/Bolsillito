import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useAssets, useDeleteAsset } from '@/lib/api/assets'
import { useUiStore } from '@/stores/uiStore'

export function AssetsList() {
  const { data: assets, isLoading, isError } = useAssets()
  const deleteAsset = useDeleteAsset()
  const openAssetModal = useUiStore((state) => state.openAssetModal)
  const openInvestmentModal = useUiStore((state) => state.openInvestmentModal)

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-medium">Activos</h2>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => openAssetModal()}>
            Nuevo activo
          </Button>
          <Button size="sm" onClick={() => openInvestmentModal()}>
            Nueva transacción
          </Button>
        </div>
      </div>

      {isLoading && <p className="text-muted-foreground text-sm">Cargando activos…</p>}
      {isError && <p className="text-destructive text-sm">No se pudieron cargar los activos.</p>}
      {assets?.length === 0 && (
        <p className="text-muted-foreground text-sm">Todavía no cargaste ningún activo.</p>
      )}

      <ul className="flex flex-wrap gap-2">
        {assets?.map((asset) => (
          <li key={asset.id}>
            <Badge variant="outline" className="gap-1.5 py-1.5 pr-1">
              {asset.ticker} · {asset.name}
              <span className="text-muted-foreground">({asset.currency})</span>
              <button
                type="button"
                aria-label={`Eliminar ${asset.ticker}`}
                className="hover:text-destructive ml-1"
                onClick={() => deleteAsset.mutate(asset.id)}
              >
                ×
              </button>
            </Badge>
          </li>
        ))}
      </ul>
    </section>
  )
}
