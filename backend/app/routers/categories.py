from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Category, User
from app.schemas.categories import CategoryCreate, CategoryRead, CategoryUpdate
from app.services.auth import get_current_user

router = APIRouter(prefix="/categories", tags=["categories"])


async def _get_category_or_404(category_id: int, user: User, session: AsyncSession) -> Category:
    category = (
        await session.execute(
            select(Category).where(Category.id == category_id, Category.user_id == user.id)
        )
    ).scalar_one_or_none()
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada")
    return category


@router.get("", response_model=list[CategoryRead])
async def list_categories(
    current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> list[Category]:
    stmt = select(Category).where(Category.user_id == current_user.id).order_by(Category.name)
    return list((await session.execute(stmt)).scalars().all())


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Category:
    category = Category(**payload.model_dump(), user_id=current_user.id)
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category


@router.get("/{category_id}", response_model=CategoryRead)
async def get_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Category:
    return await _get_category_or_404(category_id, current_user, session)


@router.patch("/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: int,
    payload: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Category:
    category = await _get_category_or_404(category_id, current_user, session)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    await session.commit()
    await session.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Si la categoría está en uso (transacciones o planes de cuotas), la FK sin
    ON DELETE CASCADE hace que Postgres rechace el borrado -- el handler global de
    IntegrityError en app.main lo traduce a 409."""
    category = await _get_category_or_404(category_id, current_user, session)
    await session.delete(category)
    await session.commit()
