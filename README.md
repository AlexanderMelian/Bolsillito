# 💰 Bolsillito

[![CI](https://github.com/AlexanderMelian/Bolsillito/actions/workflows/ci.yml/badge.svg)](https://github.com/AlexanderMelian/Bolsillito/actions/workflows/ci.yml)

App de finanzas personales con carga **100% manual** — cuentas, tarjetas, cuotas de crédito,
movimientos e inversiones, sin ninguna integración bancaria ni de brokers (sin Open Banking, sin
APIs externas). Pensada como dashboard financiero mobile-first, no como una planilla de cálculo.

## ✨ Funcionalidades

- **Cuentas y tarjetas** — bancarias, efectivo, billeteras virtuales; tarjetas de débito y
  crédito con día de cierre/pago.
- **Movimientos** — ingresos, gastos, transferencias entre cuentas propias.
- **Cuotas de crédito** — comprar en N cuotas reparte el monto en los ciclos de facturación que
  corresponden y genera los resúmenes automáticamente; el saldo bancario se descuenta recién al
  pagar el resumen, no al momento de la compra.
- **Dashboard** — patrimonio consolidado (multi-moneda, con cotización manual), gasto por
  categoría, proyección de flujo de caja de los próximos meses.
- **Inversiones** — portafolio con costo promedio ponderado y ganancia realizada (sin cotización
  de mercado en tiempo real: es tracking manual, no un feed de precios).
- **Tema claro/oscuro**, con detección de la preferencia del sistema.

Los 4 módulos del MVP están implementados y testeados — ver el estado detallado y lo que queda
pendiente en [`agents.md`](./agents.md#-pendientes--próximos-pasos).

## 🏗️ Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.14 · FastAPI (async) · SQLAlchemy 2.0 · Alembic · PostgreSQL |
| Frontend | React (Vite) · TypeScript · Tailwind CSS v4 · shadcn/ui · Recharts · TanStack Query · Zustand |
| Infra | Docker Compose (dev/prod) · GitHub Actions |

## 🚀 Empezar

Requiere Docker.

```bash
docker compose up
```

- Frontend: http://localhost:5173
- Backend (Swagger UI): http://localhost:8000/docs
- pgAdmin: http://localhost:5050

La primera vez hay que aplicar las migraciones (con el backend levantado):

```bash
cd backend && python -m venv venv && venv/bin/pip install -r requirements.txt
venv/bin/alembic upgrade head
```

### Sin Docker

```bash
make install   # entorno virtual del backend + npm install del frontend
make migrate   # aplica las migraciones de Alembic
make dev       # equivalente a `docker compose up`
make test      # pytest + vitest
```

Comandos más al detalle (entorno virtual, variables de entorno, etc.) en
[`agents.md`](./agents.md) § Comandos del proyecto.

## ✅ Tests

161 tests de backend (100% de cobertura de línea, gate en 95%) + 63 de frontend (gate 80%
líneas/statements/funcs, 70% branches). Corren automáticamente en cada push/PR vía
[GitHub Actions](./.github/workflows/ci.yml).

```bash
cd backend && pytest              # requiere Postgres -- ver docs/testing-plan.md
cd frontend && npm run test
```

## 📚 Documentación

| Documento | Contenido |
|---|---|
| [`agents.md`](./agents.md) | Comandos, convenciones de estilo, decisiones de negocio, pendientes -- el documento vivo del proyecto. |
| [`docs/architecture.md`](./docs/architecture.md) | Arquitectura técnica, estructura de backend y frontend, justificación de decisiones. |
| [`docs/api-spec.md`](./docs/api-spec.md) | Especificación de la API: recursos, validaciones, ejemplos. |
| [`docs/testing-plan.md`](./docs/testing-plan.md) | Estrategia y organización de la suite de tests. |
| [`db/schema.sql`](./db/schema.sql) | DDL de referencia del esquema (la fuente de verdad real son las migraciones de Alembic). |

## 📂 Estructura

```
backend/
  app/
    models.py     # SQLAlchemy 2.0 -- única fuente de verdad del esquema
    schemas/       # DTOs Pydantic v2, uno por recurso
    routers/       # endpoints FastAPI
    services/      # lógica de negocio (ciclos de facturación, saldos, cotizaciones, ...)
  migrations/      # Alembic
  tests/
frontend/
  src/
    app/           # shell, rutas, nav, tema
    features/      # componentes de UI por recurso
    lib/api/       # cliente HTTP + hooks de TanStack Query
    stores/        # estado de UI (Zustand)
```

## 🔒 Decisiones clave

- **Sin campos desnormalizados que se puedan desincronizar**: el saldo de una cuenta, el total
  de un resumen de tarjeta y el costo/ganancia de una inversión se recalculan a partir del
  historial de movimientos, nunca se guardan como valor fijo.
- **Mono-usuario, sin autenticación** — es una app de uso personal.
- Detalle completo de estas y otras decisiones en
  [`agents.md`](./agents.md#-decisiones-de-negocio-no-re-preguntar-ya-confirmadas).
