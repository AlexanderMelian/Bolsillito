from pydantic import BaseModel, ConfigDict, field_validator


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str
    password: str

    @field_validator("username")
    @classmethod
    def check_username(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("username debe tener al menos 3 caracteres")
        return value

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("password debe tener al menos 8 caracteres")
        return value


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


class Token(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    token_type: str = "bearer"
    user: UserRead
