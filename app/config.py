from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://crm:crm@localhost:5432/crm_viet"
    api_prefix: str = "/api"
    jwt_secret_key: str = "dev-change-me-use-openssl-rand-hex-32-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    # SMTP (Sprint 4 — gửi email)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True

    # Zalo OA webhook (Sprint 4 — verify token)
    zalo_oa_verify_token: str = ""

    # AWS S3 (File storage)
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "ap-southeast-1"
    s3_bucket_name: str = ""
    s3_presign_ttl: int = 900

    # Chat encryption (AES-256-GCM) — 32 bytes hex (openssl rand -hex 32)
    chat_encryption_key: str = ""

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"


settings = Settings()
