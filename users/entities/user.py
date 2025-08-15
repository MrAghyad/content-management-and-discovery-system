from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime
from typing import List
from .role import RoleLiteral

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    roles: List[RoleLiteral] = ["viewer"]

class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    is_active: bool
    roles: List[RoleLiteral]
    created_at: datetime
    class Config:
        from_attributes = True
