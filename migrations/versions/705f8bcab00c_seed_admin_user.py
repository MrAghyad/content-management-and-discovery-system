"""seed admin user

Revision ID: 705f8bcab00c
Revises: 1fbe8b4c1564
Create Date: 2025-08-17 13:32:45.007435+00:00

"""
from typing import Sequence, Union

from alembic import op
import os
import uuid
from datetime import datetime, timezone

from alembic import op
from sqlalchemy import text
from sqlalchemy.engine import Connection


# revision identifiers, used by Alembic.
revision: str = '705f8bcab00c'
down_revision: Union[str, Sequence[str], None] = '1fbe8b4c1564'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def _get_env(var: str, default: str) -> str:
    val = os.getenv(var, default).strip()
    if not val:
        return default
    return val

def upgrade() -> None:
    """
    Upsert admin role and admin user, and bind them together.
    Reads ADMIN_EMAIL and ADMIN_PASSWORD from env.
    """
    conn: Connection = op.get_bind()

    admin_email = "admin@example.com"
    admin_password ="ChangeMe123!"

    # Use the app's hashing function to keep the same format
    try:
        from app.core.security import hash_password  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "Failed to import app.core.security.hash_password inside migration. "
            "Ensure application code is available in PYTHONPATH."
        ) from e

    password_hash = hash_password(admin_password)

    # 1) Ensure role 'admin' exists
    role_id = conn.execute(
        text("SELECT id FROM roles WHERE name = 'admin'")
    ).scalar()

    if role_id is None:
        role_id = str(uuid.uuid4())
        conn.execute(
            text(
                """
                INSERT INTO roles (id, name, created_at)
                VALUES (:id, 'admin', :created_at)
                """
            ),
            {"id": role_id, "created_at": datetime.now(timezone.utc)},
        )

    # 2) Ensure user exists
    user_row = conn.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": admin_email},
    ).first()

    if user_row is None:
        user_id = str(uuid.uuid4())
        conn.execute(
            text(
                """
                INSERT INTO users (id, email, password_hash, is_active, created_at)
                VALUES (:id, :email, :password_hash, TRUE, :created_at)
                """
            ),
            {
                "id": user_id,
                "email": admin_email,
                "password_hash": password_hash,
                "created_at": datetime.now(timezone.utc),
            },
        )
    else:
        user_id = user_row[0]

    # 3) Ensure mapping exists
    exists = conn.execute(
        text(
            """
            SELECT 1 FROM user_roles
            WHERE user_id = :uid AND role_id = :rid
            """
        ),
        {"uid": user_id, "rid": role_id},
    ).first()

    if exists is None:
        conn.execute(
            text(
                """
                INSERT INTO user_roles (user_id, role_id)
                VALUES (:uid, :rid)
                """
            ),
            {"uid": user_id, "rid": role_id},
        )


def downgrade() -> None:
    """
    Optionally remove ONLY the seeded admin user for reversibility.
    Does not remove the 'admin' role (it may be in use).
    """
    conn: Connection = op.get_bind()

    admin_email = "admin@example.com"

    row = conn.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": admin_email},
    ).first()

    if row:
        uid = row[0]
        # remove role mapping, then user
        conn.execute(text("DELETE FROM user_roles WHERE user_id = :uid"), {"uid": uid})
        conn.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": uid})
