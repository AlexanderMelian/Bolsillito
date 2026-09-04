# Arquitectura Técnica — Bolsillito

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
                                                        billing_cycle, cash-flow projection,
                                                        weighted average cost)
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

## 4. Entornos

- `dev`: Docker Compose levanta `db` (postgres:16), `pgadmin`, `backend` (uvicorn --reload) y
  `frontend` (vite dev server), todos con hot-reload vía bind mounts.
- `prod`: `docker-compose.prod.yml` construye imágenes optimizadas (multi-stage build del
  frontend servido como estáticos, backend con Gunicorn+Uvicorn workers), sin bind mounts.
- Variables de entorno (`.env`, no versionado): `DATABASE_URL`, `VITE_API_URL`,
  `DEFAULT_CURRENCY` (moneda de referencia para consolidar patrimonio, ver `exchange_rates`).
