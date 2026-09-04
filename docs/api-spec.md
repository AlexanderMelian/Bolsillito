# Especificación de API — Bolsillito

La fuente de verdad es el OpenAPI que expone FastAPI automáticamente en `/docs` (Swagger UI) y
`/redoc` una vez levantado el backend (Fase 1). Este documento resume los recursos, DTOs y
convenciones que ese OpenAPI va a reflejar, para poder diseñar el frontend en paralelo antes de
tener el backend corriendo.

## Convenciones generales

- Prefijo `/api/v1`.
- Todos los DTOs de entrada son `*Create` / `*Update` (Pydantic v2, `model_config = {"extra":
  "forbid"}` para detectar typos de campos en el body); los de salida son `*Read`.
- Montos: `string` decimal en JSON (no `float`), ej. `"1234.56"` — Pydantic v2 serializa
  `Decimal` como string por defecto, evitando errores de precisión de punto flotante en el
  cliente.
- Fechas: `YYYY-MM-DD` (ISO 8601, sin hora) para todo lo que sea "fecha de negocio" (compra,
  cierre, vencimiento); `datetime` con timezone solo en `created_at`.
- Errores: `422` con el detalle estándar de Pydantic para validación; `404` con
  `{"detail": "..."}` para recursos inexistentes; `409` para violaciones de reglas de negocio
  (ej. transferencia a la misma cuenta).

## Recursos (CRUD estándar salvo excepciones anotadas)

| Recurso | Endpoints | Notas |
|---|---|---|
| `/accounts` | GET, POST, GET/{id}, PATCH/{id}, DELETE/{id} | `DELETE` es soft-delete (`is_archived=true`) si tiene movimientos asociados. |
| `/cards` | GET, POST, GET/{id}, PATCH/{id}, DELETE/{id} | `POST`/`PATCH` validan `closing_day`/`payment_day` obligatorios si `type=credit`. |
| `/cards/{id}/statements` | GET | Lista los `CardStatement` de la tarjeta (histórico + ciclo abierto actual). |
| `/cards/{id}/statements/{statement_id}/pay` | POST | Registra el pago: crea la `Transaction` de pago y pasa el `status` a `paid`. |
| `/categories` | GET, POST, PATCH/{id}, DELETE/{id} | Catálogo simple. |
| `/transactions` | GET (con filtros `account_id`, `category_id`, `date_from`, `date_to`, `type`), POST, GET/{id}, PATCH/{id}, DELETE/{id} | `POST` con `type=transfer` requiere `destination_account_id`. |
| `/installment-plans` | POST, GET/{id}, DELETE/{id} | `POST` dispara `services/billing_cycle.py` para generar los `InstallmentItem` y asociarlos/crear los `CardStatement` correspondientes. |
| `/assets` | GET, POST, GET/{id} | Catálogo de activos (ticker, tipo, moneda). |
| `/investment-transactions` | GET (filtro `asset_id`), POST, DELETE/{id} | El precio promedio y la posición se calculan al vuelo, no se guardan. |
| `/dashboard/summary` | GET (query `month`) | Saldo total, patrimonio neto, ingresos/gastos del mes, consolidado en la moneda de referencia vía `exchange_rates`. |
| `/dashboard/cash-flow-projection` | GET (query `months=6`) | Próximos N meses: total comprometido por cuotas pendientes + gastos recurrentes conocidos. |
| `/exchange-rates` | GET, POST | Carga manual de cotizaciones usadas para consolidar patrimonio multi-moneda. |

## Ejemplo — crear una compra en cuotas

**Request** `POST /api/v1/installment-plans`
```json
{
  "card_id": 3,
  "category_id": 7,
  "description": "Notebook",
  "purchase_date": "2026-03-14",
  "total_amount": "300000.00",
  "total_installments": 3
}
```

**Response** `201 Created`
```json
{
  "id": 42,
  "card_id": 3,
  "category_id": 7,
  "description": "Notebook",
  "purchase_date": "2026-03-14",
  "total_amount": "300000.00",
  "total_installments": 3,
  "items": [
    {"number": 1, "amount": "100000.00", "statement_closing_date": "2026-03-15"},
    {"number": 2, "amount": "100000.00", "statement_closing_date": "2026-04-15"},
    {"number": 3, "amount": "100000.00", "statement_closing_date": "2026-05-15"}
  ]
}
```
(La tarjeta 3 tiene `closing_day=15`; la compra del 14/03 cae en el ciclo que cierra el 15/03,
como se explica en `docs/architecture.md`.)

## Ejemplo — proyección de flujo de caja

**Request** `GET /api/v1/dashboard/cash-flow-projection?months=3`

**Response** `200 OK`
```json
{
  "reference_currency": "ARS",
  "projection": [
    {"month": "2026-03", "committed_amount": "145000.00"},
    {"month": "2026-04", "committed_amount": "130000.00"},
    {"month": "2026-05", "committed_amount": "100000.00"}
  ]
}
```
