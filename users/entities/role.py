from pydantic import BaseModel
from typing import Literal
from uuid import UUID
from datetime import datetime

RoleLiteral = Literal["admin", "editor", "viewer"]

class RoleOut(BaseModel):
    id: UUID
    name: RoleLiteral
    created_at: datetime
    class Config:
        from_attributes = True

class AssignRoleIn(BaseModel):
    role: RoleLiteral
