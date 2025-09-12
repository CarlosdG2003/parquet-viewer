import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
import duckdb
from typing import AsyncGenerator

# Base para modelos SQLAlchemy
Base = declarative_base()

# Configuración PostgreSQL
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://parquet_user:parquet_pass@localhost:5432/parquet_viewer"
)

# Motor SQLAlchemy para PostgreSQL
engine = create_async_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=False  # Cambia a True para ver queries SQL
)

# Sesión async
AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

class DatabaseManager:
    """Gestor centralizado para ambas bases de datos"""
    
    def __init__(self):
        self.duckdb_conn = None
        self.postgres_engine = engine
    
    def get_duckdb_connection(self):
        """Obtiene conexión DuckDB (para archivos parquet)"""
        if self.duckdb_conn is None:
            self.duckdb_conn = duckdb.connect()
        return self.duckdb_conn
    
    async def get_postgres_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Obtiene sesión PostgreSQL async (para metadatos)"""
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

# Instancia global
db_manager = DatabaseManager()

# Dependency para FastAPI
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency para inyección de dependencias en FastAPI"""
    async for session in db_manager.get_postgres_session():
        yield session