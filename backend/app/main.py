from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.routers import (
    accounts, cards, categories, dashboard, exchange_rates, installment_plans, transactions,
)

settings = get_settings()

app = FastAPI(title="Bolsillito API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accounts.router, prefix="/api/v1")
app.include_router(cards.router, prefix="/api/v1")
app.include_router(categories.router, prefix="/api/v1")
app.include_router(transactions.router, prefix="/api/v1")
app.include_router(installment_plans.router, prefix="/api/v1")
app.include_router(exchange_rates.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """Traduce violaciones de constraints de Postgres (FK, CHECK, UNIQUE) a 409 en vez de un
    500 genérico -- ver la convención de errores en docs/api-spec.md."""
    return JSONResponse(
        status_code=409,
        content={"detail": "La operación viola una regla de integridad de datos."},
    )


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
