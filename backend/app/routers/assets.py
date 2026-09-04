from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Asset
from app.schemas.assets import AssetCreate, AssetRead, AssetUpdate

router = APIRouter(prefix="/assets", tags=["assets"])


async def _get_asset_or_404(asset_id: int, session: AsyncSession) -> Asset:
    asset = await session.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activo no encontrado")
    return asset


@router.get("", response_model=list[AssetRead])
async def list_assets(session: AsyncSession = Depends(get_session)) -> list[Asset]:
    stmt = select(Asset).order_by(Asset.ticker)
    return list((await session.execute(stmt)).scalars().all())


@router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
async def create_asset(payload: AssetCreate, session: AsyncSession = Depends(get_session)) -> Asset:
    asset = Asset(**payload.model_dump())
    session.add(asset)
    await session.commit()
    await session.refresh(asset)
    return asset


@router.get("/{asset_id}", response_model=AssetRead)
async def get_asset(asset_id: int, session: AsyncSession = Depends(get_session)) -> Asset:
    return await _get_asset_or_404(asset_id, session)


@router.patch("/{asset_id}", response_model=AssetRead)
async def update_asset(
    asset_id: int, payload: AssetUpdate, session: AsyncSession = Depends(get_session)
) -> Asset:
    asset = await _get_asset_or_404(asset_id, session)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(asset, field, value)
    await session.commit()
    await session.refresh(asset)
    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(asset_id: int, session: AsyncSession = Depends(get_session)) -> None:
    """Si el activo tiene transacciones cargadas, la FK (sin ON DELETE CASCADE a propósito)
    hace que Postgres rechace el borrado -- el handler global de IntegrityError lo traduce a 409."""
    asset = await _get_asset_or_404(asset_id, session)
    await session.delete(asset)
    await session.commit()
