# Plan de Pruebas — Bolsillito

## Backend (pytest)

**Herramientas:** `pytest`, `pytest-asyncio`, `httpx.AsyncClient` (contra la app FastAPI sin
levantar un server real), una base de datos Postgres de test separada (o `testcontainers` /
un contenedor Docker efímero) — **no SQLite**, porque `NUMERIC`, `ENUM` y algunos
`CheckConstraint` de este proyecto no se comportan igual en SQLite y esconderían bugs reales.

**Prioridad 1 — lógica no trivial (unit tests puros, sin DB):**
- `services/billing_cycle.py`:
  - Compra el día exacto del cierre (`purchase.day == closing_day`) → cae en el ciclo actual.
  - Compra un día después del cierre → cae en el ciclo siguiente.
  - `closing_day=31` con una compra en febrero → no debe romper (`_safe_day`).
  - `payment_day` menor que `closing_day` (vencimiento cruza a mes siguiente) vs mayor
    (vencimiento en el mismo mes del cierre).
  - `build_installment_amounts`: la suma de las cuotas generadas siempre es exactamente igual a
    `total_amount` (ej. `100 / 3` no debe perder $0.01 por redondeo).
  - `build_installment_closing_dates`: N cuotas generan N fechas de cierre consecutivas y
    correctas cruzando fin de año (diciembre → enero).

**Prioridad 2 — integración (con DB de test):**
- Alta de transferencia: se crea una única `Transaction` tipo `transfer`; el saldo de la cuenta
  origen baja y el de destino sube en la misma operación atómica.
- Alta de compra en cuotas: se crea `InstallmentPlan` + N `InstallmentItem`, y **no** se
  modifica el saldo de ninguna cuenta bancaria en ese momento.
- Cierre de ciclo: al pasar `closing_date`, un `CardStatement` en `open` pasa a `closed` con
  `total_amount` = suma de sus `installment_items` + gastos de pago único del período.
- Pago de resumen: registrar el pago de un `CardStatement` crea una `Transaction` tipo `expense`
  contra `payment_account_id` y **recién ahí** reduce el saldo bancario; el `status` pasa a
  `paid`.
- Portafolio de inversiones: comprar en dos lotes a distinto precio y verificar que el precio
  promedio ponderado calculado sea correcto; vender parte de la posición y verificar que la
  cantidad restante se actualice sin afectar el precio promedio de lo que queda.

**Cobertura mínima esperada antes de cerrar cada módulo (Fase 2):** los tests de Prioridad 1 del
módulo correspondiente en verde, más al menos un test de integración end-to-end por endpoint de
escritura.

## Frontend (Vitest + React Testing Library)

- Componentes de formulario/modal (`TransactionModal`, `InstallmentModal`): validación de campos
  requeridos, que el submit llame al endpoint correcto según el tipo elegido (income/expense/
  transfer/cuotas).
- `UpcomingPaymentsCard` y `CashFlowChart`: dado un mock de la respuesta de la API de proyección,
  se renderizan los montos y meses esperados (evita regresiones silenciosas en el mapeo de
  datos → gráfico).
- No se testea Recharts en sí (librería externa ya testeada), solo que reciba los `props`
  correctos.

## CI (GitHub Actions)

- Job `backend`: `pip install -r requirements.txt` → levantar Postgres como servicio del
  workflow → `pytest`.
- Job `frontend`: `npm ci` → `npm run lint` → `npm run test` → `npm run build` (falla el build
  si hay errores de TypeScript).
- Ambos jobs corren en cada PR contra `develop` y `main`.
