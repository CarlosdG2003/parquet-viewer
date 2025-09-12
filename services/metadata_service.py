from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
from models.database_models import FileMetadata, MetadataHistory, FileMetadataCreate, FileMetadataUpdate
from datetime import datetime

class MetadataService:
    """Servicio para gestionar metadatos en PostgreSQL"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_all_metadata(self) -> List[FileMetadata]:
        """Obtiene todos los metadatos de archivos"""
        query = select(FileMetadata).order_by(FileMetadata.updated_at.desc())
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_metadata_by_filename(self, filename: str) -> Optional[FileMetadata]:
        """Obtiene metadatos de un archivo específico"""
        query = select(FileMetadata).where(FileMetadata.filename == filename)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_metadata(self, metadata: FileMetadataCreate) -> FileMetadata:
        """Crea nuevos metadatos para un archivo"""
        db_metadata = FileMetadata(**metadata.dict())
        self.db.add(db_metadata)
        
        try:
            await self.db.commit()
            await self.db.refresh(db_metadata)
            return db_metadata
        except IntegrityError:
            await self.db.rollback()
            raise ValueError(f"Ya existen metadatos para el archivo {metadata.filename}")

    async def update_metadata(
        self, 
        filename: str, 
        metadata: FileMetadataUpdate, 
        changed_by: str = "system"
    ) -> Optional[FileMetadata]:
        """Actualiza metadatos de un archivo y registra el historial"""
        
        # Obtener metadatos actuales
        current = await self.get_metadata_by_filename(filename)
        if not current:
            return None

        # Preparar datos de actualización (solo campos no nulos)
        update_data = {k: v for k, v in metadata.dict().items() if v is not None}
        
        if not update_data:
            return current

        # Registrar cambios en el historial
        await self._record_history_changes(current, update_data, changed_by)

        # Actualizar los datos
        query = update(FileMetadata).where(
            FileMetadata.filename == filename
        ).values(**update_data, updated_at=datetime.utcnow())
        
        await self.db.execute(query)
        await self.db.commit()

        # Obtener los datos actualizados
        return await self.get_metadata_by_filename(filename)

    async def delete_metadata(self, filename: str) -> bool:
        """Elimina metadatos de un archivo"""
        query = delete(FileMetadata).where(FileMetadata.filename == filename)
        result = await self.db.execute(query)
        await self.db.commit()
        return result.rowcount > 0

    async def update_file_stats(
        self, 
        filename: str, 
        file_size_mb: float, 
        row_count: int, 
        column_count: int
    ) -> Optional[FileMetadata]:
        """Actualiza estadísticas técnicas del archivo"""
        query = update(FileMetadata).where(
            FileMetadata.filename == filename
        ).values(
            file_size_mb=file_size_mb,
            row_count=row_count,
            column_count=column_count,
            updated_at=datetime.utcnow()
        )
        
        result = await self.db.execute(query)
        await self.db.commit()
        
        if result.rowcount > 0:
            return await self.get_metadata_by_filename(filename)
        return None

    async def search_metadata(
        self, 
        search_term: str = None,
        responsible: str = None,
        permissions: str = None,
        tags: List[str] = None
    ) -> List[FileMetadata]:
        """Busca metadatos con filtros"""
        query = select(FileMetadata)

        if search_term:
            search_pattern = f"%{search_term.lower()}%"
            query = query.where(
                FileMetadata.title.ilike(search_pattern) |
                FileMetadata.description.ilike(search_pattern) |
                FileMetadata.filename.ilike(search_pattern)
            )

        if responsible:
            query = query.where(FileMetadata.responsible == responsible)

        if permissions:
            query = query.where(FileMetadata.permissions == permissions)

        if tags:
            # Buscar archivos que contengan cualquiera de los tags
            query = query.where(FileMetadata.tags.overlap(tags))

        query = query.order_by(FileMetadata.updated_at.desc())
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_metadata_history(self, filename: str) -> List[MetadataHistory]:
        """Obtiene el historial de cambios de un archivo"""
        # Primero obtener el ID del archivo
        file_query = select(FileMetadata.id).where(FileMetadata.filename == filename)
        file_result = await self.db.execute(file_query)
        file_id = file_result.scalar_one_or_none()
        
        if not file_id:
            return []

        # Obtener historial
        query = select(MetadataHistory).where(
            MetadataHistory.file_id == file_id
        ).order_by(MetadataHistory.changed_at.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_unique_responsibles(self) -> List[str]:
        """Obtiene lista de responsables únicos"""
        query = select(FileMetadata.responsible).distinct().where(
            FileMetadata.responsible.isnot(None)
        )
        result = await self.db.execute(query)
        return [r[0] for r in result.fetchall() if r[0]]

    async def get_unique_tags(self) -> List[str]:
        """Obtiene lista de tags únicos"""
        query = select(FileMetadata.tags).where(
            FileMetadata.tags.isnot(None)
        )
        result = await self.db.execute(query)
        
        # Aplanar arrays de tags
        all_tags = set()
        for tags_array in result.scalars():
            if tags_array:
                all_tags.update(tags_array)
        
        return sorted(list(all_tags))

    async def _record_history_changes(
        self, 
        current_metadata: FileMetadata, 
        update_data: Dict[str, Any], 
        changed_by: str
    ):
        """Registra cambios en el historial"""
        for field, new_value in update_data.items():
            if field == "updated_at":
                continue
                
            old_value = getattr(current_metadata, field)
            
            # Solo registrar si hay cambio real
            if old_value != new_value:
                history = MetadataHistory(
                    file_id=current_metadata.id,
                    field_changed=field,
                    old_value=str(old_value) if old_value is not None else None,
                    new_value=str(new_value) if new_value is not None else None,
                    changed_by=changed_by
                )
                self.db.add(history)