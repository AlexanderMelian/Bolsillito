export function formatCurrency(amount: string, currency: string): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency }).format(Number(amount))
}
