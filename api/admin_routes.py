from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

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