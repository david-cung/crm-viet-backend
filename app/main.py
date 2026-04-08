from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.db_patch import run_schema_patches
from app.routers import (
    activities,
    auth,
    campaigns,
    contacts,
    deals,
    integrations,
    meta,
    notifications,
    reports,
    search,
    settings as settings_router,
    tasks,
    users,
)
from app.seed import ensure_company_defaults, ensure_default_admin, seed_if_empty


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        run_schema_patches(conn)
    with SessionLocal() as db:
        seed_if_empty(db)
        ensure_default_admin(db)
        ensure_company_defaults(db)
    yield


app = FastAPI(title="CRM Việt API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://[::1]:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.api_prefix)
for router in (
    contacts,
    deals,
    tasks,
    campaigns,
    activities,
    meta,
    reports,
    search,
    notifications,
    settings_router,
    integrations,
    users,
):
    app.include_router(router.router, prefix=settings.api_prefix)


@app.get("/health")
def health():
    return {"status": "ok"}
