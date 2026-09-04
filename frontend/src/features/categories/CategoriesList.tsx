import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useCategories, useDeleteCategory } from '@/lib/api/categories'
import { useUiStore } from '@/stores/uiStore'

const KIND_LABELS = { expense: 'Gasto', income: 'Ingreso', transfer: 'Transferencia' } as const

export function CategoriesList() {
  const { data: categories, isLoading, isError } = useCategories()
  const deleteCategory = useDeleteCategory()
  const openCategoryModal = useUiStore((state) => state.openCategoryModal)

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-medium">Categorías</h2>
        <Button size="sm" variant="outline" onClick={() => openCategoryModal()}>
          Nueva categoría
        </Button>
      </div>

      {isLoading && <p className="text-muted-foreground text-sm">Cargando categorías…</p>}
      {isError && (
        <p className="text-destructive text-sm">No se pudieron cargar las categorías.</p>
      )}
      {categories?.length === 0 && (
        <p className="text-muted-foreground text-sm">Todavía no cargaste ninguna categoría.</p>
      )}

      <ul className="flex flex-wrap gap-2">
        {categories?.map((category) => (
          <li key={category.id}>
            <Badge variant="outline" className="gap-1.5 py-1.5 pr-1">
              {category.icon} {category.name}
              <span className="text-muted-foreground">· {KIND_LABELS[category.kind]}</span>
              <button
                type="button"
                aria-label={`Eliminar ${category.name}`}
                className="hover:text-destructive ml-1"
                onClick={() => deleteCategory.mutate(category.id)}
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
