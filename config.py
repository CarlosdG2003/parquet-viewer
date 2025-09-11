from pathlib import Path

class Settings:
    PARQUET_DIR = Path("./parquet_files")
    DEFAULT_PAGE_SIZE = 50 # cuantas filas mostrar por pagina
    MAX_PAGE_SIZE = 200 # maximo de filas permitidas

settings = Settings()

# Crear directorio si no existe
settings.PARQUET_DIR.mkdir(exist_ok=True)