from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from core.database import get_db_session
from core.security import verify_admin_credentials
from services.admin_service import AdminService
from services.metadata_service import MetadataService
from models.database_models import (
    FileMetadataCreate, 
    FileMetadataUpdate, 
    FileMetadataResponse
)

admin_router = APIRouter()

# Dependency para AdminService
async def get_admin_service(
    db_session: AsyncSession = Depends(get_db_session),
    admin_user: str = Depends(verify_admin_credentials)
) -> AdminService:
    return AdminService(db_session)

# Dependency para AdminService con usuario
async def get_admin_service_with_user(
    db_session: AsyncSession = Depends(get_db_session),
    admin_user: str = Depends(verify_admin_credentials)
) -> tuple[AdminService, str]:
    return AdminService(db_session), admin_user

# Dependency para MetadataService con autenticación
async def get_authenticated_metadata_service(
    db_session: AsyncSession = Depends(get_db_session),
    admin_user: str = Depends(verify_admin_credentials)
) -> tuple[MetadataService, str]:
    return MetadataService(db_session), admin_user

@admin_router.get("/", response_class=HTMLResponse)
async def admin_dashboard_page(admin_user: str = Depends(verify_admin_credentials)):
    """Página principal del panel de administrador"""
    with open("static/admin.html", "r", encoding="utf-8") as file:
        return HTMLResponse(content=file.read())

@admin_router.get("/dashboard")
async def get_dashboard_stats(
    admin_service: AdminService = Depends(get_admin_service)
):
    """Obtiene estadísticas para el dashboard"""
    try:
        return await admin_service.get_dashboard_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}")

@admin_router.get("/files-without-metadata")
async def get_files_without_metadata(
    admin_service: AdminService = Depends(get_admin_service)
):
    """Lista archivos que no tienen metadatos"""
    try:
        return await admin_service.get_files_without_metadata()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo archivos: {str(e)}")

@admin_router.get("/metadata")
async def list_metadata_for_admin(
    search: Optional[str] = Query(None, description="Buscar en nombre, título o responsable"),
    responsible: Optional[str] = Query(None, description="Filtrar por responsable"),
    permissions: Optional[str] = Query(None, description="Filtrar por permisos"),
    admin_service: AdminService = Depends(get_admin_service)
):
    """Lista metadatos con filtros para el admin"""
    try:
        return await admin_service.get_metadata_summary(search, responsible, permissions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo metadatos: {str(e)}")

@admin_router.get("/filter-options")
async def get_filter_options(
    admin_service: AdminService = Depends(get_admin_service)
):
    """Obtiene opciones para filtros del admin"""
    try:
        return await admin_service.get_filter_options()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo opciones: {str(e)}")

@admin_router.get("/metadata/{filename}")
async def get_file_metadata_for_admin(
    filename: str,
    admin_service: AdminService = Depends(get_admin_service)
):
    """Obtiene información detallada de un archivo para edición"""
    try:
        file_info = await admin_service.get_detailed_file_info(filename)
        if not file_info:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        return file_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo información: {str(e)}")

@admin_router.post("/metadata", response_model=FileMetadataResponse)
async def create_metadata_as_admin(
    metadata: FileMetadataCreate,
    services: tuple[MetadataService, str] = Depends(get_authenticated_metadata_service)
):
    """Crea metadatos como administrador"""
    metadata_service, admin_user = services
    try:
        return await metadata_service.create_metadata(metadata)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creando metadatos: {str(e)}")

@admin_router.put("/metadata/{filename}", response_model=FileMetadataResponse)
async def update_metadata_as_admin(
    filename: str,
    metadata: FileMetadataUpdate,
    services: tuple[MetadataService, str] = Depends(get_authenticated_metadata_service)
):
    """Actualiza metadatos como administrador"""
    metadata_service, admin_user = services
    try:
        updated = await metadata_service.update_metadata(filename, metadata, admin_user)
        if not updated:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        return updated
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error actualizando metadatos: {str(e)}")

@admin_router.delete("/metadata/{filename}")
async def delete_metadata_as_admin(
    filename: str,
    services: tuple[MetadataService, str] = Depends(get_authenticated_metadata_service)
):
    """Elimina metadatos como administrador"""
    metadata_service, admin_user = services
    try:
        deleted = await metadata_service.delete_metadata(filename)
        if not deleted:
            raise HTTPException(status_code=404, detail="Metadatos no encontrados")
        return {"message": f"Metadatos de {filename} eliminados por {admin_user}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error eliminando metadatos: {str(e)}")

@admin_router.get("/user-info")
async def get_current_admin_user(admin_user: str = Depends(verify_admin_credentials)):
    """Obtiene información del usuario admin actual"""
    return {
        "username": admin_user,
        "role": "administrator",
        "authenticated_at": "now"
    }

# === NUEVOS ENDPOINTS PARA GESTIÓN DE COLUMNAS ===

@admin_router.get("/files/{filename}/columns")
async def get_file_columns_admin(
    filename: str,
    admin_service: AdminService = Depends(get_admin_service)
):
    """Obtiene información de columnas para administración"""
    try:
        return await admin_service.get_file_columns_admin(filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo columnas: {str(e)}")

@admin_router.put("/files/{filename}/columns/{column_name}")
async def update_column_metadata_admin(
    filename: str,
    column_name: str,
    updates: Dict[str, Any],
    services: tuple[AdminService, str] = Depends(get_admin_service_with_user)
):
    """Actualiza metadatos de una columna específica"""
    admin_service, admin_user = services
    try:
        result = await admin_service.update_column_metadata(
            filename, column_name, updates, admin_user
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error actualizando columna: {str(e)}")

@admin_router.post("/files/{filename}/columns/bulk-update")
async def bulk_update_columns_admin(
    filename: str,
    columns_updates: List[Dict[str, Any]],
    services: tuple[AdminService, str] = Depends(get_admin_service_with_user)
):
    """Actualiza metadatos de múltiples columnas de una vez"""
    admin_service, admin_user = services
    try:
        results = await admin_service.bulk_update_columns(
            filename, columns_updates, admin_user
        )
        return {
            "filename": filename,
            "results": results,
            "message": f"Procesadas {len(columns_updates)} columnas"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en actualización masiva: {str(e)}")

@admin_router.post("/files/{filename}/columns/sync")
async def sync_file_columns_admin(
    filename: str,
    admin_service: AdminService = Depends(get_admin_service)
):
    """Sincroniza metadatos de columnas con el esquema actual del archivo"""
    try:
        result = await admin_service.sync_file_columns_metadata(filename)
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sincronizando columnas: {str(e)}")

@admin_router.get("/files/{filename}/columns/display-schema")
async def get_columns_display_schema_admin(
    filename: str,
    admin_service: AdminService = Depends(get_admin_service)
):
    """Obtiene esquema de columnas con nombres personalizados"""
    try:
        return await admin_service.get_columns_display_schema(filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo esquema: {str(e)}")

@admin_router.post("/files/{filename}/columns/{column_name}/reset")
async def reset_column_metadata_admin(
    filename: str,
    column_name: str,
    admin_service: AdminService = Depends(get_admin_service)
):
    """Resetea metadatos de una columna a valores por defecto"""
    try:
        result = await admin_service.reset_column_metadata(filename, column_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reseteando columna: {str(e)}")

@admin_router.get("/files/{filename}/columns/export")
async def export_columns_config(
    filename: str,
    admin_service: AdminService = Depends(get_admin_service)
):
    """Exporta configuración de columnas para backup/importación"""
    try:
        columns_info = await admin_service.get_file_columns_admin(filename)
        
        export_data = {
            "filename": filename,
            "export_date": datetime.utcnow().isoformat(),
            "columns": [
                {
                    "original_name": col["original_name"],
                    "display_name": col["display_name"],
                    "description": col["description"],
                    "is_visible": col["is_visible"],
                    "sort_order": col["sort_order"]
                }
                for col in columns_info["columns"]
                if col["has_metadata"]
            ]
        }
        
        return export_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exportando configuración: {str(e)}")

@admin_router.post("/files/{filename}/columns/import")
async def import_columns_config(
    filename: str,
    config_data: Dict[str, Any],
    services: tuple[AdminService, str] = Depends(get_admin_service_with_user)
):
    """Importa configuración de columnas desde backup"""
    admin_service, admin_user = services
    try:
        if config_data.get("filename") != filename:
            raise HTTPException(
                status_code=400, 
                detail="El filename en la configuración no coincide"
            )
        
        columns_updates = [
            {
                "original_column_name": col["original_name"],
                "display_name": col["display_name"],
                "description": col["description"],
                "is_visible": col["is_visible"],
                "sort_order": col["sort_order"]
            }
            for col in config_data.get("columns", [])
        ]
        
        results = await admin_service.bulk_update_columns(
            filename, columns_updates, admin_user
        )
        
        return {
            "filename": filename,
            "imported_columns": len(columns_updates),
            "results": results,
            "message": "Configuración importada exitosamente"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error importando configuración: {str(e)}")

@admin_router.get("/files/{filename}/preview-with-custom-names")
async def preview_file_with_custom_names(
    filename: str,
    limit: int = Query(10, ge=1, le=100, description="Número de filas a mostrar"),
    admin_service: AdminService = Depends(get_admin_service)
):
    """Vista previa del archivo usando nombres de columnas personalizados"""
    try:
        from core.database import db_manager
        from pathlib import Path
        from config import settings
        
        # Obtener esquema personalizado
        display_schema = await admin_service.get_columns_display_schema(filename)
        
        # Obtener datos del archivo
        duckdb_conn = db_manager.get_duckdb_connection()
        file_path = settings.PARQUET_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        # Construir query solo con columnas visibles
        visible_columns = [
            f'"{col["original_name"]}" AS "{col["display_name"]}"'
            for col in display_schema["columns"]
        ]
        
        if not visible_columns:
            return {
                "filename": filename,
                "message": "No hay columnas visibles",
                "data": [],
                "columns": []
            }
        
        columns_str = ", ".join(visible_columns)
        query = f'''
            SELECT {columns_str}
            FROM parquet_scan('{file_path}')
            LIMIT {limit}
        '''
        
        df = duckdb_conn.execute(query).fetchdf()
        
        return {
            "filename": filename,
            "has_custom_names": display_schema["has_custom_names"],
            "total_visible_columns": len(display_schema["columns"]),
            "preview_rows": limit,
            "columns": [
                {
                    "name": col["display_name"],
                    "original_name": col["original_name"],
                    "description": col["description"],
                    "data_type": col["data_type"]
                }
                for col in display_schema["columns"]
            ],
            "data": df.to_dict(orient="records")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo preview: {str(e)}")