"""
API Routes - Endpoints principales de la aplicación
Organizados por funcionalidad: Files, Metadata, Charts, Power BI
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import os

from core.database import get_db_session, db_manager
from services.file_service import FileService
from services.metadata_service import MetadataService
from services.chart_service import ChartService
from services.powerbi_metadata_service import PowerBIMetadataService
from models.database_models import (
    FileMetadataCreate, FileMetadataUpdate, FileMetadataResponse,
    CombinedFileInfo, MetadataHistoryResponse,
    PowerBIRelationshipCreate
)

router = APIRouter()

# ============================================================================
# DEPENDENCIES
# ============================================================================

async def get_file_service(db: AsyncSession = Depends(get_db_session)) -> FileService:
    return FileService(db_manager.get_duckdb_connection(), MetadataService(db))

async def get_metadata_service(db: AsyncSession = Depends(get_db_session)) -> MetadataService:
    return MetadataService(db)

async def get_chart_service(db: AsyncSession = Depends(get_db_session)) -> ChartService:
    return ChartService(db_manager.get_duckdb_connection())

async def get_powerbi_service(db: AsyncSession = Depends(get_db_session)) -> PowerBIMetadataService:
    return PowerBIMetadataService(db)

# ============================================================================
# FILES - Gestión de archivos Parquet
# ============================================================================

@router.get("/files", response_model=List[CombinedFileInfo])
async def list_files(
    search: Optional[str] = None,
    responsible: Optional[str] = None,
    permissions: Optional[str] = None,
    tags: Optional[str] = None,
    service: FileService = Depends(get_file_service)
):
    """Lista archivos con datos técnicos y metadatos"""
    tags_list = [t.strip() for t in tags.split(",")] if tags else None
    
    if any([search, responsible, permissions, tags_list]):
        return await service.search_files_combined(search, responsible, permissions, tags_list)
    return await service.get_all_files_combined()

@router.get("/files/{filename}/info", response_model=CombinedFileInfo)
async def get_file_info(filename: str, service: FileService = Depends(get_file_service)):
    """Información completa de un archivo"""
    file_info = await service.get_file_combined(filename)
    if not file_info:
        raise HTTPException(404, "Archivo no encontrado")
    return file_info

@router.get("/files/{filename}/data")
async def get_file_data(
    filename: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    columns: Optional[str] = None,
    service: FileService = Depends(get_file_service)
):
    """Datos paginados del archivo"""
    cols = [c.strip() for c in columns.split(",")] if columns else None
    return await service.get_file_data(filename, page, page_size, cols)

@router.get("/files/{filename}/data/enhanced")
async def get_file_data_enhanced(
    filename: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    columns: Optional[str] = None,
    search: Optional[str] = None,
    sort_column: Optional[str] = None,
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    service: FileService = Depends(get_file_service)
):
    """Datos con búsqueda y ordenamiento"""
    cols = [c.strip() for c in columns.split(",")] if columns else None
    return await service.get_file_data_with_display_names(
        filename, page, page_size, cols, search, sort_column, sort_order
    )

@router.get("/files/{filename}/schema")
async def get_file_schema(filename: str, service: FileService = Depends(get_file_service)):
    """Esquema del archivo"""
    return {"schema": await service.get_file_schema(filename)}

@router.get("/files/{filename}/schema/enhanced")
async def get_file_schema_enhanced(filename: str, service: FileService = Depends(get_file_service)):
    """Esquema con nombres personalizados"""
    return await service.get_file_schema_with_display_names(filename)

# ============================================================================
# METADATA - Gestión de metadatos de negocio
# ============================================================================

@router.post("/metadata", response_model=FileMetadataResponse)
async def create_metadata(
    metadata: FileMetadataCreate,
    service: MetadataService = Depends(get_metadata_service)
):
    """Crea metadatos para un archivo"""
    try:
        return await service.create_metadata(metadata)
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.get("/metadata/{filename}", response_model=FileMetadataResponse)
async def get_metadata(filename: str, service: MetadataService = Depends(get_metadata_service)):
    """Obtiene metadatos de un archivo"""
    metadata = await service.get_metadata_by_filename(filename)
    if not metadata:
        raise HTTPException(404, "Metadatos no encontrados")
    return metadata

@router.put("/metadata/{filename}", response_model=FileMetadataResponse)
async def update_metadata(
    filename: str,
    metadata: FileMetadataUpdate,
    changed_by: str = Query("api"),
    service: MetadataService = Depends(get_metadata_service)
):
    """Actualiza metadatos"""
    updated = await service.update_metadata(filename, metadata, changed_by)
    if not updated:
        raise HTTPException(404, "Archivo no encontrado")
    return updated

@router.delete("/metadata/{filename}")
async def delete_metadata(filename: str, service: MetadataService = Depends(get_metadata_service)):
    """Elimina metadatos"""
    if not await service.delete_metadata(filename):
        raise HTTPException(404, "Metadatos no encontrados")
    return {"message": f"Metadatos de {filename} eliminados"}

@router.get("/metadata/{filename}/history", response_model=List[MetadataHistoryResponse])
async def get_metadata_history(filename: str, service: MetadataService = Depends(get_metadata_service)):
    """Historial de cambios"""
    return await service.get_metadata_history(filename)

@router.get("/metadata/filters/responsibles")
async def get_responsibles(service: MetadataService = Depends(get_metadata_service)):
    """Lista de responsables para filtros"""
    return {"responsibles": await service.get_unique_responsibles()}

@router.get("/metadata/filters/tags")
async def get_tags(service: MetadataService = Depends(get_metadata_service)):
    """Lista de tags para filtros"""
    return {"tags": await service.get_unique_tags()}

# ============================================================================
# SYNC - Sincronización de estadísticas
# ============================================================================

@router.post("/sync/file/{filename}")
async def sync_file(filename: str, service: FileService = Depends(get_file_service)):
    """Sincroniza estadísticas de un archivo"""
    if not await service.sync_file_stats(filename):
        raise HTTPException(404, "Error en sincronización")
    return {"message": f"Estadísticas de {filename} sincronizadas"}

@router.post("/sync/all-files")
async def sync_all_files(service: FileService = Depends(get_file_service)):
    """Sincroniza estadísticas de todos los archivos"""
    results = await service.auto_sync_all_files()
    successful = sum(1 for s in results.values() if s)
    return {
        "message": f"Sincronización completada: {successful}/{len(results)} archivos",
        "results": results
    }

# ============================================================================
# CHARTS - Generación de gráficas
# ============================================================================

@router.get("/files/{filename}/charts/columns")
async def get_chart_columns(filename: str, service: ChartService = Depends(get_chart_service)):
    """Información de columnas para gráficas"""
    return await service.get_file_columns_info(filename)

@router.post("/files/{filename}/charts/custom")
async def generate_chart(
    filename: str,
    chart_config: dict,
    service: ChartService = Depends(get_chart_service)
):
    """Genera gráfica personalizada"""
    return await service.generate_custom_chart(filename, chart_config)

# ============================================================================
# POWER BI - Metadatos y exportación
# ============================================================================

@router.post("/powerbi/extract-metadata/{filename}")
async def extract_powerbi_metadata(
    filename: str,
    service: PowerBIMetadataService = Depends(get_powerbi_service)
):
    """Extrae y guarda metadatos Power BI de un Parquet"""
    parquet_path = os.path.join("parquet_files", filename)
    
    if not os.path.exists(parquet_path):
        raise HTTPException(404, f"Archivo {filename} no encontrado")
    
    result = await service.extract_and_save_from_parquet(filename, parquet_path)
    
    return {
        "success": True,
        "message": f"Metadatos extraídos y guardados",
        "table_name": result["table"].table_name,
        "friendly_name": result["table"].friendly_name,
        "columns_count": result["columns_count"],
        "columns": [
            {
                "original": col.original_column_name,
                "friendly": col.friendly_name,
                "type": col.data_type,
                "format": col.format_string
            }
            for col in result["columns"]
        ]
    }

@router.get("/powerbi/metadata/{filename}")
async def get_powerbi_metadata(
    filename: str,
    service: PowerBIMetadataService = Depends(get_powerbi_service)
):
    """Obtiene metadatos Power BI guardados"""
    table = await service.get_table_metadata(filename)
    if not table:
        raise HTTPException(404, f"No hay metadatos Power BI para {filename}")
    
    columns = await service.get_columns_by_filename(filename)
    
    return {
        "table": {
            "filename": table.filename,
            "table_name": table.table_name,
            "friendly_name": table.friendly_name,
            "description": table.description
        },
        "columns": [
            {
                "original_name": col.original_column_name,
                "friendly_name": col.friendly_name,
                "data_type": col.data_type,
                "format": col.format_string,
                "is_key": col.is_key,
                "aggregation": col.aggregation_function
            }
            for col in columns
        ]
    }

@router.get("/powerbi/tables")
async def list_powerbi_tables(service: PowerBIMetadataService = Depends(get_powerbi_service)):
    """Lista todas las tablas con metadatos Power BI"""
    tables = await service.get_all_tables()
    
    return {
        "count": len(tables),
        "tables": [
            {
                "id": t.id,
                "filename": t.filename,
                "table_name": t.table_name,
                "friendly_name": t.friendly_name,
                "description": t.description
            }
            for t in tables
        ]
    }

@router.post("/powerbi/relationships")
async def create_relationship(
    relationship: PowerBIRelationshipCreate,
    service: PowerBIMetadataService = Depends(get_powerbi_service)
):
    """Crea relación entre dos tablas"""
    try:
        rel = await service.create_relationship(relationship)
        return {
            "success": True,
            "message": "Relación creada",
            "relationship": {
                "id": rel.id,
                "from_table": relationship.from_table_filename,
                "to_table": relationship.to_table_filename,
                "from_column": rel.from_column,
                "to_column": rel.to_column,
                "cardinality": rel.cardinality
            }
        }
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.get("/powerbi/relationships")
async def list_relationships(
    project_name: Optional[str] = None,
    service: PowerBIMetadataService = Depends(get_powerbi_service)
):
    """Lista relaciones Power BI"""
    if project_name:
        rels = await service.get_relationships_by_project(project_name)
    else:
        rels = await service.get_all_relationships()
    
    return {
        "count": len(rels),
        "relationships": [
            {
                "id": r.id,
                "project_name": r.project_name,
                "from_table": r.from_table.friendly_name,
                "to_table": r.to_table.friendly_name,
                "from_column": r.from_column,
                "to_column": r.to_column,
                "cardinality": r.cardinality,
                "cross_filter_direction": r.cross_filter_direction
            }
            for r in rels
        ]
    }

@router.delete("/powerbi/relationships/{relationship_id}")
async def delete_relationship(
    relationship_id: int,
    service: PowerBIMetadataService = Depends(get_powerbi_service)
):
    """Elimina una relación"""
    await service.delete_relationship(relationship_id)
    return {"success": True, "message": "Relación eliminada"}

@router.post("/powerbi/export/prepare")
async def prepare_export(
    filenames: list[str],
    service: PowerBIMetadataService = Depends(get_powerbi_service)
):
    """Prepara datos para exportación a Power BI"""
    data = await service.get_export_data(filenames)
    
    return {
        "success": True,
        "tables_count": len(data["tables"]),
        "tables": [
            {
                "filename": t.filename,
                "table_name": t.table_name,
                "friendly_name": t.friendly_name,
                "columns_count": len(data["columns"][t.filename])
            }
            for t in data["tables"]
        ],
        "relationships_count": len(data["relationships"]),
        "relationships": [
            {
                "from_table": r.from_table.friendly_name,
                "to_table": r.to_table.friendly_name,
                "from_column": r.from_column,
                "to_column": r.to_column
            }
            for r in data["relationships"]
        ]
    }

# ============================================================================
# LEGACY - Mantener compatibilidad con versiones anteriores
# ============================================================================

@router.get("/files/{filename}/stats")
async def get_file_stats_legacy(filename: str, service: FileService = Depends(get_file_service)):
    """Endpoint legacy para estadísticas"""
    info = await service.get_file_combined(filename)
    if not info:
        raise HTTPException(404, "Archivo no encontrado")
    
    return {
        "numeric_stats": {
            "file_size_mb": info.size_mb,
            "row_count": info.row_count,
            "column_count": info.column_count
        }
    }