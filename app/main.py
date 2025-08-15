from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.cache import cache
from app.core.config import settings
from app.core.database.db import engine
from app.core.database.base import Base


# Routers
from content.routers import contents_router, media_router, imports_router
from users.routers import auth_router, users_router, roles_router
from discovery.routers import discovery_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: dev-friendly table creation (replace with Alembic in prod)
    await cache.init()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()
    await cache.close()



app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}


# Users / Auth
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(roles_router)

# Content
app.include_router(contents_router)
app.include_router(media_router)
app.include_router(imports_router)
app.include_router(discovery_router)
