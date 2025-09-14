from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct
from pathlib import Path
from datetime import datetime, timedelta
import os

from models.database_models import FileMetadata, MetadataHistory
from services.metadata_service import MetadataService
from config import settings

class AdminService:
    """Servicio para funcionalidades específicas del administrador"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.metadata_service = MetadataService(db_session)

    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas para el dashboard del admin"""
        
        # Contar archivos físicos
        parquet_files = list(settings.PARQUET_DIR.glob("*.parquet"))
        total_files = len(parquet_files)
        
        # Contar archivos con metadatos
        query = select(func.count(FileMetadata.id))
        result = await self.db.execute(query)
        files_with_metadata = result.scalar() or 0
        
        # Archivos sin metadatos
        files_without_metadata = total_files - files_with_metadata
        
        # Último archivo actualizado
        last_updated_query = select(FileMetadata.updated_at).order_by(
            FileMetadata.updated_at.desc()
        ).limit(1)
        last_updated_result = await self.db.execute(last_updated_query)
        last_updated = last_updated_result.scalar_one_or_none()
        
        # Actividad reciente (últimos 7 días)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_activity_query = select(MetadataHistory).where(
            MetadataHistory.changed_at >= seven_days_ago
        ).order_by(MetadataHistory.changed_at.desc()).limit(10)
        
        recent_activity_result = await self.db.execute(recent_activity_query)
        recent_activity = recent_activity_result.scalars().all()
        
        return {
            "total_files": total_files,
            "files_with_metadata": files_with_metadata,
            "files_without_metadata": files_without_metadata,
            "last_updated": last_updated.isoformat() if last_updated else None,
            "recent_activity": [
                {
                    "id": activity.id,
                    "field_changed": activity.field_changed,
                    "changed_by": activity.changed_by,
                    "changed_at": activity.changed_at.isoformat(),
                    "file_id": activity.file_id
                }
                for activity in recent_activity
            ]
        }

    async def get_files_without_metadata(self) -> List[Dict[str, Any]]:
        """Obtiene lista de archivos que no tienen metadatos"""
        
        # Obtener todos los archivos con metadatos
        query = select(FileMetadata.filename)
        result = await self.db.execute(query)
        files_with_metadata = {row[0] for row in result.fetchall()}
        
        # Obtener archivos físicos sin metadatos
        files_without_metadata = []
        for parquet_file in settings.PARQUET_DIR.glob("*.parquet"):
            if parquet_file.name not in files_with_metadata:
                stat = parquet_file.stat()
                files_without_metadata.append({
                    "filename": parquet_file.name,
                    "size_bytes": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        return sorted(files_without_metadata, key=lambda x: x["modified"], reverse=True)

    async def get_metadata_summary(
        self, 
        search: Optional[str] = None,
        responsible: Optional[str] = None,
        permissions: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Obtiene resumen de metadatos para la tabla del admin"""
        
        query = select(FileMetadata)
        
        # Aplicar filtros
        if search:
            search_pattern = f"%{search.lower()}%"
            query = query.where(
                FileMetadata.title.ilike(search_pattern) |
                FileMetadata.filename.ilike(search_pattern) |
                FileMetadata.responsible.ilike(search_pattern)
            )
        
        if responsible:
            query = query.where(FileMetadata.responsible == responsible)
            
        if permissions:
            query = query.where(FileMetadata.permissions == permissions)
        
        query = query.order_by(FileMetadata.updated_at.desc())
        result = await self.db.execute(query)
        metadata_list = result.scalars().all()
        
        return [
            {
                "id": metadata.id,
                "filename": metadata.filename,
                "title": metadata.title,
                "responsible": metadata.responsible,
                "frequency": metadata.frequency,
                "permissions": metadata.permissions,
                "tags": metadata.tags or [],
                "created_at": metadata.created_at.isoformat(),
                "updated_at": metadata.updated_at.isoformat()
            }
            for metadata in metadata_list
        ]

    async def get_filter_options(self) -> Dict[str, List[str]]:
        """Obtiene opciones para filtros del admin"""
        
        # Responsables únicos
        responsibles_query = select(distinct(FileMetadata.responsible)).where(
            FileMetadata.responsible.isnot(None)
        )
        responsibles_result = await self.db.execute(responsibles_query)
        responsibles = [r[0] for r in responsibles_result.fetchall() if r[0]]
        
        # Permisos únicos
        permissions_query = select(distinct(FileMetadata.permissions)).where(
            FileMetadata.permissions.isnot(None)
        )
        permissions_result = await self.db.execute(permissions_query)
        permissions = [p[0] for p in permissions_result.fetchall() if p[0]]
        
        return {
            "responsibles": sorted(responsibles),
            "permissions": sorted(permissions)
        }

    async def get_detailed_file_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """Obtiene información detallada de un archivo para edición"""
        
        metadata = await self.metadata_service.get_metadata_by_filename(filename)
        if not metadata:
            return None
            
        # Obtener historial reciente
        history = await self.metadata_service.get_metadata_history(filename)
        
        return {
            "id": metadata.id,
            "filename": metadata.filename,
            "title": metadata.title,
            "description": metadata.description,
            "responsible": metadata.responsible,
            "frequency": metadata.frequency,
            "permissions": metadata.permissions,
            "tags": metadata.tags or [],
            "file_size_mb": float(metadata.file_size_mb) if metadata.file_size_mb else None,
            "row_count": metadata.row_count,
            "column_count": metadata.column_count,
            "created_at": metadata.created_at.isoformat(),
            "updated_at": metadata.updated_at.isoformat(),
            "history": [
                {
                    "field_changed": h.field_changed,
                    "old_value": h.old_value,
                    "new_value": h.new_value,
                    "changed_by": h.changed_by,
                    "changed_at": h.changed_at.isoformat()
                }
                for h in history[:10]  # Últimos 10 cambios
            ]
        }