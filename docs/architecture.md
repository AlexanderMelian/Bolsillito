# Arquitectura Técnica — Bolsillito

> **Estado:** los 4 módulos del MVP implementados (Cuentas/Tarjetas, Transacciones/Cuotas,
> Dashboard/Reportes, Inversiones) más el Módulo 5 (multi-usuario). Este documento describe la
> arquitectura tal como quedó construida, no solo la planeada en Fase 0 — ver `agents.md` §
> Pendientes para lo que queda afuera del alcance actual.

## 1. Componentes

```
┌─────────────────────┐        HTTPS/JSON         ┌──────────────────────┐        asyncpg        ┌──────────────┐
│   Frontend (SPA)     │ ────────────────────────▶ │   Backend (FastAPI)   │ ─────────────────────▶ │  PostgreSQL   │
│  React + Vite + TS   │ ◀──────────────────────── │  SQLAlchemy 2.0 async │ ◀───────────────────── │               │
│  Tailwind + shadcn/ui│      REST + OpenAPI        │  Pydantic v2 schemas  │                        └──────────────┘
└─────────────────────┘                            └──────────────────────┘
        │                                                     │
        │ fetch vía lib/api (TanStack Query)                  │ Alembic (migraciones)
        ▼                                                     ▼
  stores/ (Zustand, estado de UI)                    services/ (lógica de negocio:
                                                        billing_cycle, balances,
                                                        card_statements, exchange_rates,
                                                        investments)
```

Sin Open Banking: toda la carga de datos entra por los endpoints REST desde formularios/modales
del frontend. No hay integraciones con bancos ni brokers.

## 2. Flujo de datos entre capas

1. El frontend nunca escribe directamente en la base de datos ni conoce el esquema SQL — solo
   conoce los DTOs Pydantic expuestos en `docs/api-spec.md` / `/docs` (OpenAPI).
2. Los **routers** de FastAPI validan entrada (Pydantic), delegan la lógica de negocio a la
   capa de **services** (ej. `services/billing_cycle.py`) y devuelven DTOs de salida.
3. Los **services** son funciones puras o casi-puras sobre objetos de dominio (fechas, montos),
   fácilmente testeables sin necesidad de una base de datos real — ver `backend/app/billing_cycle.py`.
4. Los **modelos SQLAlchemy** (`backend/app/models.py`) son la única fuente de verdad del
   esquema; Alembic genera migraciones a partir de ellos (no se edita `db/schema.sql` a mano en
   producción, ese archivo es solo documentación/referencia inicial).

## 3. Justificación de decisiones técnicas

- **SQLAlchemy asíncrono (`AsyncSession` + `asyncpg`) en vez de síncrono**: FastAPI corre sobre
  un event loop async; usar sesiones síncronas de SQLAlchemy bloquearía ese loop en cada query,
  serializando requests que deberían poder atenderse concurrentemente (ej. el dashboard hace
  varias consultas de agregación en paralelo). El costo (mayor complejidad en manejo de
  sesiones/transacciones) se justifica porque el dashboard es el caso de uso más frecuente y más
  sensible a latencia.
- **Manejo de sesiones**: una `AsyncSession` por request vía dependencia de FastAPI
  (`Depends(get_session)`), con `expire_on_commit=False` para poder serializar el objeto
  devuelto sin una query extra tras el commit. Nunca se comparte una sesión entre requests.
- **`NUMERIC(12,2)` para dinero, `NUMERIC(20,8)` para inversiones**: `float` introduce errores de
  redondeo inaceptables en dinero (ej. `0.1 + 0.2 != 0.3`); `Decimal` + `NUMERIC` en Postgres
  garantiza aritmética exacta. Las inversiones (especialmente cripto) necesitan más decimales de
  precisión en cantidad y precio que el dinero "de caja".
- **`InstallmentItem` por cuota (no un campo `current_month` en `Installments`)**: para poder
  proyectar flujo de caja futuro (pregunta de negocio #3 del brief) hace falta saber, para cada
  cuota individual, a qué mes/ciclo pertenece — un solo campo de "mes actual" no permite
  consultar "cuánto debo en cuotas los próximos 6 meses".
- **`CardStatement` como entidad propia**: es lo que realmente se paga y lo que descuenta el
  saldo bancario (decisión de negocio #2). Sin esta entidad, "pagar la tarjeta" no tendría un
  objeto claro al cual asociar la transacción de pago.
- **Categorías como tabla, no string libre**: permite iconos, tipo (income/expense) y evita
  categorías duplicadas por typos (ej. "Comida" vs "comida"), importante en carga 100% manual.
- **JWT stateless (`PyJWT`) en vez de sesiones server-side**: no hay tabla de sesiones que
  limpiar ni estado compartido entre workers — cualquier instancia del backend puede validar un
  token con solo `SECRET_KEY`. El costo (no se puede invalidar un token antes de que expire) es
  aceptable para "algo sencillo" con pocos usuarios de confianza (ver `agents.md` § Decisiones
  de negocio #4); si hiciera falta revocar sesiones, la alternativa más simple sería agregar una
  columna `token_version` en `User` y validarla en `get_current_user`.
- **`user_id` como columna en casi todas las tablas, filtrado en cada query, en vez de un
  esquema Postgres por usuario o row-level security**: más simple de razonar y de testear con el
  stack actual (SQLAlchemy async + Alembic), a costa de tener que acordarse de filtrar/validar
  ownership en cada endpoint nuevo — mitigado documentando la convención en `agents.md` §
  Reglas de estilo y con tests de aislamiento cruzado (`test_auth_api.py`, ver
  `docs/testing-plan.md`).

## 4. Estructura del backend (`app/`)

```
app/
  main.py            # instancia FastAPI, CORS, registro de routers, handler global de IntegrityError -> 409
  config.py          # Settings (pydantic-settings), lee backend/.env
  database.py        # engine async + get_session (dependencia de FastAPI)
  models.py          # SQLAlchemy 2.0 -- única fuente de verdad del esquema
  schemas/           # DTOs Pydantic, un archivo por recurso (accounts.py, cards.py, ...)
  routers/           # endpoints, un archivo por recurso; validan con el schema y delegan a services/
  services/          # lógica de negocio sin FastAPI de por medio (testeable sin HTTP):
                      #   auth.py             -- hash/verify de password, JWT, dependencia get_current_user
                      #   billing_cycle.py    -- ciclos de facturación y reparto de cuotas
                      #   balances.py         -- efecto de una transacción sobre el saldo
                      #   card_statements.py  -- alta/cálculo de resúmenes, flujo de pago
                      #   exchange_rates.py   -- conversión de moneda
                      #   investments.py      -- costo promedio ponderado, posición, ganancia realizada
```

**Autenticación y aislamiento multi-tenant**: `services/auth.py` expone `get_current_user`, una
dependencia de FastAPI (`HTTPBearer(auto_error=False)` + decode manual del JWT) que todo router
protegido declara como `current_user: User = Depends(get_current_user)`. A partir de ahí, cada
router es responsable de dos cosas: (1) filtrar toda lista/`GET` por `.where(Model.user_id ==
current_user.id)`, y (2) validar ownership (no solo existencia) de cualquier FK que llegue en el
body de un create/update — ver el detalle y la convención de 404-no-403 en `agents.md` § Reglas
de estilo y `docs/api-spec.md` § Autenticación.

Los `routers` nunca calculan directamente: arman la respuesta a partir de lo que devuelven los
`services`. Esto es lo que permite testear, por ejemplo, `build_installment_amounts` con
`pytest` puro (sin DB, sin HTTP) y por separado testear que el endpoint efectivamente use ese
resultado — ver `docs/testing-plan.md`.

**Cálculo vs. almacenamiento**: varias veces se decidió calcular en el momento de la consulta en
vez de mantener un campo desnormalizado: `CardStatement.total_amount`/`status` (se recalculan en
cada `GET`, salvo que ya esté `paid`), los reportes del dashboard, y la posición/costo
promedio/ganancia realizada de una inversión (`services/investments.py`). La alternativa
—mantenerlos actualizados en cada escritura que los afecta— es más rápida de leer pero exige
acordarse de tocarlos desde cada punto de escritura relevante (alta de transacción, borrado,
edición...); ya hubo un bug real por este motivo (gastos de pago único que no generaban su
`CardStatement`, ver `agents.md`) y la superficie de "puntos que hay que acordarse de tocar" solo
crece. Se prioriza la certeza de que el dato mostrado es correcto sobre la performance de
lectura, razonable para el volumen de datos de una app personal.

**FK cruda vs. `relationship()`**: `Transaction.investment_transaction_id` es una FK simple, sin
un `relationship()` ORM que la acompañe (a diferencia de `InstallmentPlan.items`, que sí tiene
uno). La consecuencia concreta: el unit-of-work de SQLAlchemy ordena automáticamente los
`DELETE` en cascada cuando hay un `relationship()` de por medio, pero **no** cuando dos objetos
comparten una FK sin relación ORM explícita — hay que borrar el lado que referencia (acá, la
`Transaction` vinculada) con un `DELETE` inmediato (`session.execute(delete(...))`) antes de
borrar el lado referenciado, en vez de confiar en `session.delete()` para ambos. Se encontró
como bug real escribiendo `DELETE /investment-transactions/{id}` — ver `agents.md`.

## 5. Estructura del frontend (`frontend/src/`)

```
frontend/src/
  app/
    Nav.tsx           # navegación (bottom bar en mobile, sidebar en desktop)
    pages/            # una página por ruta -- solo componen features + sus dialogs
                       #   LoginPage.tsx / RegisterPage.tsx -- fuera del shell autenticado
  features/<recurso>/ # componentes de UI por recurso (accounts, cards, categories,
                       # transactions, dashboard), incluye sus *.test.tsx
  components/ui/      # shadcn/ui (no se edita a mano; se regenera con `shadcn add`)
  lib/
    api/client.ts     # apiRequest: agrega el Bearer token del authStore y desloguea en un 401
    api/auth.ts        # register/login + hooks useRegister/useLogin (guardan el token al resolver)
    api/<recurso>.ts  # fetch + hooks de TanStack Query, un archivo por recurso -- espejo
                       # de los routers del backend
    utils/            # formatCurrency, etc.
  stores/
    uiStore.ts        # Zustand -- qué modal está abierto y, si aplica, qué entidad se edita
    authStore.ts       # Zustand + persist -- token y user actuales (localStorage)
  test-utils.tsx       # renderWithProviders (QueryClient nuevo por test)
```

**Ruteo y auth gate**: `react-router-dom` con `BrowserRouter` en `main.tsx`. `App.tsx` lee
`authStore`: sin `token`, solo monta `/login` y `/registro` (cualquier otra ruta cae en
`LoginPage`); con `token`, monta el shell normal —`/` (Dashboard), `/cuentas` (Cuentas +
Tarjetas + Categorías), `/movimientos` (Transacciones), `/inversiones`— y `/login`/`/registro`
redirigen a `/`. No hay un router guard por-ruta más granular ni roles: es un gate binario a
nivel de toda la app, consistente con "algo sencillo" (`agents.md` § Decisiones de negocio #4).
El logout (botón "Salir" en el header) es local: limpia `authStore`, no hay endpoint de logout
en el backend (un JWT no se puede invalidar server-side sin estado adicional, ver más arriba).

**Gráficos**: Recharts, siguiendo la skill `dataviz` del proyecto. Cada serie de magnitud
(gasto por categoría, cuotas comprometidas) usa un solo hue secuencial (`--chart-1`, azul) en
vez de un color por categoría — evita el anti-patrón de "arcoíris" y no hace falta leyenda para
una sola serie. La paleta categórica completa (`--chart-1..5` en `index.css`) está validada con
el script de la skill para light y dark; reemplaza los tokens grises (chroma 0) que deja
`shadcn init` por defecto, que no sirven para graficar nada.

**Tema oscuro/claro**: `stores/themeStore.ts` (Zustand + `persist`) guarda la preferencia
(`light`/`dark`/`system`) en `localStorage` y aplica/quita la clase `.dark` en `<html>`; en modo
`system` sigue en vivo el cambio de preferencia del SO vía
`matchMedia('(prefers-color-scheme: dark)')`. El toggle vive en `app/ThemeToggle.tsx`, en el
header junto al resto de los controles de sesión.

## 6. Entornos

- `dev`: Docker Compose levanta `db` (postgres:16), `pgadmin`, `backend` (uvicorn --reload) y
  `frontend` (vite dev server), todos con hot-reload vía bind mounts.
- `prod`: `docker-compose.prod.yml` construye imágenes optimizadas (multi-stage build del
  frontend servido como estáticos, backend con Gunicorn+Uvicorn workers), sin bind mounts.
- Variables de entorno (`.env`, no versionado): `DATABASE_URL`, `VITE_API_URL`,
  `DEFAULT_CURRENCY` (moneda de referencia para consolidar patrimonio, ver `exchange_rates`).
