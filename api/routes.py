from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session, db_manager
from services.metadata_service import MetadataService
from services.file_service import FileService
from models.database_models import (
    FileMetadataCreate, 
    FileMetadataUpdate, 
    FileMetadataResponse,
    CombinedFileInfo,
    MetadataHistoryResponse
)

router = APIRouter()

# Dependency para crear FileService con ambas conexiones
async def get_file_service(db_session: AsyncSession = Depends(get_db_session)) -> FileService:
    metadata_service = MetadataService(db_session)
    duckdb_conn = db_manager.get_duckdb_connection()
    return FileService(duckdb_conn, metadata_service)

# Dependency para MetadataService
async def get_metadata_service(db_session: AsyncSession = Depends(get_db_session)) -> MetadataService:
    return MetadataService(db_session)

@router.get("/files", response_model=List[CombinedFileInfo])
async def list_files_combined(
    search: Optional[str] = Query(None, description="Término de búsqueda"),
    responsible: Optional[str] = Query(None, description="Filtrar por responsable"),
    permissions: Optional[str] = Query(None, description="Filtrar por permisos"),
    tags: Optional[str] = Query(None, description="Tags separados por comas"),
    file_service: FileService = Depends(get_file_service)
):
    """Lista todos los archivos combinando datos técnicos (DuckDB) + metadatos (PostgreSQL)"""
    try:
        # Procesar tags si se proporcionan
        tags_list = [tag.strip() for tag in tags.split(",")] if tags else None
        
        if search or responsible or permissions or tags_list:
            # Búsqueda con filtros
            return await file_service.search_files_combined(
                search_term=search,
                responsible=responsible,
                permissions=permissions,
                tags=tags_list
            )
        else:
            # Obtener todos los archivos
            return await file_service.get_all_files_combined()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener archivos: {str(e)}")

@router.get("/files/{filename}/info", response_model=CombinedFileInfo)
async def get_file_info_combined(
    filename: str,
    file_service: FileService = Depends(get_file_service)
):
    """Obtiene información combinada de un archivo específico"""
    try:
        file_info = await file_service.get_file_combined(filename)
        if not file_info:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        return file_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener información: {str(e)}")

@router.get("/files/{filename}/data")
async def get_file_data(
    filename: str,
    page: int = Query(1, ge=1, description="Página"),
    page_size: int = Query(50, ge=1, le=200, description="Tamaño de página"),
    columns: Optional[str] = Query(None, description="Columnas separadas por comas"),
    file_service: FileService = Depends(get_file_service)
):
    """Obtiene datos paginados del archivo usando DuckDB"""
    try:
        column_list = [col.strip() for col in columns.split(",")] if columns else None
        return await file_service.get_file_data(filename, page, page_size, column_list)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener datos: {str(e)}")

@router.get("/files/{filename}/schema")
async def get_file_schema(
    filename: str,
    file_service: FileService = Depends(get_file_service)
):
    """Obtiene el esquema del archivo usando DuckDB"""
    try:
        schema = await file_service.get_file_schema(filename)
        return {"schema": schema}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener esquema: {str(e)}")

# === ENDPOINTS DE METADATOS (PostgreSQL) ===

@router.post("/metadata", response_model=FileMetadataResponse)
async def create_file_metadata(
    metadata: FileMetadataCreate,
    metadata_service: MetadataService = Depends(get_metadata_service)
):
    """Crea nuevos metadatos para un archivo"""
    try:
        return await metadata_service.create_metadata(metadata)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear metadatos: {str(e)}")

@router.get("/metadata/{filename}", response_model=FileMetadataResponse)
async def get_file_metadata(
    filename: str,
    metadata_service: MetadataService = Depends(get_metadata_service)
):
    """Obtiene metadatos de un archivo específico"""
    metadata = await metadata_service.get_metadata_by_filename(filename)
    if not metadata:
        raise HTTPException(status_code=404, detail="Metadatos no encontrados")
    return metadata

@router.put("/metadata/{filename}", response_model=FileMetadataResponse)
async def update_file_metadata(
    filename: str,
    metadata: FileMetadataUpdate,
    changed_by: str = Query("api", description="Usuario que realiza el cambio"),
    metadata_service: MetadataService = Depends(get_metadata_service)
):
    """Actualiza metadatos de un archivo"""
    try:
        updated = await metadata_service.update_metadata(filename, metadata, changed_by)
        if not updated:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        return updated
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar metadatos: {str(e)}")

@router.delete("/metadata/{filename}")
async def delete_file_metadata(
    filename: str,
    metadata_service: MetadataService = Depends(get_metadata_service)
):
    """Elimina metadatos de un archivo"""
    try:
        deleted = await metadata_service.delete_metadata(filename)
        if not deleted:
            raise HTTPException(status_code=404, detail="Metadatos no encontrados")
        return {"message": f"Metadatos de {filename} eliminados correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar metadatos: {str(e)}")

@router.get("/metadata/{filename}/history", response_model=List[MetadataHistoryResponse])
async def get_file_metadata_history(
    filename: str,
    metadata_service: MetadataService = Depends(get_metadata_service)
):
    """Obtiene el historial de cambios de metadatos"""
    try:
        return await metadata_service.get_metadata_history(filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener historial: {str(e)}")

# === ENDPOINTS DE UTILIDAD ===

@router.get("/metadata/filters/responsibles")
async def get_unique_responsibles(
    metadata_service: MetadataService = Depends(get_metadata_service)
):
    """Obtiene lista de responsables únicos para filtros"""
    try:
        responsibles = await metadata_service.get_unique_responsibles()
        return {"responsibles": responsibles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener responsables: {str(e)}")

@router.get("/metadata/filters/tags")
async def get_unique_tags(
    metadata_service: MetadataService = Depends(get_metadata_service)
):
    """Obtiene lista de tags únicos para filtros"""
    try:
        tags = await metadata_service.get_unique_tags()
        return {"tags": tags}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener tags: {str(e)}")

@router.post("/sync/file/{filename}")
async def sync_file_stats(
    filename: str,
    file_service: FileService = Depends(get_file_service)
):
    """Sincroniza estadísticas técnicas de un archivo con sus metadatos"""
    try:
        success = await file_service.sync_file_stats(filename)
        if not success:
            raise HTTPException(status_code=404, detail="Archivo no encontrado o error en sincronización")
        return {"message": f"Estadísticas de {filename} sincronizadas correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en sincronización: {str(e)}")

@router.post("/sync/all-files")
async def sync_all_files_stats(
    file_service: FileService = Depends(get_file_service)
):
    """Sincroniza estadísticas técnicas de todos los archivos con sus metadatos"""
    try:
        results = await file_service.auto_sync_all_files()
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        
        return {
            "message": f"Sincronización completada: {successful}/{total} archivos sincronizados",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en sincronización masiva: {str(e)}")

# === ENDPOINT LEGACY (mantener compatibilidad) ===

@router.get("/files/{filename}/stats")
async def get_file_stats_legacy(
    filename: str,
    file_service: FileService = Depends(get_file_service)
):
    """Endpoint legacy para estadísticas - redirige a info combinada"""
    try:
        file_info = await file_service.get_file_combined(filename)
        if not file_info:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        # Formato legacy para compatibilidad
        return {
            "numeric_stats": {
                "file_size_mb": file_info.size_mb,
                "row_count": file_info.row_count,
                "column_count": file_info.column_count
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener estadísticas: {str(e)}")