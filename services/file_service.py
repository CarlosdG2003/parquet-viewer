from typing import List, Optional, Dict, Any
from pathlib import Path
import duckdb
from datetime import datetime
from models.parquet_file import ParquetFile
from models.database_models import CombinedFileInfo, FileMetadata
from services.metadata_service import MetadataService
from config import settings
import pandas as pd
import numpy as np

class FileService:
    """Servicio que integra datos técnicos (DuckDB) con metadatos (PostgreSQL)"""
    
    def __init__(self, duckdb_conn: duckdb.DuckDBPyConnection, metadata_service: MetadataService):
        self.duckdb_conn = duckdb_conn
        self.metadata_service = metadata_service

    async def get_all_files_combined(self) -> List[CombinedFileInfo]:
        """Obtiene todos los archivos combinando datos técnicos + metadatos"""
        combined_files = []
        
        # 1. Obtener archivos físicos del directorio
        physical_files = {}
        for file_path in settings.PARQUET_DIR.glob("*.parquet"):
            parquet_file = ParquetFile(file_path)
            file_info = parquet_file.get_info()
            physical_files[file_path.name] = file_info
        
        # 2. Obtener todos los metadatos de PostgreSQL
        metadata_list = await self.metadata_service.get_all_metadata()
        metadata_dict = {meta.filename: meta for meta in metadata_list}
        
        # 3. Combinar datos técnicos con metadatos
        all_filenames = set(physical_files.keys()) | set(metadata_dict.keys())
        
        for filename in all_filenames:
            # Datos técnicos (pueden no existir si el archivo se eliminó físicamente)
            technical_data = physical_files.get(filename, {
                "name": filename,
                "size_bytes": 0,
                "size_mb": 0.0,
                "modified": "",
                "row_count": None,
                "column_count": None,
                "columns": []
            })
            
            # Metadatos (pueden no existir si es un archivo nuevo)
            metadata = metadata_dict.get(filename)
            
            # Crear objeto combinado
            combined = CombinedFileInfo(
                # Datos técnicos
                name=filename,
                size_bytes=technical_data.get("size_bytes", 0),
                size_mb=technical_data.get("size_mb", 0.0),
                modified=technical_data.get("modified", ""),
                row_count=technical_data.get("row_count"),
                column_count=technical_data.get("column_count"),
                columns=technical_data.get("columns", []),
                
                # Metadatos del negocio
                id=metadata.id if metadata else None,
                title=metadata.title if metadata else None,
                description=metadata.description if metadata else None,
                responsible=metadata.responsible if metadata else None,
                frequency=metadata.frequency if metadata else None,
                permissions=metadata.permissions if metadata else "public",
                tags=metadata.tags if metadata else [],
                created_at=metadata.created_at if metadata else None,
                updated_at=metadata.updated_at if metadata else None
            )
            
            combined_files.append(combined)
        
        return sorted(combined_files, key=lambda x: x.modified or "", reverse=True)

    async def get_file_combined(self, filename: str) -> Optional[CombinedFileInfo]:
        """Obtiene información combinada de un archivo específico"""
        # Datos técnicos
        file_path = settings.PARQUET_DIR / filename
        technical_data = {}
        
        if file_path.exists():
            parquet_file = ParquetFile(file_path)
            technical_data = parquet_file.get_info()
        
        # Metadatos
        metadata = await self.metadata_service.get_metadata_by_filename(filename)
        
        if not technical_data and not metadata:
            return None
        
        return CombinedFileInfo(
            # Datos técnicos
            name=filename,
            size_bytes=technical_data.get("size_bytes", 0),
            size_mb=technical_data.get("size_mb", 0.0),
            modified=technical_data.get("modified", ""),
            row_count=technical_data.get("row_count"),
            column_count=technical_data.get("column_count"),
            columns=technical_data.get("columns", []),
            
            # Metadatos del negocio
            id=metadata.id if metadata else None,
            title=metadata.title if metadata else None,
            description=metadata.description if metadata else None,
            responsible=metadata.responsible if metadata else None,
            frequency=metadata.frequency if metadata else None,
            permissions=metadata.permissions if metadata else "public",
            tags=metadata.tags if metadata else [],
            created_at=metadata.created_at if metadata else None,
            updated_at=metadata.updated_at if metadata else None
        )

    async def sync_file_stats(self, filename: str) -> bool:
        """Sincroniza estadísticas técnicas del archivo con los metadatos"""
        file_path = settings.PARQUET_DIR / filename
        
        if not file_path.exists():
            return False
        
        try:
            parquet_file = ParquetFile(file_path)
            file_info = parquet_file.get_info()
            
            # Actualizar estadísticas en PostgreSQL
            await self.metadata_service.update_file_stats(
                filename=filename,
                file_size_mb=file_info["size_mb"],
                row_count=file_info["row_count"],
                column_count=file_info["column_count"]
            )
            
            return True
        except Exception as e:
            print(f"Error syncing stats for {filename}: {e}")
            return False

    async def search_files_combined(
        self, 
        search_term: str = None,
        responsible: str = None,
        permissions: str = None,
        tags: List[str] = None
    ) -> List[CombinedFileInfo]:
        """Busca archivos combinando filtros técnicos y de metadatos"""
        
        # Buscar en metadatos primero
        matching_metadata = await self.metadata_service.search_metadata(
            search_term=search_term,
            responsible=responsible,
            permissions=permissions,
            tags=tags
        )
        
        # Obtener archivos físicos
        physical_files = {}
        for file_path in settings.PARQUET_DIR.glob("*.parquet"):
            parquet_file = ParquetFile(file_path)
            file_info = parquet_file.get_info()
            physical_files[file_path.name] = file_info
        
        # Si hay término de búsqueda, también buscar en archivos físicos
        if search_term:
            search_term_lower = search_term.lower()
            for filename, file_info in physical_files.items():
                if search_term_lower in filename.lower():
                    # Verificar si ya está en los metadatos encontrados
                    if not any(meta.filename == filename for meta in matching_metadata):
                        # Crear metadata ficticia para archivos físicos sin metadatos
                        matching_metadata.append(type('obj', (object,), {
                            'filename': filename,
                            'title': None,
                            'description': None,
                            'responsible': None,
                            'frequency': None,
                            'permissions': 'public',
                            'tags': [],
                            'id': None,
                            'created_at': None,
                            'updated_at': None
                        })())
        
        # Combinar resultados
        combined_results = []
        for metadata in matching_metadata:
            technical_data = physical_files.get(metadata.filename, {})
            
            combined = CombinedFileInfo(
                name=metadata.filename,
                size_bytes=technical_data.get("size_bytes", 0),
                size_mb=technical_data.get("size_mb", 0.0),
                modified=technical_data.get("modified", ""),
                row_count=technical_data.get("row_count"),
                column_count=technical_data.get("column_count"),
                columns=technical_data.get("columns", []),
                
                id=getattr(metadata, 'id', None),
                title=getattr(metadata, 'title', None),
                description=getattr(metadata, 'description', None),
                responsible=getattr(metadata, 'responsible', None),
                frequency=getattr(metadata, 'frequency', None),
                permissions=getattr(metadata, 'permissions', 'public'),
                tags=getattr(metadata, 'tags', []),
                created_at=getattr(metadata, 'created_at', None),
                updated_at=getattr(metadata, 'updated_at', None)
            )
            
            combined_results.append(combined)
        
        return combined_results

    async def get_file_data(
        self, 
        filename: str, 
        page: int = 1, 
        page_size: int = 50,
        columns: List[str] = None
    ) -> Dict[str, Any]:
        """Obtiene datos paginados del archivo usando DuckDB"""
        file_path = settings.PARQUET_DIR / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"File {filename} not found")
        
        parquet_file = ParquetFile(file_path)
        return parquet_file.get_data(page, page_size, columns)

    async def get_file_schema(self, filename: str) -> List[Dict[str, Any]]:
        """Obtiene el esquema del archivo usando DuckDB"""
        file_path = settings.PARQUET_DIR / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"File {filename} not found")
        
        parquet_file = ParquetFile(file_path)
        return parquet_file.get_schema()

    async def auto_sync_all_files(self) -> Dict[str, bool]:
        """Sincroniza estadísticas de todos los archivos físicos con metadatos"""
        results = {}
        
        for file_path in settings.PARQUET_DIR.glob("*.parquet"):
            filename = file_path.name
            success = await self.sync_file_stats(filename)
            results[filename] = success
        
        return results
    
    async def get_file_data_with_display_names(
        self, 
        filename: str, 
        page: int = 1, 
        page_size: int = 50,
        columns: List[str] = None,
        search_term: str = None,
        sort_column: str = None,
        sort_order: str = "asc"
    ) -> Dict[str, Any]:
        file_path = settings.PARQUET_DIR / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"File {filename} not found")
        
        try:
            # Obtener metadatos de columnas si existen
            from services.admin_service import AdminService
            admin_service = AdminService(self.metadata_service.db)
            
            try:
                display_schema = await admin_service.get_columns_display_schema(filename)
                has_custom_names = display_schema.get("has_custom_names", False)
                columns_mapping = {
                    col["original_name"]: col for col in display_schema.get("columns", [])
                }
            except:
                # Si no hay metadatos de columnas, usar esquema original
                has_custom_names = False
                columns_mapping = {}
            
            # Construir query base
            offset = (page - 1) * page_size
            
            # Determinar columnas a seleccionar
            if columns and has_custom_names:
                # Mapear nombres de visualización a nombres originales
                original_columns = []
                display_columns = []
                for col in columns:
                    found = False
                    for orig_name, col_info in columns_mapping.items():
                        if col_info["display_name"] == col:
                            original_columns.append(f'"{orig_name}"')
                            display_columns.append(col)
                            found = True
                            break
                    if not found:
                        original_columns.append(f'"{col}"')
                        display_columns.append(col)
                
                columns_str = ", ".join(original_columns)
            else:
                # Si no hay columnas específicas, obtener todas las visibles
                if has_custom_names:
                    visible_cols = [
                        f'"{col_info["original_name"]}" AS "{col_info["display_name"]}"'
                        for col_info in columns_mapping.values()
                    ]
                    columns_str = ", ".join(visible_cols) if visible_cols else "*"
                    display_columns = [col_info["display_name"] for col_info in columns_mapping.values()]
                else:
                    columns_str = "*"
                    display_columns = None
            
            # Query base
            base_query = f'SELECT {columns_str} FROM parquet_scan("{file_path}")'
            
            # Agregar filtro de búsqueda
            where_clause = ""
            if search_term:
                search_conditions = []
                # Obtener todas las columnas para búsqueda
                schema_query = f'DESCRIBE SELECT * FROM parquet_scan("{file_path}")'
                schema_df = self.duckdb_conn.execute(schema_query).fetchdf()
                
                for _, row in schema_df.iterrows():
                    col_name = row['column_name']
                    col_type = row['column_type'].lower()
                    
                    # Solo buscar en columnas de texto y convertir números a string
                    if 'varchar' in col_type or 'string' in col_type:
                        search_conditions.append(f'LOWER(CAST("{col_name}" AS VARCHAR)) LIKE LOWER(\'%{search_term}%\')')
                    elif any(t in col_type for t in ['int', 'float', 'double', 'decimal']):
                        search_conditions.append(f'CAST("{col_name}" AS VARCHAR) LIKE \'%{search_term}%\'')
                
                if search_conditions:
                    where_clause = f" WHERE ({' OR '.join(search_conditions)})"
            
            # Agregar ordenamiento
            order_clause = ""
            if sort_column and sort_order:
                # Si hay nombres personalizados, usar el nombre original
                actual_sort_column = sort_column
                if has_custom_names:
                    for orig_name, col_info in columns_mapping.items():
                        if col_info["display_name"] == sort_column:
                            actual_sort_column = orig_name
                            break
                
                order_clause = f' ORDER BY "{actual_sort_column}" {sort_order.upper()}'
            
            # Query con paginación
            data_query = f'{base_query}{where_clause}{order_clause} LIMIT {page_size} OFFSET {offset}'
            df = self.duckdb_conn.execute(data_query).fetchdf()
            
            # Query para contar total de registros (con filtros)
            count_query = f'SELECT COUNT(*) as total FROM parquet_scan("{file_path}"){where_clause}'
            total_rows = self.duckdb_conn.execute(count_query).fetchone()[0]
            
            # Convertir DataFrame a formato JSON serializable
            data_records = []
            for _, row in df.iterrows():
                record = {}
                for col in df.columns:
                    value = row[col]
                    # Manejar valores especiales
                    if pd.isna(value):
                        record[col] = None
                    elif isinstance(value, (pd.Timestamp)):
                        record[col] = value.isoformat()
                    elif isinstance(value, (np.integer, np.floating)):
                        record[col] = value.item()
                    elif isinstance(value, np.bool_):
                        record[col] = bool(value)
                    else:
                        record[col] = value
                data_records.append(record)
            
            return {
                "data": data_records,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_rows": int(total_rows),
                    "total_pages": (int(total_rows) + page_size - 1) // page_size
                },
                "columns": display_columns or list(df.columns),
                "has_custom_names": has_custom_names,
                "search_applied": bool(search_term),
                "sort_applied": bool(sort_column)
            }
            
        except Exception as e:
            raise Exception(f"Error executing query: {str(e)}")

    async def get_file_schema_with_display_names(self, filename: str) -> Dict[str, Any]:
        """Obtiene esquema con nombres personalizados y metadatos adicionales"""
        file_path = settings.PARQUET_DIR / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"File {filename} not found")
        
        try:
            # Obtener esquema técnico básico
            parquet_file = ParquetFile(file_path)
            basic_schema = parquet_file.get_schema()
            
            # Obtener metadatos de columnas usando la misma sesión
            from models.database_models import ColumnMetadata
            from sqlalchemy import select
            
            query = select(ColumnMetadata).where(
                ColumnMetadata.filename == filename,
                ColumnMetadata.is_visible == True
            ).order_by(ColumnMetadata.sort_order, ColumnMetadata.original_column_name)
            
            result = await self.metadata_service.db.execute(query)
            metadata_list = result.scalars().all()
            
            # Crear mapeo de metadatos
            columns_mapping = {
                meta.original_column_name: meta for meta in metadata_list
            }
            
            has_custom_names = len(metadata_list) > 0
            
            # Enriquecer esquema con metadatos personalizados
            enhanced_schema = []
            for col_info in basic_schema:
                original_name = col_info["name"]
                custom_info = columns_mapping.get(original_name)
                
                enhanced_col = {
                    "original_name": original_name,
                    "display_name": custom_info.display_name if custom_info else original_name,
                    "description": custom_info.description if custom_info else "",
                    "type": col_info["type"],
                    "null_count": col_info.get("null_count", 0),
                    "unique_count": col_info.get("unique_count", 0),
                    "is_visible": custom_info.is_visible if custom_info else True,
                    "has_custom_metadata": custom_info is not None
                }
                
                enhanced_schema.append(enhanced_col)
            
            return {
                "filename": filename,
                "has_custom_names": has_custom_names,
                "schema": enhanced_schema,
                "total_columns": len(enhanced_schema)
            }
            
        except Exception as e:
            raise Exception(f"Error getting enhanced schema: {str(e)}")