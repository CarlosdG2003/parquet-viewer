"""
Servicio para gestionar metadatos de Power BI
Extrae, almacena y gestiona metadatos específicos para exportación a Power BI
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import pyarrow.parquet as pq
import json

from models.database_models import (
    PowerBIColumnMetadata,
    PowerBITableMetadata,
    PowerBIRelationship,
    PowerBIMeasure,
    PowerBIColumnMetadataCreate,
    PowerBITableMetadataCreate,
    PowerBIRelationshipCreate
)

class PowerBIMetadataService:
    """Servicio para gestionar metadatos específicos de Power BI"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    # ==================== EXTRACCIÓN DE METADATOS DESDE PARQUET ====================
    
    async def extract_and_save_from_parquet(self, filename: str, parquet_path: str) -> Dict[str, Any]:
        """
        Extrae metadatos de un archivo Parquet y los guarda en la base de datos
        Busca metadatos incrustados o genera automáticamente
        """
        # Leer archivo Parquet
        table = pq.read_table(parquet_path)
        schema_metadata = table.schema.metadata or {}
        
        # Extraer o generar metadatos de tabla
        table_metadata = self._extract_table_metadata(filename, schema_metadata)
        await self.save_table_metadata(table_metadata)
        
        # Extraer o generar metadatos de columnas
        columns_metadata = self._extract_columns_metadata(filename, table, schema_metadata)
        for col_meta in columns_metadata:
            await self.save_column_metadata(col_meta)
        
        # Extraer relaciones si existen
        relationships = self._extract_relationships(schema_metadata)
        
        return {
            "table": table_metadata,
            "columns": columns_metadata,
            "relationships": relationships,
            "columns_count": len(columns_metadata)
        }
    
    def _extract_table_metadata(self, filename: str, schema_metadata: dict) -> PowerBITableMetadataCreate:
        """Extrae metadatos de tabla desde Parquet o genera por defecto"""
        # Intentar extraer desde metadatos incrustados
        table_name = schema_metadata.get(b'powerbi_table_name', filename.replace('.parquet', '')).decode() if isinstance(schema_metadata.get(b'powerbi_table_name'), bytes) else filename.replace('.parquet', '')
        friendly_name = schema_metadata.get(b'powerbi_friendly_name', table_name).decode() if isinstance(schema_metadata.get(b'powerbi_friendly_name'), bytes) else table_name
        description = schema_metadata.get(b'powerbi_description', '').decode() if isinstance(schema_metadata.get(b'powerbi_description'), bytes) else ''
        
        return PowerBITableMetadataCreate(
            filename=filename,
            table_name=table_name,
            friendly_name=friendly_name,
            description=description,
            is_hidden=False
        )
    
    def _extract_columns_metadata(self, filename: str, table, schema_metadata: dict) -> List[PowerBIColumnMetadataCreate]:
        """Extrae metadatos de columnas desde Parquet o genera automáticamente"""
        columns_metadata = []
        
        # Intentar extraer metadatos embebidos
        embedded_columns = None
        if b'powerbi_columns' in schema_metadata:
            try:
                embedded_columns = json.loads(schema_metadata[b'powerbi_columns'].decode())
            except:
                pass
        
        for field in table.schema:
            col_name = field.name
            
            # Buscar metadatos embebidos para esta columna
            embedded = embedded_columns.get(col_name, {}) if embedded_columns else {}
            
            # Determinar tipo de datos
            data_type = self._map_arrow_type_to_powerbi(field.type)
            
            col_meta = PowerBIColumnMetadataCreate(
                filename=filename,
                original_column_name=col_name,
                friendly_name=embedded.get('friendly_name', col_name.replace('_', ' ').title()),
                data_type=data_type,
                format_string=embedded.get('format', self._get_default_format(data_type)),
                description=embedded.get('description', ''),
                is_hidden=embedded.get('is_hidden', False),
                is_key=embedded.get('is_key', 'id' in col_name.lower()),
                aggregation_function=embedded.get('aggregation', self._get_default_aggregation(data_type))
            )
            columns_metadata.append(col_meta)
        
        return columns_metadata
    
    def _extract_relationships(self, schema_metadata: dict) -> List[Dict[str, Any]]:
        """Extrae relaciones desde metadatos del Parquet"""
        if b'powerbi_relationships' not in schema_metadata:
            return []
        
        try:
            relationships = json.loads(schema_metadata[b'powerbi_relationships'].decode())
            return relationships
        except:
            return []
    
    def _map_arrow_type_to_powerbi(self, arrow_type) -> str:
        """Mapea tipos Arrow a tipos Power BI"""
        type_str = str(arrow_type).lower()
        
        if 'string' in type_str or 'utf8' in type_str:
            return 'String'
        elif 'int' in type_str:
            return 'Int64'
        elif 'float' in type_str or 'double' in type_str:
            return 'Double'
        elif 'bool' in type_str:
            return 'Boolean'
        elif 'date' in type_str or 'timestamp' in type_str:
            return 'DateTime'
        elif 'decimal' in type_str:
            return 'Decimal'
        else:
            return 'String'
    
    def _get_default_format(self, data_type: str) -> Optional[str]:
        """Obtiene formato por defecto según tipo de dato"""
        formats = {
            'Double': '#,##0.00',
            'Decimal': '#,##0.00',
            'DateTime': 'dd/mm/yyyy',
            'Int64': '#,##0'
        }
        return formats.get(data_type)
    
    def _get_default_aggregation(self, data_type: str) -> Optional[str]:
        """Obtiene función de agregación por defecto"""
        if data_type in ['Double', 'Decimal', 'Int64']:
            return 'SUM'
        return None
    
    # ==================== GESTIÓN DE COLUMNAS ====================
    
    async def save_column_metadata(self, metadata: PowerBIColumnMetadataCreate):
        """Guarda o actualiza metadatos de columna"""
        # Verificar si existe
        query = select(PowerBIColumnMetadata).where(
            PowerBIColumnMetadata.filename == metadata.filename,
            PowerBIColumnMetadata.original_column_name == metadata.original_column_name
        )
        result = await self.db.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Actualizar
            for key, value in metadata.dict(exclude={'filename', 'original_column_name'}).items():
                setattr(existing, key, value)
        else:
            # Crear nuevo
            new_col = PowerBIColumnMetadata(**metadata.dict())
            self.db.add(new_col)
        
        await self.db.commit()
    
    async def get_columns_by_filename(self, filename: str) -> List[PowerBIColumnMetadata]:
        """Obtiene todos los metadatos de columnas de un archivo"""
        query = select(PowerBIColumnMetadata).where(
            PowerBIColumnMetadata.filename == filename
        ).order_by(PowerBIColumnMetadata.original_column_name)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def update_column_metadata(self, filename: str, column_name: str, updates: Dict[str, Any]):
        """Actualiza metadatos específicos de una columna"""
        query = select(PowerBIColumnMetadata).where(
            PowerBIColumnMetadata.filename == filename,
            PowerBIColumnMetadata.original_column_name == column_name
        )
        result = await self.db.execute(query)
        column = result.scalar_one_or_none()
        
        if column:
            for key, value in updates.items():
                if hasattr(column, key):
                    setattr(column, key, value)
            await self.db.commit()
            return column
        return None
    
    # ==================== GESTIÓN DE TABLAS ====================
    
    async def save_table_metadata(self, metadata: PowerBITableMetadataCreate):
        """Guarda o actualiza metadatos de tabla"""
        query = select(PowerBITableMetadata).where(
            PowerBITableMetadata.filename == metadata.filename
        )
        result = await self.db.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            for key, value in metadata.dict(exclude={'filename'}).items():
                setattr(existing, key, value)
        else:
            new_table = PowerBITableMetadata(**metadata.dict())
            self.db.add(new_table)
        
        await self.db.commit()
    
    async def get_table_metadata(self, filename: str) -> Optional[PowerBITableMetadata]:
        """Obtiene metadatos de una tabla"""
        query = select(PowerBITableMetadata).where(
            PowerBITableMetadata.filename == filename
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all_tables(self) -> List[PowerBITableMetadata]:
        """Obtiene todas las tablas con metadatos Power BI"""
        query = select(PowerBITableMetadata).order_by(PowerBITableMetadata.friendly_name)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    # ==================== GESTIÓN DE RELACIONES ====================
    
    async def create_relationship(self, relationship: PowerBIRelationshipCreate) -> PowerBIRelationship:
        """Crea una relación entre dos tablas"""
        # Obtener IDs de las tablas
        from_table = await self.get_table_metadata(relationship.from_table_filename)
        to_table = await self.get_table_metadata(relationship.to_table_filename)
        
        if not from_table or not to_table:
            raise ValueError("Una o ambas tablas no existen")
        
        new_rel = PowerBIRelationship(
            project_name=relationship.project_name,
            from_table_id=from_table.id,
            to_table_id=to_table.id,
            from_column=relationship.from_column,
            to_column=relationship.to_column,
            cardinality=relationship.cardinality,
            cross_filter_direction=relationship.cross_filter_direction,
            is_active=relationship.is_active,
            description=relationship.description,
            created_by=relationship.created_by
        )
        
        self.db.add(new_rel)
        await self.db.commit()
        await self.db.refresh(new_rel)
        return new_rel
    
    async def get_relationships_by_project(self, project_name: str) -> List[PowerBIRelationship]:
        """Obtiene todas las relaciones de un proyecto"""
        query = select(PowerBIRelationship).where(
            PowerBIRelationship.project_name == project_name,
            PowerBIRelationship.is_active == True
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_all_relationships(self) -> List[PowerBIRelationship]:
        """Obtiene todas las relaciones activas"""
        query = select(PowerBIRelationship).where(
            PowerBIRelationship.is_active == True
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def delete_relationship(self, relationship_id: int):
        """Elimina una relación"""
        query = delete(PowerBIRelationship).where(PowerBIRelationship.id == relationship_id)
        await self.db.execute(query)
        await self.db.commit()
    
    # ==================== PREPARACIÓN PARA EXPORTACIÓN ====================
    
    async def get_export_data(self, filenames: List[str]) -> Dict[str, Any]:
        """
        Obtiene todos los metadatos necesarios para exportar a Power BI
        """
        tables = []
        all_columns = {}
        
        for filename in filenames:
            table = await self.get_table_metadata(filename)
            if table:
                columns = await self.get_columns_by_filename(filename)
                tables.append(table)
                all_columns[filename] = columns
        
        # Obtener relaciones entre estas tablas
        table_ids = [t.id for t in tables]
        query = select(PowerBIRelationship).where(
            PowerBIRelationship.from_table_id.in_(table_ids),
            PowerBIRelationship.to_table_id.in_(table_ids),
            PowerBIRelationship.is_active == True
        )
        result = await self.db.execute(query)
        relationships = result.scalars().all()
        
        return {
            "tables": tables,
            "columns": all_columns,
            "relationships": relationships
        }
    
    # ==================== LIMPIEZA ====================
    
    async def delete_metadata_by_filename(self, filename: str):
        """Elimina todos los metadatos Power BI de un archivo"""
        # Eliminar columnas
        await self.db.execute(
            delete(PowerBIColumnMetadata).where(PowerBIColumnMetadata.filename == filename)
        )
        
        # Eliminar tabla (las relaciones se borran en cascada)
        await self.db.execute(
            delete(PowerBITableMetadata).where(PowerBITableMetadata.filename == filename)
        )
        
        await self.db.commit()