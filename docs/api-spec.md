# Especificación de API — Bolsillito

> **Estado:** implementado y testeado — los 4 módulos del MVP (Cuentas/Tarjetas,
> Transacciones/Cuotas, Dashboard/Reportes, Inversiones) más el Módulo 5 (multi-usuario). Ver
> `agents.md` § Pendientes para lo que queda afuera del alcance actual.

La fuente de verdad interactiva es el OpenAPI que expone FastAPI en `/docs` (Swagger UI) y
`/redoc` con el backend corriendo. Este documento es la referencia legible sin levantar nada,
y documenta también las reglas de negocio que el OpenAPI no expresa (qué combina con qué, qué
tira 409 vs 422).

## Convenciones generales

- Prefijo `/api/v1` en todos los endpoints.
- DTOs de entrada `*Create` / `*Update`, de salida `*Read` (Pydantic v2,
  `model_config = ConfigDict(extra="forbid")` en los de entrada — un campo desconocido en el
  body es 422, no se ignora silenciosamente).
- Montos: `string` decimal en JSON (ej. `"1234.56"`), nunca `float` — evita errores de
  precisión en el cliente. Los campos de moneda (`currency`, `from_currency`, `to_currency`) son
  strings ISO 4217 de 3 letras (`"ARS"`, `"USD"`).
- Fechas: `"YYYY-MM-DD"` para toda fecha de negocio (compra, cierre, vencimiento, movimiento).
- Errores:
  - `422` — validación de forma/reglas de negocio verificables sin tocar la DB (Pydantic
    `model_validator`/`field_validator`), ej. transferencia sin `destination_account_id`,
    tarjeta de crédito sin `closing_day`.
  - `404` — recurso inexistente, `{"detail": "..."}`.
  - `409` — violación de una constraint de integridad de la base (`IntegrityError` capturado
    por un handler global en `app/main.py`) — FK, `UNIQUE`, `CHECK`. Mensaje genérico
    (`"La operación viola una regla de integridad de datos."`); si hace falta un mensaje más
    específico para un caso puntual, se valida antes en Pydantic o a mano en el router (ver
    ejemplos de 409 explícitos más abajo).

## Autenticación

Todos los endpoints, salvo `POST /auth/register` y `POST /auth/login`, requieren
`Authorization: Bearer <token>`. Sin ese header (o con un token inválido/vencido): `401` con
`{"detail": "No autenticado"}` y header `WWW-Authenticate: Bearer`.

Casi todas las tablas tienen `user_id` y cada endpoint filtra/valida por el usuario autenticado.
**Un recurso que existe pero pertenece a otro usuario devuelve `404`, igual que uno inexistente**
— nunca `403` — para no revelar su existencia. Esto aplica también a las FKs que se mandan en el
body de un create/update (ej. `account_id` en `POST /transactions`): si esa cuenta es de otro
usuario, es `404`, no `422`. Única excepción: `/exchange-rates` no filtra por usuario (ver esa
sección) aunque sigue requiriendo estar autenticado.

### `/auth`

| Método | Path | Notas |
|---|---|---|
| POST | `/auth/register` | `201`. Crea el usuario y devuelve un `Token` ya logueado. `409` si el username ya existe. |
| POST | `/auth/login` | `200`. Devuelve un `Token`. `401` si el usuario no existe o la contraseña no matchea. |
| GET | `/auth/me` | `200`. Requiere token. Devuelve el `UserRead` del usuario autenticado. |

**`UserCreate`** (body de `/register`): `username: str` (≥ 3 caracteres, `422` si no),
`password: str` (≥ 8 caracteres, `422` si no).
**`LoginRequest`** (body de `/login`): `username: str`, `password: str`.
**`UserRead`**: `id: int`, `username: str`.
**`Token`**: `access_token: str`, `token_type: "bearer"`, `user: UserRead`.

El token es un JWT (`PyJWT`, HS256) con `sub = str(user_id)`, sin refresh token y sin forma de
invalidarlo antes de que expire (dura 7 días, `access_token_expire_minutes` en `config.py`) — ver
"algo sencillo" en `agents.md` § Decisiones de negocio #4.

---

## Cuentas — `/accounts`

| Método | Path | Query | Notas |
|---|---|---|---|
| GET | `/accounts` | `include_archived: bool = false` | Por defecto no lista cuentas archivadas. |
| POST | `/accounts` | — | `201`. |
| GET | `/accounts/{id}` | — | `404` si no existe. |
| PATCH | `/accounts/{id}` | — | Parcial (`exclude_unset`). |
| DELETE | `/accounts/{id}` | — | Ver regla de soft-delete abajo. `200` con el recurso (soft o hard). |

**`AccountCreate`**: `name: str`, `type: "bank"|"cash"|"wallet"|"investment"`,
`currency: str = "ARS"`, `balance: Decimal = "0.00"`.
**`AccountUpdate`**: los mismos campos, todos opcionales.
**`AccountRead`**: agrega `id: int`, `is_archived: bool`.

**Regla de `DELETE`**: si la cuenta tiene tarjetas o transacciones asociadas (como origen o
destino), no se borra — se archiva (`is_archived = true`) para no perder el historial. Si no
tiene nada asociado, se borra físicamente. En ambos casos responde `200` con el estado final del
recurso (no `204`), justamente para que el cliente sepa cuál de los dos pasó.

---

## Tarjetas — `/cards`

| Método | Path | Query | Notas |
|---|---|---|---|
| GET | `/cards` | `account_id: int?` | Filtra por cuenta si se pasa. |
| POST | `/cards` | — | `201`. `422` si `type=credit` sin `closing_day`/`payment_day`. |
| GET | `/cards/{id}` | — | `404`. |
| PATCH | `/cards/{id}` | — | Revalida la regla de ciclo sobre el estado combinado resultante. |
| DELETE | `/cards/{id}` | — | `204`. `409` si tiene transacciones o planes de cuotas (FK sin `ON DELETE CASCADE`, a propósito). |

**`CardCreate`**: `account_id: int`, `payment_account_id: int? = null`, `name: str`,
`type: "debit"|"credit"`, `credit_limit: Decimal? = null`, `closing_day: int? = null` (1–31),
`payment_day: int? = null` (1–31). `payment_account_id` es la cuenta desde la que se paga el
resumen si es distinta de `account_id` (si es `null`, se paga desde `account_id`).
**`CardRead`**: agrega `id: int`.

### Resúmenes de una tarjeta — `/cards/{id}/statements`

| Método | Path | Notas |
|---|---|---|
| GET | `/cards/{id}/statements` | Lista `CardStatement`, ordenados por `closing_date`. |
| POST | `/cards/{id}/statements/{statement_id}/pay` | Registra el pago. |

**`CardStatementRead`**: `id`, `card_id`, `closing_date`, `payment_due_date`,
`status: "open"|"closed"|"paid"`, `total_amount: Decimal`, `payment_transaction_id: int?`.

`total_amount` y `status` **se calculan en el momento de la consulta** (nunca se leen tal cual
de la columna, salvo que ya esté `paid`): suman las `InstallmentItem` del resumen más los gastos
de pago único (`Transaction.card_id` sin `installment_plan_id`) fechados dentro del período. Un
gasto con tarjeta de crédito —sea de pago único o una cuota— siempre tiene un `CardStatement`
asociado a su ciclo, se haya cargado por `/transactions` o por `/installment-plans`.

`status`: `paid` si tiene `payment_transaction_id`; si no, `closed` si `hoy >= closing_date`,
si no `open`.

**Pagar un resumen** — `POST /cards/{id}/statements/{statement_id}/pay`
Body: `{"payment_date": "2026-03-25"}`.
Crea una `Transaction` tipo `expense` contra la cuenta de pago de la tarjeta por el
`total_amount` del resumen (recién ahí se descuenta el saldo bancario — ver decisión de negocio
#2 en `agents.md`), marca el resumen `paid` y lo enlaza vía `payment_transaction_id`.
`409` si el resumen ya está pagado o si no tiene saldo pendiente (`total_amount <= 0`).

---

## Categorías — `/categories`

CRUD estándar (`GET`, `POST`→`201`, `GET/{id}`, `PATCH/{id}`, `DELETE/{id}`→`204`).
**`CategoryCreate`**: `name: str` (único **por usuario** — dos usuarios pueden tener cada uno una
categoría "Comida"), `kind: "income"|"expense"|"transfer"`, `icon: str? = null` (un emoji, texto
libre). `DELETE` da `409` si la categoría está referenciada por alguna transacción o plan de
cuotas.

---

## Movimientos — `/transactions`

| Método | Path | Query | Notas |
|---|---|---|---|
| GET | `/transactions` | `account_id`, `category_id`, `type`, `date_from`, `date_to` (todos opcionales) | `account_id` matchea como origen **o** destino. |
| POST | `/transactions` | — | `201`. Ver validaciones abajo. |
| GET | `/transactions/{id}` | — | `404`. |
| PATCH | `/transactions/{id}` | — | Solo metadata (ver abajo). |
| DELETE | `/transactions/{id}` | — | `204`. Revierte el efecto sobre el saldo. `409` si es el registro de una compra en cuotas. |

**`TransactionCreate`**: `type: "income"|"expense"|"transfer"`, `account_id: int`,
`destination_account_id: int?`, `card_id: int?`, `category_id: int?`, `amount: Decimal` (> 0),
`currency: str?` (si se omite, toma la de `account_id`), `date: str`, `description: str?`.

Validado en el schema (422, sin tocar la DB):
- `type=transfer` ⇒ `card_id` debe ser `null`, `destination_account_id` obligatorio y distinto
  de `account_id`.
- `type` != `transfer` ⇒ `destination_account_id` debe ser `null`; `card_id` solo se permite si
  `type=expense`.

Validado en el router (necesita la DB):
- La cuenta (y, si aplica, la cuenta de destino) tiene que existir (`404`).
- Si hay `card_id`, la tarjeta tiene que existir y pertenecer a `account_id` (`422` si no).
- Transferencia entre cuentas de distinta moneda ⇒ `422` (ver decisión de negocio #6).
- Si hay `category_id`, la categoría tiene que existir y su `kind` tiene que coincidir con
  `type` (`422` si no).
- Si se manda `currency` explícito, tiene que coincidir con la moneda de `account_id` (`422`).

**Efecto sobre el saldo** (`services/balances.py`, `apply_transaction_balance_effect`):
- `income`/`expense` sin tarjeta, o con tarjeta de **débito**: ajusta `account_id` de inmediato.
- `expense` con tarjeta de **crédito**: no toca el saldo (impacta al pagar el resumen).
- `transfer`: descuenta `account_id`, acredita `destination_account_id`, atómico.

**`TransactionUpdate`**: solo `category_id`, `date`, `description` — **no** se puede editar
`amount`/`account_id`/`type`/`card_id` una vez creado (para eso: `DELETE` + `POST`, así el
efecto sobre el saldo no queda desincronizado). Si se manda `category_id`, se revalida que
exista y que su `kind` matchee `type` de la transacción existente.

**`DELETE`**: revierte el efecto sobre el saldo (lo inverso de `apply_transaction_balance_effect`)
antes de borrar. Si la transacción es el registro de una compra en cuotas
(`installment_plan_id` no nulo), devuelve `409` — hay que borrar el plan de cuotas, que se
encarga de todo (ver abajo).

---

## Compras en cuotas — `/installment-plans`

| Método | Path | Notas |
|---|---|---|
| POST | `/installment-plans` | `201`. Genera las cuotas y crea/reutiliza los resúmenes. |
| GET | `/installment-plans/{id}` | `404`. |
| DELETE | `/installment-plans/{id}` | `204`. Borra cuotas y transacción de registro. |

**`InstallmentPlanCreate`**: `card_id: int`, `category_id: int?`, `description: str`,
`purchase_date: str`, `total_amount: Decimal` (> 0), `total_installments: int` (≥ 1).

Validaciones: la tarjeta tiene que existir y ser `type=credit` (`422` si es débito — las cuotas
solo existen en tarjetas de crédito); si hay `category_id`, tiene que existir y ser
`kind=expense` (`422`).

Al crear: usa `services/billing_cycle.py` (`build_installment_amounts` +
`build_installment_closing_dates`, ver el detalle algorítmico en `docs/architecture.md`) para
repartir `total_amount` en `total_installments` cuotas y asignar cada una al ciclo que le
corresponde, creando el `CardStatement` de cada ciclo si todavía no existe. Además crea una
`Transaction` tipo `expense` con `installment_plan_id` seteado, para que la compra aparezca en
el historial — **no** afecta el saldo (es una tarjeta de crédito).

**`DELETE`**: borra la `Transaction` de registro (su FK a `installment_plans` no tiene
`ON DELETE CASCADE` a propósito, así que hay que borrarla antes) y después el plan, cuyas
`InstallmentItem` se van en cascada. Los `CardStatement` no se tocan — si quedan vacíos, su
`total_amount` calculado da `0.00` en el siguiente `GET`.

**Ejemplo** — `POST /api/v1/installment-plans`
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
Respuesta `201` (tarjeta con `closing_day=15`: la compra del 14/03 cae en el ciclo que cierra el
15/03):
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
    {"number": 1, "amount": "100000.00", "statement_id": 101},
    {"number": 2, "amount": "100000.00", "statement_id": 102},
    {"number": 3, "amount": "100000.00", "statement_id": 103}
  ]
}
```

---

## Cotizaciones — `/exchange-rates`

**Sin `user_id`** — a diferencia de todo lo demás en esta API, una cotización de mercado
(ARS→USD del 2026-03-14, por ejemplo) no es un dato personal, es un hecho del mundo que todos los
usuarios comparten; si el usuario A carga la cotización del día, el usuario B la ve también. Los
endpoints igual requieren `Authorization: Bearer <token>` (cualquier usuario autenticado sirve).

| Método | Path | Notas |
|---|---|---|
| GET | `/exchange-rates` | Ordenadas por `date` descendente. |
| POST | `/exchange-rates` | **Upsert**: `201` si crea, `200` si actualiza una ya cargada para el mismo par+fecha. |

**`ExchangeRateCreate`**: `from_currency: str`, `to_currency: str`, `rate: Decimal` (hasta 6
decimales), `date: str`. Si ya existe una cotización para `(from_currency, to_currency, date)`,
el `POST` actualiza el `rate` en vez de fallar `409` — pensado para poder corregir la cotización
del día sin borrar primero.

---

## Dashboard — `/dashboard`

Todos los montos se devuelven consolidados en `reference_currency` (= `DEFAULT_CURRENCY` de
`backend/.env`, por defecto `ARS`), usando `services/exchange_rates.py`: la cotización manual
más reciente **a hoy** (no a la fecha del movimiento — ver `agents.md`), con fallback a la tasa
inversa si no se cargó la directa. Un monto en una moneda sin cotización cargada no rompe la
respuesta: se excluye del total y queda listado aparte (`unconverted_balances` en `/summary`) o
simplemente no suma (en los otros dos endpoints).

### `GET /dashboard/summary`

Query: `month: "YYYY-MM"?` (default: mes actual). `422` si el formato no es válido.

```json
{
  "reference_currency": "ARS",
  "month": "2026-09",
  "total_balance": "1234567.89",
  "month_income": "500000.00",
  "month_expenses": "320000.00",
  "unconverted_balances": [{"currency": "USD", "amount": "10.00"}]
}
```
`total_balance`: suma de todas las cuentas no archivadas, convertidas. `month_income` /
`month_expenses`: suma de `Transaction` tipo `income`/`expense` con fecha dentro del mes —
**excluye** las transacciones que son el pago de un resumen (`CardStatement.
payment_transaction_id`), para no contar una compra en cuotas como gasto dos veces (una al
comprar, otra al pagar el resumen).

### `GET /dashboard/spending-by-category`

Query: `month: "YYYY-MM"?`. Gastos del mes agrupados por categoría, orden descendente por total;
`category_id: null` agrupa los gastos sin categoría (`category_name: "Sin categoría"`). Mismo
criterio de exclusión de pagos de resumen que `/summary`.
```json
[
  {"category_id": 3, "category_name": "Comida", "icon": "🍔", "total": "45000.00"},
  {"category_id": null, "category_name": "Sin categoría", "icon": null, "total": "8000.00"}
]
```

### `GET /dashboard/cash-flow-projection`

Query: `months: int = 6` (1–24, `422` fuera de rango). Devuelve **siempre** `months` entradas,
una por mes calendario empezando por el actual, aunque el compromiso sea `"0.00"` (para que el
frontend tenga un eje X estable). Suma, por mes de `payment_due_date`, el `total_amount`
calculado (ver `/cards/{id}/statements` más arriba) de los `CardStatement` no pagados.
```json
{
  "reference_currency": "ARS",
  "projection": [
    {"month": "2026-09", "committed_amount": "145000.00"},
    {"month": "2026-10", "committed_amount": "130000.00"},
    {"month": "2026-11", "committed_amount": "0.00"}
  ]
}
```

---

## Activos — `/assets`

CRUD estándar (`GET`, `POST`→`201`, `GET/{id}`, `PATCH/{id}`, `DELETE/{id}`→`204`).
**`AssetCreate`**: `ticker: str`, `name: str`, `type: "stock"|"bond"|"crypto"|"fund"|"other"`,
`currency: str = "USD"`. `(user_id, ticker, type)` es único — `409` si el mismo usuario lo repite
(dos usuarios sí pueden tener cada uno un `AAPL`/`stock`). `DELETE` da `409` si el activo tiene
transacciones cargadas.

---

## Transacciones de inversión — `/investment-transactions` y `/portfolio`

| Método | Path | Query | Notas |
|---|---|---|---|
| GET | `/investment-transactions` | `asset_id`, `account_id` (opcionales) | Ordenadas por fecha descendente. |
| POST | `/investment-transactions` | — | `201`. Ver validaciones y efecto sobre el saldo abajo. |
| GET | `/investment-transactions/{id}` | — | `404`. |
| DELETE | `/investment-transactions/{id}` | — | `204`. Revierte el efecto sobre el saldo. `409` si dejaría la posición del activo en negativo. |
| GET | `/portfolio` | — | Posiciones actuales consolidadas en la moneda de referencia. |

**`InvestmentTransactionCreate`**: `asset_id: int`, `account_id: int?` (opcional — si no se
manda, la transacción queda registrada sin afectar ningún saldo), `type: "buy"|"sell"|"dividend"`,
`quantity: Decimal` (> 0), `price: Decimal` (> 0), `fee: Decimal = "0.00"` (≥ 0), `date: str`.

Para un **dividendo**, `quantity * price` es el monto total percibido — la convención más simple
es cargar `quantity=1` y `price=<monto total>` (el schema no tiene un campo "monto" separado, ver
`agents.md`).

Validado en el router: el activo tiene que existir (`404`); si hay `account_id`, la cuenta tiene
que existir (`404`) y su moneda tiene que coincidir con la del activo (`422`); una venta no puede
superar la posición actual del activo (`422`, calculada sobre el total de compras menos ventas,
sin importar el orden cronológico); el monto neto de la operación (lo que efectivamente entra o
sale de la cuenta) tiene que ser mayor a `0` (`422` — cubre, por ejemplo, una venta cuyo `fee`
supera lo obtenido).

**Efecto sobre el saldo** (solo si se manda `account_id`): se crea una `Transaction` con
`investment_transaction_id` seteado —`expense` por `quantity*price + fee` en una compra,
`income` por `quantity*price - fee` en una venta o dividendo— y se aplica igual que cualquier
otro movimiento (`services/balances.py`). Sin `account_id`, la transacción de inversión no
genera ningún movimiento de caja.

**`DELETE`**: revierte el efecto sobre el saldo (si tenía `account_id`) y borra la `Transaction`
vinculada con un `DELETE` inmediato (no cascada — la FK no tiene `ON DELETE CASCADE` a
propósito). También valida que borrar esta transacción no deje la posición neta del activo en
negativo (ej. borrar una compra de la que ya se vendió parte) — en ese caso, `409`.

### `GET /portfolio`

Solo lista activos con al menos una transacción. El precio promedio ponderado, la cantidad y la
ganancia realizada **se calculan en cada consulta** a partir de `investment_transactions` (mismo
criterio que `CardStatement.total_amount`: nunca un campo desnormalizado que se pueda
desincronizar) — ver el algoritmo en `docs/architecture.md` § Estructura del backend.

Como el resto del dashboard, los montos se consolidan en `reference_currency` vía
`services/exchange_rates.py`; lo que no se puede convertir queda en `unconverted`.

```json
{
  "reference_currency": "ARS",
  "total_cost": "1500000.00",
  "total_realized_gain": "45000.00",
  "unconverted": [],
  "positions": [
    {
      "asset_id": 1, "ticker": "AAPL", "name": "Apple", "type": "stock", "currency": "USD",
      "quantity": "10.00000000", "avg_cost": "150.00000000", "total_cost": "1500.00",
      "realized_gain": "0.00"
    }
  ]
}
```

**Importante**: sin integración con ninguna cotización de mercado (ver "sin Open Banking ni APIs
externas" en `docs/architecture.md`), `total_cost`/`avg_cost` son el **costo** de la posición
(lo que se pagó), no su valor de mercado actual — no hay `unrealized_gain` ni "valor actual del
portafolio". Solo `realized_gain` (de ventas ya concretadas) es calculable sin una cotización
externa.
