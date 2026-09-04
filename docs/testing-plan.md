# Plan de Pruebas — Bolsillito

> **Estado:** 130 tests backend (100% cobertura de línea en `app/`, gate `--cov-fail-under=95`)
> + 52 tests frontend (gate 80% líneas/statements/funcs, 70% branches) — Módulos 1, 2 y 3.
> Ambas suites en verde. Ver `backend/tests/` y `frontend/src/**/*.test.{ts,tsx}`.

## Backend (pytest)

**Herramientas:** `pytest`, `pytest-asyncio` (`asyncio_mode=auto`, loop de scope `session`, ver
`backend/pytest.ini`), `pytest-cov`, `httpx.AsyncClient` (contra la app FastAPI sin levantar un
server real), y **una base Postgres de test separada** (`bolsillito_test`, creada por
`db/init/01_create_test_db.sql` en el mismo contenedor que la de desarrollo) — **no SQLite**,
porque `NUMERIC`, `ENUM` y varios `CheckConstraint` de este proyecto no se comportan igual en
SQLite y esconderían bugs reales (así se encontró el bug de `values_callable` en los ENUM
durante Fase 1 — ver `agents.md`).

Cada test corre dentro de un `SAVEPOINT` que se descarta al terminar (`backend/tests/conftest.py`,
fixture `db_session` con `join_transaction_mode="create_savepoint"`), así quedan aislados entre
sí aunque el código bajo prueba haga su propio `session.commit()` — no hace falta recrear las
tablas en cada test. El fixture `client` (mismo archivo) monta un `AsyncClient` contra la app
real con `get_session` overrideado para usar esa misma `db_session`: los tests de endpoint
ejercitan el stack completo (router → schema → service → DB) sin mockear nada.

### Organización por archivo

| Archivo | Qué cubre |
|---|---|
| `test_billing_cycle.py` | `services/billing_cycle.py` en aislamiento (sin DB): asignación de ciclo, redondeo de cuotas, fin de mes, cruce de año. |
| `test_models.py` | Constraints del modelo contra Postgres real: `CheckConstraint`, `UniqueConstraint`, cascadas `ON DELETE`, que los ENUM persistan el `.value` y no el `.name`. |
| `test_config.py`, `test_database.py`, `test_health.py` | Settings, `get_session`, endpoint de salud. |
| `test_accounts_api.py`, `test_cards_api.py`, `test_categories_api.py` | CRUD de Módulo 1: soft-delete de cuentas, validación de ciclo de tarjetas de crédito, 409 por FK. |
| `test_transactions_api.py` | Efecto sobre el saldo por tipo de movimiento (ingreso, gasto, gasto con débito, gasto con crédito, transferencia), todas las validaciones cruzadas (tarjeta≠cuenta, categoría≠tipo, moneda≠cuenta), filtros de listado, reversión de saldo al borrar, bloqueo de borrado si está ligado a un plan de cuotas. |
| `test_installment_plans_api.py` | Generación de cuotas y resúmenes al comprar, que no toque el saldo, rechazo de tarjeta de débito, borrado en cascada (cuotas + transacción de registro). |
| `test_card_statements_api.py` | Cálculo de `total_amount`/`status` combinando cuotas + gastos de pago único, incluida la regresión de "un gasto único a crédito tiene que generar su propio resumen"; flujo de pago (débito real de la cuenta, no se puede pagar dos veces ni un resumen en `$0`). |
| `test_exchange_rates_api.py` | Upsert de cotizaciones (mismo par+fecha actualiza en vez de fallar). |
| `test_dashboard_api.py` | Consolidación multi-moneda (directa, inversa, sin cotización), exclusión de pagos de resumen en los reportes de ingreso/gasto, agrupación por categoría, proyección de flujo de caja (incluye meses en `$0`, excluye resúmenes pagados). |

### Patrones a seguir en tests nuevos

- **`CheckConstraint`/`UniqueConstraint`/FK nuevos** → agregar el test de integración
  correspondiente en `test_models.py` (intentar la violación, esperar `IntegrityError`).
- **FK con `ondelete="CASCADE"`** → la `relationship()` del lado "uno" necesita
  `passive_deletes=True` (ver `agents.md`) y un test que borre el padre y verifique que el hijo
  desaparece.
- **Todo endpoint de escritura nuevo** → al menos un test de integración end-to-end (vía
  `client`, no llamando servicios directo) más los casos de error específicos (404 de cada FK
  referenciada, 422 de cada validación, 409 si aplica).
- **Lógica de negocio no trivial** (cálculo de fechas, montos, agregaciones) → función pura en
  `services/`, testeada sin DB primero (`test_billing_cycle.py` es el ejemplo de referencia),
  *además* del test de integración que verifica que el endpoint la use bien.

**Gate:** `--cov-fail-under=95` en `pytest.ini`, hoy en 100%. Si un módulo nuevo lo baja, se sube
la cobertura de ese módulo antes de seguir — no se baja el umbral.

## Frontend (Vitest + Testing Library)

**Herramientas:** Vitest con cobertura v8, `@testing-library/react` + `@testing-library/user-event`,
`renderWithProviders` (`src/test-utils.tsx`, un `QueryClient` nuevo por test con `retry: false`).
No hay MSW instalado — el `fetch` global se mockea directo con `vi.stubGlobal('fetch', vi.fn(...))`
en cada `describe`, matcheando por URL y método.

**Trampa recurrente:** el segundo argumento de `fetch` (`init`) **nunca** es `undefined` — el
cliente (`lib/api/client.ts`) siempre manda al menos `{ headers: {...} }`. Para distinguir un GET
en el mock hay que chequear `init.method === undefined`, no `!init` (un `!init` siempre da
`false` y el branch de GET nunca matchea). Patrón correcto:
```ts
if (url.endsWith('/api/v1/accounts') && (!init || init.method === undefined)) { /* GET */ }
```

**Selects de shadcn (Radix)**: jsdom no implementa `hasPointerCapture`/`scrollIntoView`, que
Radix necesita para manejar el puntero. Los polyfills ya están en `src/setupTests.ts` — si un
test nuevo interactúa con un `Select` y tira un error de puntero, revisar que ese archivo se
esté cargando (`vitest.config.ts` → `setupFiles`).

**Gráficos (Recharts)**: `ResponsiveContainer` no mide nada en jsdom porque no hay layout real,
así que las barras SVG no se pueden verificar desde un test. Los componentes de
`features/dashboard/` se testean por sus estados (carga / error / vacío) y los textos/títulos
correctos según los datos mockeados, no por el contenido del `<svg>`.

### Organización por área

| Área | Archivos de test | Qué cubren |
|---|---|---|
| Cuentas | `AccountsList`, `AccountFormDialog` | Alta, edición (remount por `key`, ver `agents.md`), borrado, apertura de modal en modo crear/editar. |
| Tarjetas | `CardsList`, `CardFormDialog`, `CardStatementsDialog` | Alta con campos condicionales de ciclo (crédito), borrado, listado de resúmenes con su estado, pago. |
| Categorías | `CategoriesList`, `CategoryFormDialog` | Alta, borrado. |
| Movimientos | `TransactionsList`, `TransactionFormDialog`, `InstallmentPurchaseDialog` | Campos condicionales según `type` (cuenta destino solo en transferencia, tarjeta solo en gasto), preview de monto por cuota, borrado deshabilitado si está ligado a un plan de cuotas. |
| Dashboard | `SummaryCards`, `SpendingByCategoryChart`, `CashFlowChart`, `ExchangeRatesSection` | Estados de carga/error/vacío, formato de montos, alta de cotización. |
| Ruteo | `App.test.tsx` | Navegación entre `/`, `/cuentas`, `/movimientos`. |
| API client | `lib/api/client.test.ts` | `ApiError` en respuestas no-OK, `undefined` en `204`, mensaje genérico si el body de error no es JSON. |

**Gate:** 80% líneas/statements/funcs, 70% branches (`vitest.config.ts` → `coverage.thresholds`).
Más laxo que el backend a propósito: hay bastante código de vendor (shadcn, Radix) que igual se
instrumenta cuando un test lo importa indirectamente, y no vale la pena perseguir 100% ahí.

## CI (GitHub Actions)

**No implementado todavía** — ver `agents.md` § Pendientes. El plan original:
- Job `backend`: instala dependencias → levanta Postgres como servicio del workflow → `pytest`.
- Job `frontend`: `npm ci` → `npm run lint` → `npm run test` → `npm run build`.
- Ambos en cada PR contra `develop` y `main`.

Hasta que se implemente, la verificación es manual: `docker compose up -d db` +
`backend/venv/bin/pytest` + `cd frontend && npm run test && npm run build` antes de cada commit
(así se viene haciendo en los Módulos 1–3).
