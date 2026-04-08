"""Bổ sung cột/bảng khi DB đã tồn tại (chưa dùng Alembic)."""

from sqlalchemy import text
from sqlalchemy.engine import Connection


def run_schema_patches(connection: Connection) -> None:
    connection.execute(
        text("ALTER TABLE activities ADD COLUMN IF NOT EXISTS contact_id UUID REFERENCES contacts(id)")
    )
    connection.execute(text("ALTER TABLE activities ADD COLUMN IF NOT EXISTS deal_id UUID REFERENCES deals(id)"))
    connection.execute(
        text(
            "ALTER TABLE activities ADD COLUMN IF NOT EXISTS occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
        )
    )
    connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(32) NOT NULL DEFAULT 'staff'"))

