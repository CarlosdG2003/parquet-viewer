from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct, update
from pathlib import Path
from datetime import datetime, timedelta
import os

from models.database_models import FileMetadata, MetadataHistory, ColumnMetadata
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

    # === NUEVOS MÉTODOS PARA GESTIÓN DE COLUMNAS ===

    async def get_file_columns_admin(self, filename: str) -> Dict[str, Any]:
        """Obtiene información de columnas para administración"""
        try:
            # Primero obtener esquema técnico del archivo
            from core.database import db_manager
            duckdb_conn = db_manager.get_duckdb_connection()
            
            file_path = settings.PARQUET_DIR / filename
            if not file_path.exists():
                raise FileNotFoundError(f"Archivo {filename} no encontrado")
            
            # Obtener esquema actual del archivo
            schema_query = f'DESCRIBE SELECT * FROM parquet_scan("{file_path}")'
            schema_df = duckdb_conn.execute(schema_query).fetchdf()
            
            # Obtener metadatos existentes de columnas (si existen)
            existing_metadata_query = select(ColumnMetadata).where(
                ColumnMetadata.filename == filename
            ).order_by(ColumnMetadata.sort_order, ColumnMetadata.original_column_name)
            
            existing_result = await self.db.execute(existing_metadata_query)
            existing_metadata = {
                meta.original_column_name: meta 
                for meta in existing_result.scalars().all()
            }
            
            # Combinar información técnica con metadatos
            columns_info = []
            for index, row in schema_df.iterrows():
                col_name = row['column_name']
                col_type = row['column_type']
                
                # Obtener metadatos existentes o crear valores por defecto
                metadata = existing_metadata.get(col_name)
                
                columns_info.append({
                    "original_name": col_name,
                    "display_name": metadata.display_name if metadata else col_name,
                    "description": metadata.description if metadata else "",
                    "data_type": col_type,
                    "is_visible": metadata.is_visible if metadata else True,
                    "sort_order": metadata.sort_order if metadata else index,
                    "has_metadata": metadata is not None,
                    "metadata_id": metadata.id if metadata else None
                })
            
            return {
                "filename": filename,
                "total_columns": len(columns_info),
                "columns": sorted(columns_info, key=lambda x: x["sort_order"]),
                "last_sync": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Error obteniendo columnas de {filename}: {str(e)}")

    async def update_column_metadata(
        self, 
        filename: str, 
        original_column_name: str, 
        updates: Dict[str, Any],
        changed_by: str = "admin"
    ) -> Dict[str, Any]:
        """Actualiza o crea metadatos de una columna específica"""
        try:
            # Buscar metadatos existentes
            existing_query = select(ColumnMetadata).where(
                ColumnMetadata.filename == filename,
                ColumnMetadata.original_column_name == original_column_name
            )
            existing_result = await self.db.execute(existing_query)
            existing = existing_result.scalar_one_or_none()
            
            if existing:
                # Actualizar existente
                for field, value in updates.items():
                    if hasattr(existing, field):
                        setattr(existing, field, value)
                existing.updated_at = func.now()
                
                await self.db.commit()
                await self.db.refresh(existing)
                
                return {
                    "action": "updated",
                    "column": original_column_name,
                    "metadata_id": existing.id
                }
            else:
                # Crear nuevo
                new_metadata = ColumnMetadata(
                    filename=filename,
                    original_column_name=original_column_name,
                    display_name=updates.get("display_name", original_column_name),
                    description=updates.get("description"),
                    is_visible=updates.get("is_visible", True),
                    sort_order=updates.get("sort_order", 0),
                    data_type=updates.get("data_type")
                )
                
                self.db.add(new_metadata)
                await self.db.commit()
                await self.db.refresh(new_metadata)
                
                return {
                    "action": "created",
                    "column": original_column_name,
                    "metadata_id": new_metadata.id
                }
                
        except Exception as e:
            await self.db.rollback()
            raise Exception(f"Error actualizando metadatos de columna: {str(e)}")

    async def bulk_update_columns(
        self, 
        filename: str, 
        columns_updates: List[Dict[str, Any]], 
        changed_by: str = "admin"
    ) -> Dict[str, Any]:
        """Actualiza metadatos de múltiples columnas de una vez"""
        results = {"updated": 0, "created": 0, "errors": []}
        
        for update in columns_updates:
            try:
                original_name = update.pop("original_column_name")
                result = await self.update_column_metadata(
                    filename, original_name, update, changed_by
                )
                
                if result["action"] == "updated":
                    results["updated"] += 1
                else:
                    results["created"] += 1
                    
            except Exception as e:
                results["errors"].append({
                    "column": update.get("original_column_name", "unknown"),
                    "error": str(e)
                })
        
        return results

    async def sync_file_columns_metadata(self, filename: str) -> Dict[str, Any]:
        """Sincroniza metadatos de columnas con el esquema actual del archivo"""
        try:
            from core.database import db_manager
            
            duckdb_conn = db_manager.get_duckdb_connection()
            file_path = settings.PARQUET_DIR / filename
            
            if not file_path.exists():
                raise FileNotFoundError(f"Archivo {filename} no encontrado")
            
            # Obtener columnas actuales del archivo
            schema_query = f'DESCRIBE SELECT * FROM parquet_scan("{file_path}")'
            schema_df = duckdb_conn.execute(schema_query).fetchdf()
            current_columns = set(schema_df['column_name'].tolist())
            
            # Obtener metadatos existentes
            existing_query = select(ColumnMetadata).where(
                ColumnMetadata.filename == filename
            )
            existing_result = await self.db.execute(existing_query)
            existing_metadata = existing_result.scalars().all()
            existing_columns = {meta.original_column_name for meta in existing_metadata}
            
            results = {"created": 0, "updated": 0, "hidden": 0}
            
            # Crear metadatos para columnas nuevas
            new_columns = current_columns - existing_columns
            for index, (_, row) in enumerate(schema_df.iterrows()):
                col_name = row['column_name']
                if col_name in new_columns:
                    new_metadata = ColumnMetadata(
                        filename=filename,
                        original_column_name=col_name,
                        display_name=col_name,
                        data_type=row['column_type'],
                        is_visible=True,
                        sort_order=len(existing_columns) + index
                    )
                    self.db.add(new_metadata)
                    results["created"] += 1
            
            # Marcar como ocultas las columnas que ya no existen
            removed_columns = existing_columns - current_columns
            if removed_columns:
                await self.db.execute(
                    update(ColumnMetadata)
                    .where(
                        ColumnMetadata.filename == filename,
                        ColumnMetadata.original_column_name.in_(removed_columns)
                    )
                    .values(is_visible=False)
                )
                results["hidden"] = len(removed_columns)
            
            await self.db.commit()
            
            return {
                "filename": filename,
                "sync_results": results,
                "total_current_columns": len(current_columns),
                "synced_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            await self.db.rollback()
            raise Exception(f"Error sincronizando columnas: {str(e)}")

    async def get_columns_display_schema(self, filename: str) -> Dict[str, Any]:
        """Obtiene esquema de columnas con nombres personalizados para mostrar en tabla"""
        try:
            query = select(ColumnMetadata).where(
                ColumnMetadata.filename == filename,
                ColumnMetadata.is_visible == True
            ).order_by(ColumnMetadata.sort_order, ColumnMetadata.original_column_name)
            
            result = await self.db.execute(query)
            metadata_list = result.scalars().all()
            
            if not metadata_list:
                # Si no hay metadatos, obtener esquema básico del archivo
                columns_info = await self.get_file_columns_admin(filename)
                return {
                    "filename": filename,
                    "has_custom_names": False,
                    "columns": [
                        {
                            "original_name": col["original_name"],
                            "display_name": col["original_name"],
                            "description": None,
                            "data_type": col["data_type"]
                        }
                        for col in columns_info["columns"]
                        if col["is_visible"]
                    ]
                }
            
            return {
                "filename": filename,
                "has_custom_names": True,
                "columns": [
                    {
                        "original_name": meta.original_column_name,
                        "display_name": meta.display_name or meta.original_column_name,
                        "description": meta.description,
                        "data_type": meta.data_type
                    }
                    for meta in metadata_list
                ]
            }
            
        except Exception as e:
            raise Exception(f"Error obteniendo esquema de visualización: {str(e)}")

    async def reset_column_metadata(self, filename: str, original_column_name: str) -> Dict[str, Any]:
        """Resetea metadatos de una columna a valores por defecto"""
        try:
            query = select(ColumnMetadata).where(
                ColumnMetadata.filename == filename,
                ColumnMetadata.original_column_name == original_column_name
            )
            result = await self.db.execute(query)
            metadata = result.scalar_one_or_none()
            
            if metadata:
                metadata.display_name = original_column_name
                metadata.description = None
                metadata.is_visible = True
                metadata.updated_at = func.now()
                
                await self.db.commit()
                
                return {
                    "action": "reset",
                    "column": original_column_name,
                    "message": f"Metadatos de '{original_column_name}' reseteados"
                }
            else:
                return {
                    "action": "no_change",
                    "column": original_column_name,
                    "message": f"No hay metadatos que resetear para '{original_column_name}'"
                }
                
        except Exception as e:
            await self.db.rollback()
            raise Exception(f"Error reseteando metadatos: {str(e)}")