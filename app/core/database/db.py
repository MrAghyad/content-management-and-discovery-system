from celery.signals import worker_process_init
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session_maker = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


def _get_session_factory() -> async_sessionmaker:
    _engine = create_async_engine(
        settings.database_url,  # must be asyncpg URL: postgresql+asyncpg://...
        pool_pre_ping=True,
        future=True,
    )
    _SessionFactory = async_sessionmaker(_engine, expire_on_commit=False)
    return _SessionFactory

@worker_process_init.connect
def reset_db_connection(**kwargs):
    """
    Reset database connection pool when Celery worker process starts.
    This prevents sharing database connections between forked processes.
    """
    print("Disposing database engine in Celery worker process")

    try:
        engine.dispose()
        print("Successfully disposed database engine connections")
    except Exception as e:
        print(f"Error disposing database engine: {str(e)}")