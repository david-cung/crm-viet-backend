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

    # SMTP settings (single row id=1)
    connection.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS smtp_settings (
              id INTEGER PRIMARY KEY,
              host VARCHAR(255) NOT NULL DEFAULT '',
              port INTEGER NOT NULL DEFAULT 587,
              "user" VARCHAR(255) NOT NULL DEFAULT '',
              password VARCHAR(255) NOT NULL DEFAULT '',
              from_email VARCHAR(255) NOT NULL DEFAULT '',
              use_tls BOOLEAN NOT NULL DEFAULT TRUE
            )
            """
        )
    )

    # Chat tables (Module 1)
    connection.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS conversations (
              id UUID PRIMARY KEY,
              type VARCHAR(16) NOT NULL DEFAULT 'direct',
              name VARCHAR(255) NOT NULL DEFAULT '',
              avatar_url VARCHAR(512) NOT NULL DEFAULT '',
              created_by UUID NOT NULL REFERENCES users(id),
              created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
              updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    connection.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS conversation_members (
              id UUID PRIMARY KEY,
              conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
              user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              role VARCHAR(16) NOT NULL DEFAULT 'member',
              joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
              last_read_at TIMESTAMPTZ NULL,
              is_muted BOOLEAN NOT NULL DEFAULT FALSE
            )
            """
        )
    )
    connection.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS message_files (
              id UUID PRIMARY KEY,
              message_id UUID NULL,
              uploader_id UUID NOT NULL REFERENCES users(id),
              original_name VARCHAR(512) NOT NULL DEFAULT '',
              file_size INTEGER NOT NULL DEFAULT 0,
              mime_type VARCHAR(255) NOT NULL DEFAULT '',
              s3_key VARCHAR(1024) NOT NULL,
              thumbnail_s3_key VARCHAR(1024) NULL,
              created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    connection.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS messages (
              id UUID PRIMARY KEY,
              conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
              sender_id UUID NOT NULL REFERENCES users(id),
              content_encrypted TEXT NOT NULL DEFAULT '',
              content_iv VARCHAR(255) NOT NULL DEFAULT '',
              content_tag VARCHAR(255) NOT NULL DEFAULT '',
              message_type VARCHAR(16) NOT NULL DEFAULT 'text',
              file_id UUID NULL REFERENCES message_files(id),
              reply_to_id UUID NULL REFERENCES messages(id),
              reactions JSONB NOT NULL DEFAULT '{}'::jsonb,
              is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
              deleted_at TIMESTAMPTZ NULL,
              edited_at TIMESTAMPTZ NULL,
              created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    connection.execute(text("ALTER TABLE message_files ADD CONSTRAINT IF NOT EXISTS fk_message_files_message_id FOREIGN KEY (message_id) REFERENCES messages(id)"))
    connection.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS message_read_receipts (
              message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
              user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              read_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
              PRIMARY KEY (message_id, user_id)
            )
            """
        )
    )

