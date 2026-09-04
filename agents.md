# Agent Instructions & Project Context — Bolsillito

Bolsillito es una app de finanzas personales (cuentas, tarjetas, cuotas de crédito,
movimientos, inversiones) con carga 100% manual — sin integraciones bancarias (Open Banking).
Monorepo: **FastAPI** (backend) + **React (Vite + TypeScript + Tailwind + shadcn/ui)** (frontend),
**PostgreSQL** como base de datos.

Ver `docs/architecture.md`, `docs/api-spec.md` y `db/schema.sql` para el diseño completo.

---

## 🛠️ Comandos del proyecto

### Backend (FastAPI)
- **Crear entorno virtual:** `python -m venv backend/venv` (usar siempre el `python` del
  sistema — apunta a 3.14.6, no crear ni buscar otra versión)
- **Activar entorno:** `source backend/venv/bin/activate`
- **Instalar dependencias:** `pip install -r backend/requirements.txt`
- **Ejecutar servidor de desarrollo:** `uvicorn app.main:app --reload` (desde `backend/`)
- **Crear una migración:** `alembic revision --autogenerate -m "mensaje"` (desde `backend/`)
  — si la migración agrega un `pg_enum` nuevo, agregar a mano `op.execute("DROP TYPE IF EXISTS
  <nombre>")` en `downgrade()`: Alembic no genera el `DROP TYPE` de los ENUM de Postgres
  automáticamente, y sin eso un `downgrade` + `upgrade` posterior falla con
  `type "..." already exists` (nos pasó armando la migración inicial).
- **Aplicar migraciones:** `alembic upgrade head` (desde `backend/`)
- **Ejecutar tests:** `pytest` (desde `backend/`; corre con cobertura y falla si baja del 95%
  — ver `pytest.ini`. Requiere la base `bolsillito_test` — la crea sola `docker compose up db`
  en un volumen nuevo vía `db/init/`, pero si el volumen ya existía de antes hay que crearla a
  mano una vez: `docker compose exec db psql -U bolsillito -d bolsillito -c "CREATE DATABASE
  bolsillito_test;"`)
- Si un modelo nuevo agrega una FK con `ondelete="CASCADE"`, la `relationship()` del lado "uno"
  necesita `passive_deletes=True` (ver `Account.cards` en `app/models.py`) — si no, el ORM
  intenta poner la FK en `NULL` antes de que Postgres borre en cascada, y falla contra una
  columna `NOT NULL`. Agregar siempre un test que borre el padre y verifique que el hijo
  desaparece.

### Frontend (React + Vite)
- **Instalar dependencias:** `npm install` (desde `frontend/`)
- **Ejecutar servidor de desarrollo:** `npm run dev` (desde `frontend/`)
- **Compilar para producción:** `npm run build`
- **Ejecutar tests:** `npm run test` (Vitest + Testing Library, con cobertura; gate en
  `vitest.config.ts` — 80% líneas/statements/funcs, 70% branches)

### Docker
- **Levantar entorno de desarrollo (hot-reload):** `docker compose up`
- **Levantar entorno de producción:** `docker compose -f docker-compose.prod.yml up -d --build`
- **Detener y eliminar contenedores:** `docker compose down` (agregar `-v` para borrar también
  el volumen de datos)

### Atajos (Makefile)
- `make install` — instala dependencias de backend y frontend
- `make migrate` — aplica migraciones de Alembic
- `make dev` — levanta backend + frontend en modo desarrollo
- `make test` — corre pytest + vitest

---

## 📐 Reglas de estilo y buenas prácticas

### Backend (Python / FastAPI)
- Python 3.14, type hints en todo el código, sin `Any` salvo justificación explícita.
- **Pydantic v2** para validación (schemas separados de los modelos SQLAlchemy: `*Create`,
  `*Update`, `*Read`).
- **SQLAlchemy 2.0** estilo `Mapped`/`mapped_column`, **async** (`asyncpg` + `AsyncSession`) —
  nunca sesiones síncronas.
- Montos monetarios: siempre `Decimal` + `NUMERIC(12,2)` en DB. **Nunca `float` para dinero.**
  Cantidades/precios de inversión: `NUMERIC(20,8)`.
- Estructura modular: `app/models.py` (SQLAlchemy, un solo archivo por ahora), `app/schemas/`
  (Pydantic, un archivo por recurso: `accounts.py`, `cards.py`, ...), `app/routers/` (un
  archivo por recurso), `app/services/` (lógica de negocio, ej. `billing_cycle.py`).
- La lógica de ciclos de facturación y cuotas vive en `app/services/billing_cycle.py` — no debe
  duplicarse en routers.
- Errores: los `CheckConstraint`/`UniqueConstraint`/FK del modelo son la última línea de
  defensa, pero cuando se pueden validar antes de tocar la DB (ej. tarjeta de crédito sin
  `closing_day`/`payment_day`) se valida también en el schema Pydantic (`model_validator`) para
  devolver 422 con un mensaje claro en vez de un 409 genérico. Ver `app/schemas/cards.py` y el
  handler global de `IntegrityError` → 409 en `app/main.py`.
- **Bug de Python 3.14 a tener en cuenta:** un campo Pydantic llamado igual que su tipo (ej.
  `date: date`, sobre todo en su forma `date: date | None`) puede romper en runtime con
  `TypeError: unsupported operand type(s) for |: 'NoneType' and 'NoneType'` -- la nueva
  resolución diferida de anotaciones de 3.14 (`annotationlib`, PEP 649) a veces resuelve el
  nombre del tipo contra el propio atributo de la clase en vez del import del módulo. Se
  soluciona aliaseando el import (`from datetime import date as date_type`) y usándolo en la
  anotación, dejando el nombre del campo como `date` (ver `app/schemas/transactions.py`). Mismo
  cuidado con cualquier otro campo cuyo nombre coincida exactamente con su tipo.
- El saldo de una cuenta se ajusta con SQL atómico (`balance = balance + delta`,
  `services/balances.py`), nunca leyendo y reescribiendo en Python. Un gasto con tarjeta de
  crédito no toca el saldo (se ignora en `apply_transaction_balance_effect`); afecta recién al
  pagar el resumen (`services/card_statements.pay_statement`).
- Cualquier gasto con `card_id` de una tarjeta de crédito -- sea de pago único vía
  `POST /transactions` o una compra en cuotas vía `POST /installment-plans` -- necesita un
  `CardStatement` para su ciclo (`get_or_create_statement`). Nos olvidamos de esto para los
  gastos de pago único al escribir el módulo de transacciones: sin esa llamada, un gasto único a
  crédito nunca aparecía en `GET /cards/{id}/statements` ni se podía pagar. Si se agrega un nuevo
  punto de entrada que cree una `Transaction` con `card_id` de una tarjeta de crédito, hay que
  acordarse de esto.
- Conversión de moneda (`app/services/exchange_rates.py`): el dashboard convierte todo a la
  cotización más reciente disponible **a hoy**, no a la fecha del movimiento -- es una app de
  carga manual, el usuario típicamente solo carga la cotización del día, así que pedir la tasa
  "de la fecha del gasto" fallaría casi siempre para movimientos pasados. `convert()` también
  prueba la tasa inversa si no se cargó la directa (ej. se cargó ARS→USD pero se necesita
  USD→ARS). El resultado de `convert()` siempre se redondea a centavos -- multiplicar un monto
  de 2 decimales por una cotización de 6 deja un `Decimal` con hasta 8, y eso rompe la
  serialización esperada por el frontend.
- Los reportes de ingreso/gasto del dashboard (`/dashboard/summary`,
  `/dashboard/spending-by-category`) excluyen las `Transaction` que son el pago de un resumen
  (`Transaction.id` referenciado desde `CardStatement.payment_transaction_id`) -- si no se
  excluyeran, una compra en cuotas se contaría como gasto dos veces: una al comprar, otra al
  pagar el resumen.

### Frontend (React / TypeScript / Tailwind)
- Componentes funcionales + hooks. Sin clases.
- Tailwind CSS + shadcn/ui para todos los estilos y componentes base.
- Mobile-first: diseñar primero el layout mobile, expandir con `md:`/`lg:` después.
- Toda alta/edición de datos ocurre en modal o `Sheet` (shadcn), no en páginas de formulario
  completas — el objetivo es minimizar fricción de carga manual.
- Estado de servidor con **TanStack Query**; estado de UI local con **Zustand**. No mezclar
  ambos.
- Preferencia estética: interfaz limpia, minimalista, tonos oscuros/mate.
- Estructura: `lib/api/<recurso>.ts` (fetch + hooks de React Query por recurso, mirror del
  router del backend), `features/<recurso>/` (componentes), `stores/uiStore.ts` (qué modal está
  abierto y, si aplica, qué entidad se está editando).
- Formularios de alta/edición en el mismo Dialog: si el form necesita resetear su estado según
  qué se está editando, remontarlo con `key={entity?.id ?? 'new'}` e inicializar el `useState`
  directo desde la prop, en vez de un `useEffect` que sincronice manualmente (ver
  `features/accounts/AccountFormDialog.tsx`) — evita el render extra y el warning de oxlint
  `set-state-in-effect`.
- Tests de componentes: mockear `fetch` con `vi.stubGlobal` (no MSW, no hay uno instalado) y
  envolver con `renderWithProviders` (`src/test-utils.tsx`, un `QueryClient` nuevo por test).
  Los componentes que usan el `Select` de shadcn (Radix) necesitan los polyfills de
  `hasPointerCapture`/`scrollIntoView` ya cargados en `src/setupTests.ts` — si un test nuevo
  interactúa con un `Select` y jsdom tira un error de puntero, es por esto.
- Routing con `react-router-dom` (`BrowserRouter` en `main.tsx`, rutas en `App.tsx`): páginas en
  `app/pages/`, nav compartida en `app/Nav.tsx`. Un componente de página solo compone
  features + sus dialogs, no tiene lógica propia.
- Gráficos con Recharts siguiendo la skill `dataviz`: paleta categórica validada
  (`node .../dataviz/scripts/validate_palette.js`) pisada sobre los tokens `--chart-1..5` de
  shadcn en `index.css` (el `shadcn init` por defecto deja esos tokens en gris puro, chroma 0 —
  inusables). Magnitud de una sola serie (gasto por categoría, cuotas comprometidas) va con
  **un solo hue secuencial** (`--chart-1`, azul), nunca arcoíris por categoría — ver
  `references/choosing-a-form.md` de la skill. Gridlines/ejes usan `var(--border)` /
  `var(--muted-foreground)` (ya son grises neutros, no hace falta agregar tokens nuevos).
  `ResponsiveContainer` de Recharts no mide nada en jsdom (no hay layout real), así que los
  tests de estos componentes no pueden verificar las barras SVG en sí -- se testean los
  estados de carga/error/vacío y que el título/mensaje correcto se muestre.

---

## 🗺️ Roadmap de desarrollo

- [x] **Fase 0: Documentación estratégica** (arquitectura, API spec, modelo de datos, guía de
      estilo, plan de pruebas).
- [x] **Fase 1: Configuración inicial** (entornos, Docker Compose, Alembic, Git).
- [x] **Fase 2 — Módulo 1: Cuentas y Tarjetas** (CRUD + validación de ciclos de facturación).
- [x] **Fase 2 — Módulo 2: Transacciones y Cuotas** (movimientos, transferencias, cuotas).
- [x] **Fase 2 — Módulo 3: Dashboard y Reportes** (agregaciones, gráficos, flujo de caja
      proyectado).
- [ ] **Fase 2 — Módulo 4: Inversiones** (portafolio, precio promedio ponderado).

## 🔜 Pendientes / próximos pasos

Lo que falta o quedó deliberadamente afuera del alcance de los Módulos 1–3, para no
re-descubrirlo desde cero en la próxima sesión:

**Funcionalidad**
- **Módulo 4 — Inversiones**: sin empezar. No hay routers/schemas para `assets` ni
  `investment_transactions` (las tablas ya existen, ver `db/schema.sql`). El precio promedio
  ponderado y la posición deberían calcularse al vuelo a partir de los movimientos, mismo
  criterio que `CardStatement.total_amount` (ver `docs/architecture.md` § 4) — no guardarlos
  como campo que se pueda desincronizar.
- **Transferencias multi-moneda**: hoy `422` si origen y destino tienen distinta moneda
  (decisión de negocio #6). Si se pide soporte real, hay que sumar un monto en la moneda de
  destino + la cotización aplicada.
- **Reintegros/notas de crédito a tarjeta**: `card_id` en una `Transaction` solo es válido con
  `type=expense` (decisión #7). `compute_statement_totals` solo suma gastos.

**Infraestructura**
- **CI (GitHub Actions)**: planeado en Fase 0, nunca implementado — no existe
  `.github/workflows/`. Ver el plan concreto (jobs, pasos) en `docs/testing-plan.md` § CI.
  Mientras tanto la verificación es manual antes de cada commit.
- **Tema oscuro**: los tokens `.dark` de shadcn están definidos en `index.css` pero nada agrega
  esa clase al `<html>` — falta `next-themes` o un toggle manual para que la app respete la
  preferencia del sistema u ofrezca un switch. Hoy siempre renderiza en claro.
- **Bundle del frontend**: `npm run build` avisa que el chunk principal supera 500kB
  (Recharts pesa bastante). No es un problema todavía a esta escala, pero si crece más conviene
  code-splitting por ruta (`React.lazy` en `app/pages/`).

**Deuda técnica intencional (documentada, no urgente)**
- Mono-usuario sin autenticación (decisión #4) — si se agrega, todas las entidades necesitan
  `user_id` y hay que revisar cada query para que filtre por usuario.
- `python3.14-venv` no viene instalado por defecto en el sistema (`sudo apt install
  python3.14-venv`) — si `backend/venv` se recrea desde cero en una máquina nueva sin ese
  paquete, `python -m venv` falla con `ensurepip` faltante.

## 📌 Decisiones de negocio (no re-preguntar, ya confirmadas)

1. Transferencias entre cuentas propias → una única `Transaction` con `type='transfer'` y
   `destination_account_id`.
2. Compras en cuotas de crédito **no** afectan el saldo bancario al momento de la compra; afectan
   recién cuando se paga el resumen (`CardStatement`).
3. El dashboard debe mostrar una proyección de flujo de caja con los gastos comprometidos
   (cuotas pendientes) de los próximos meses.
4. MVP mono-usuario, sin autenticación. No agregar tablas `users`/JWT sin que se pida
   explícitamente.
5. Soporte multi-moneda desde el día uno (`currency` por cuenta/activo + tabla
   `exchange_rates` cargada manualmente).
6. Simplificación deliberada (Módulo 2): una transferencia solo puede ser entre cuentas de la
   misma moneda (422 si no coinciden) -- no hay conversión de moneda en la transferencia misma.
   Para "comprar dólares" el usuario registra dos movimientos separados (gasto en la cuenta ARS
   + ingreso en la cuenta USD). Si se pide soporte real de transferencias multi-moneda, hay que
   sumar un campo de monto en la moneda de destino y una tasa de cambio aplicada.
7. Simplificación deliberada (Módulo 2): `card_id` en una `Transaction` solo es válido con
   `type=expense` -- no se modela un reintegro/nota de crédito a la tarjeta. Si se necesita, hay
   que revisar `services/card_statements.compute_statement_totals` (hoy solo suma gastos).
