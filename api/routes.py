from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional

from models.parquet_file import ParquetFile
from config import settings

router = APIRouter()

# lista todos los archivos parquet
@router.get("/files") 
async def list_files() -> List[Dict[str, Any]]:
    files = []
    for file_path in settings.PARQUET_DIR.glob("*.parquet"):
        parquet_file = ParquetFile(file_path)
        files.append(parquet_file.get_info())
    return files

# metadatos de un archivo especifico
@router.get("/files/{filename}/info")
async def get_file_info(filename: str) -> Dict[str, Any]:
    file_path = settings.PARQUET_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    parquet_file = ParquetFile(file_path)
    return parquet_file.get_info()

# Esquema detallado
@router.get("/files/{filename}/schema")
async def get_file_schema(filename: str) -> Dict[str, Any]:
    file_path = settings.PARQUET_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    try:
        parquet_file = ParquetFile(file_path)
        schema = parquet_file.get_schema()
        return {"schema": schema}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener esquema: {str(e)}")

# Datos paginados
@router.get("/files/{filename}/data")
async def get_file_data(
    filename: str, 
    page: int = 1, 
    page_size: int = 50,
    columns: Optional[str] = None
) -> Dict[str, Any]:
    file_path = settings.PARQUET_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    if page_size > settings.MAX_PAGE_SIZE:
        page_size = settings.MAX_PAGE_SIZE
    
    try:
        parquet_file = ParquetFile(file_path)
        column_list = columns.split(',') if columns else None
        if column_list:
            column_list = [col.strip() for col in column_list]
        
        return parquet_file.get_data(page, page_size, column_list)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener datos: {str(e)}")

# Estadisticas numericas
@router.get("/files/{filename}/stats")
async def get_file_stats(filename: str) -> Dict[str, Any]:
    file_path = settings.PARQUET_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    try:
        parquet_file = ParquetFile(file_path)
        return parquet_file.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener estadísticas: {str(e)}")