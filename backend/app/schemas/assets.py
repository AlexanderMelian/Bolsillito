from pydantic import BaseModel, ConfigDict

from app.models import AssetType


class AssetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str
    name: str
    type: AssetType
    currency: str = "USD"


class AssetUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str | None = None
    name: str | None = None
    type: AssetType | None = None
    currency: str | None = None


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    name: str
    type: AssetType
    currency: str
