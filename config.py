from pathlib import Path
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class Settings:
    # Configuración de archivos parquet
    PARQUET_DIR = Path("./parquet_files")
    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 200

    # Configuración PostgreSQL
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "parquet_viewer")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "parquet_user")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "parquet_pass")

    @property
    def database_url(self):
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

settings = Settings()

# Crear directorio si no existe
settings.PARQUET_DIR.mkdir(exist_ok=True)