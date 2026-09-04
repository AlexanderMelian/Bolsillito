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

### CI (GitHub Actions)
`.github/workflows/ci.yml`, jobs `backend`/`frontend` en paralelo por push/PR contra `master` y
`develop` — detalle de cada paso en `docs/testing-plan.md` § CI. El job de backend usa un
servicio `postgres:16` con `POSTGRES_DB=bolsillito_test` directo (una sola base, sin Alembic:
`conftest.py` crea las tablas desde `Base.metadata`), así que simula el entorno de test más
fácil que replicar el setup completo de dev con dos bases.

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
- **Multi-usuario: todo endpoint nuevo (salvo `/auth/*` y `/exchange-rates`) necesita
  `current_user: User = Depends(get_current_user)`** (`app/services/auth.py`). Cualquier query
  de listado filtra por `Model.user_id == current_user.id`; cualquier `_get_*_or_404` filtra
  igual (nunca solo por `id`); cualquier FK que venga en el payload de un create/update se valida
  por ownership (existe **y** pertenece al usuario), no solo por existencia -- si no, es un IDOR.
  Un recurso que existe pero es de otro usuario devuelve **404, no 403** (no revelar que existe).
  Ver `app/routers/accounts.py` o `app/routers/transactions.py` (`_validate_and_resolve`) como
  referencia. `exchange_rates` es la única tabla sin `user_id` (cotización de mercado, dato
  compartido) pero sus endpoints igual requieren `get_current_user` -- ver decisión #4.
- **Bug real encontrado al migrar a multi-usuario**: `services/card_statements.pay_statement`
  creaba la `Transaction` de pago de un resumen sin `user_id` -- no lo agarró ningún test viejo
  porque ninguno pagaba un resumen y después intentaba leerlo filtrado por usuario. Al volverse
  `NOT NULL` la columna, esto habría roto todo pago de resumen en producción. Moraleja: cuando se
  agrega una columna `NOT NULL` nueva, no alcanza con revisar los `routers/` -- hay que revisar
  también todo `services/` que construya un modelo directamente (`Model(...)`), porque ahí no hay
  `current_user` a mano y es fácil que quede afuera del `grep` mental de "dónde se crea esto".
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
- **FK cruda sin `relationship()` → ordenar los `DELETE` a mano.** `Transaction.
  investment_transaction_id` no tiene un `relationship()` ORM que lo acompañe (ver
  `docs/architecture.md` § 4). Sin eso, el unit-of-work de SQLAlchemy no sabe que hay que borrar
  la `Transaction` vinculada antes que la `InvestmentTransaction` que referencia, y a veces
  flushea en el orden contrario → `ForeignKeyViolationError`. Solución: borrar el lado que
  referencia con un `DELETE` inmediato (`await session.execute(delete(Transaction).where(...))`,
  no `session.delete(obj)`) antes de borrar el lado referenciado -- mismo patrón que ya se usaba
  en `DELETE /installment-plans/{id}`, pero ahí no hacía falta explicarlo porque nunca se probó
  el caso sin `relationship()`. Si se agrega otra FK cruda entre dos entidades con borrado
  encadenado, aplicar el mismo patrón y agregar el test que lo prueba (no alcanza con "no tira
  error al crear", hay que probar el `DELETE`).

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
- **Tema claro/oscuro**: `stores/themeStore.ts` (Zustand + `persist` en `localStorage`, clave
  `bolsillito-theme`) agrega/saca la clase `.dark` de `<html>` -- el CSS de shadcn ya tenía los
  tokens `.dark` definidos desde Fase 1, solo faltaba esto. `light`/`dark`/`system` se cicla con
  `app/ThemeToggle.tsx` (ícono en el header). `index.html` tiene un script inline que aplica el
  tema ANTES de que React monte (misma clave de storage) para no parpadear en claro un instante.
  Si se cambia la clave de `persist`, hay que actualizar los dos lugares.
- **Dos trampas de jsdom que aparecieron con el tema, ya resueltas en `setupTests.ts`:**
  (1) `window.matchMedia` no existe en jsdom -- `themeStore.ts` lo llama en el nivel de módulo
  (para escuchar cambios de preferencia del SO), así que sin el polyfill *cualquier* test que
  importe `App` o `ThemeToggle` rompía al cargar el módulo, no al ejercitar el tema. (2) Node
  22+ trae su propio `localStorage` global activo sin el flag `--localstorage-file`, con
  `setItem`/`clear` rotos, y pisa el de jsdom -- se reemplaza por un mock en memoria. Un test que
  dispara alguno de estos dos errores casi seguro está tocando el tema indirectamente (a través
  de `App.test.tsx` u otro componente que renderice el header).

---

## 🗺️ Roadmap de desarrollo

- [x] **Fase 0: Documentación estratégica** (arquitectura, API spec, modelo de datos, guía de
      estilo, plan de pruebas).
- [x] **Fase 1: Configuración inicial** (entornos, Docker Compose, Alembic, Git).
- [x] **Fase 2 — Módulo 1: Cuentas y Tarjetas** (CRUD + validación de ciclos de facturación).
- [x] **Fase 2 — Módulo 2: Transacciones y Cuotas** (movimientos, transferencias, cuotas).
- [x] **Fase 2 — Módulo 3: Dashboard y Reportes** (agregaciones, gráficos, flujo de caja
      proyectado).
- [x] **Fase 2 — Módulo 4: Inversiones** (portafolio, precio promedio ponderado).
- [x] **Fase 2 — Módulo 5: Multi-usuario** (registro/login usuario+contraseña, JWT, aislamiento
      de datos por `user_id`).

## 🔜 Pendientes / próximos pasos

Lo que falta o quedó deliberadamente afuera del alcance de los Módulos 1–3, para no
re-descubrirlo desde cero en la próxima sesión:

**Funcionalidad**
- **Cotización de mercado / ganancia no realizada**: el portafolio (`/portfolio`) solo muestra
  costo de la posición y ganancia **realizada** (de ventas concretadas) — no hay ninguna
  integración con una cotización de mercado (a propósito: "sin Open Banking ni APIs externas").
  Si se quiere mostrar valor actual / ganancia en papel, la opción más consistente con el resto
  de la app es un campo de precio cargado a mano por activo (mismo patrón que
  `exchange_rates`), no una API externa.
- **Transferencias multi-moneda**: hoy `422` si origen y destino tienen distinta moneda
  (decisión de negocio #6). Si se pide soporte real, hay que sumar un monto en la moneda de
  destino + la cotización aplicada.
- **Reintegros/notas de crédito a tarjeta**: `card_id` en una `Transaction` solo es válido con
  `type=expense` (decisión #7). `compute_statement_totals` solo suma gastos.

**Infraestructura**
- **Bundle del frontend**: `npm run build` avisa que el chunk principal supera 500kB
  (Recharts pesa bastante). No es un problema todavía a esta escala, pero si crece más conviene
  code-splitting por ruta (`React.lazy` en `app/pages/`).

**Deuda técnica intencional (documentada, no urgente)**
- Auth "algo sencillo" (decisión #4): sin refresh tokens, sin reseteo de contraseña, sin
  verificación de email, sin rate-limiting de login. El JWT dura 7 días (`access_token_expire_
  minutes` en `config.py`) y no hay forma de invalidarlo antes de que expire salvo cambiar
  `secret_key`. Si esto se vuelve una app real con más de un usuario de confianza, hay que
  sumar esas piezas.
- `SECRET_KEY` de desarrollo (`dev-only-insecure-secret-key-change-me` en `config.py`) tiene que
  reemplazarse por un valor real vía variable de entorno antes de cualquier despliegue.
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
4. ~~MVP mono-usuario, sin autenticación~~ — **superada**: la app es multi-usuario desde el
   Módulo 5. Registro/login con usuario+contraseña (sin email), JWT bearer (`PyJWT`, HS256,
   7 días, sin refresh token), contraseñas con `bcrypt`. Casi todas las tablas tienen `user_id`
   y cada endpoint filtra/valida ownership por el usuario autenticado (`get_current_user`);
   un recurso de otro usuario da 404, no 403, para no revelar que existe. Única excepción:
   `exchange_rates` sigue sin `user_id` (es cotización de mercado compartida, no dato personal),
   aunque sus endpoints ahora requieren estar autenticado igual que el resto.
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
8. Convención deliberada (Módulo 4): `InvestmentTransaction` no tiene un campo "monto total"
   separado para dividendos -- se carga como `quantity=1`, `price=<monto total percibido>`. El
   costo promedio ponderado en una venta **no cambia** (solo se registra la ganancia/pérdida
   realizada de esa venta puntual); vender más de la posición actual da `422` (se valida sobre
   el total compras-ventas, no cronológicamente por lote/FIFO).
9. Una transacción de inversión con `account_id` genera una `Transaction` vinculada (débito en
   compra, crédito en venta/dividendo) igual que una compra en cuotas genera su transacción de
   registro -- ver `agents.md` (FK cruda) y `docs/api-spec.md` § Transacciones de inversión.
   Sin `account_id`, la transacción de inversión no toca ningún saldo (uso: activos en un broker
   que no se modela como cuenta).
