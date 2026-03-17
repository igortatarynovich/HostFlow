from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserPublic(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool


class LoginResponse(Token):
    user: UserPublic


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str
