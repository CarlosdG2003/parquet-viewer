from typing import List, Optional, Dict, Any
from pathlib import Path
import duckdb
from datetime import datetime
from models.parquet_file import ParquetFile
from models.database_models import CombinedFileInfo, FileMetadata
from services.metadata_service import MetadataService
from config import settings

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