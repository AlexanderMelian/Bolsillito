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
- **Ejecutar tests:** `pytest` (desde `backend/`, usa `pytest.ini` -> `testpaths = tests`;
  `scripts/` queda afuera a propósito porque `smoke_test.py` no es un test automatizado)

### Frontend (React + Vite)
- **Instalar dependencias:** `npm install` (desde `frontend/`)
- **Ejecutar servidor de desarrollo:** `npm run dev` (desde `frontend/`)
- **Compilar para producción:** `npm run build`
- **Ejecutar tests:** `npm run test`

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
- Estructura modular: separar `models/` (SQLAlchemy), `schemas/` (Pydantic), `routers/`
  (endpoints), `services/` (lógica de negocio, ej. cálculo de ciclos de facturación).
- La lógica de ciclos de facturación y cuotas vive en `services/billing_cycle.py` — no debe
  duplicarse en routers.

### Frontend (React / TypeScript / Tailwind)
- Componentes funcionales + hooks. Sin clases.
- Tailwind CSS + shadcn/ui para todos los estilos y componentes base.
- Mobile-first: diseñar primero el layout mobile, expandir con `md:`/`lg:` después.
- Toda alta/edición de datos ocurre en modal o `Sheet` (shadcn), no en páginas de formulario
  completas — el objetivo es minimizar fricción de carga manual.
- Estado de servidor con **TanStack Query**; estado de UI local con **Zustand**. No mezclar
  ambos.
- Preferencia estética: interfaz limpia, minimalista, tonos oscuros/mate.

---

## 🗺️ Roadmap de desarrollo

- [x] **Fase 0: Documentación estratégica** (arquitectura, API spec, modelo de datos, guía de
      estilo, plan de pruebas).
- [x] **Fase 1: Configuración inicial** (entornos, Docker Compose, Alembic, Git).
- [ ] **Fase 2 — Módulo 1: Cuentas y Tarjetas** (CRUD + validación de ciclos de facturación).
- [ ] **Fase 2 — Módulo 2: Transacciones y Cuotas** (movimientos, transferencias, cuotas).
- [ ] **Fase 2 — Módulo 3: Dashboard y Reportes** (agregaciones, gráficos, flujo de caja
      proyectado).
- [ ] **Fase 2 — Módulo 4: Inversiones** (portafolio, precio promedio ponderado).

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
