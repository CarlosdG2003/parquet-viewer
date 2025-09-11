from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import duckdb

class ParquetFile:

    # Inicializa con la ruta del archivo
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.name = filepath.name
        self.size = filepath.stat().st_size
        self.modified = datetime.fromtimestamp(filepath.stat().st_mtime)
        self.conn = duckdb.connect()
    
    # Obtiene metadatos (tamaño, filas, columnas)
    def get_info(self) -> Dict[str, Any]:
        try:
            result = self.conn.execute(f"SELECT COUNT(*) FROM '{self.filepath}'").fetchone()
            row_count = result[0] if result else 0
            
            schema_result = self.conn.execute(f"DESCRIBE SELECT * FROM '{self.filepath}' LIMIT 0").fetchall()
            columns = [{"name": row[0], "type": row[1]} for row in schema_result]
            
            return {
                "name": self.name,
                "size_bytes": self.size,
                "size_mb": round(self.size / (1024 * 1024), 2),
                "modified": self.modified.isoformat(),
                "row_count": row_count,
                "column_count": len(columns),
                "columns": columns
            }
        except Exception as e:
            return {
                "name": self.name,
                "size_bytes": self.size,
                "size_mb": round(self.size / (1024 * 1024), 2),
                "modified": self.modified.isoformat(),
                "error": str(e)
            }
    
    # obtiene tipos de datos y estadísticas de columnas
    def get_schema(self) -> List[Dict[str, Any]]:
        schema_result = self.conn.execute(f"DESCRIBE SELECT * FROM '{self.filepath}'").fetchall()
        schema = []
        
        for row in schema_result:
            column_info = {
                "name": row[0],
                "type": row[1],
                "null_count": None,
                "unique_count": None
            }
            
            try:
                stats_query = f"""
                SELECT 
                    COUNT(*) - COUNT("{row[0]}") as null_count,
                    COUNT(DISTINCT "{row[0]}") as unique_count
                FROM '{self.filepath}'
                """
                stats = self.conn.execute(stats_query).fetchone()
                if stats:
                    column_info["null_count"] = stats[0]
                    column_info["unique_count"] = stats[1]
            except:
                pass
            
            schema.append(column_info)
        
        return schema
    
    # obtiene datos paginados, opcionalmente filtrados por columnas
    def get_data(self, page: int = 1, page_size: int = 50, columns: List[str] = None) -> Dict[str, Any]:
        if columns:
            columns_str = ', '.join([f'"{col}"' for col in columns])
        else:
            columns_str = "*"
        
        offset = (page - 1) * page_size
        
        data_query = f"SELECT {columns_str} FROM '{self.filepath}' LIMIT {page_size} OFFSET {offset}"
        count_query = f"SELECT COUNT(*) FROM '{self.filepath}'"
        
        data_result = self.conn.execute(data_query).fetchall()
        total_rows = self.conn.execute(count_query).fetchone()[0]
        
        column_names = [desc[0] for desc in self.conn.execute(data_query).description]
        
        data = [dict(zip(column_names, row)) for row in data_result]
        
        return {
            "data": data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_rows": total_rows,
                "total_pages": (total_rows + page_size - 1) // page_size
            },
            "columns": column_names
        }
    
    # Calcula estadísticas numéricas para gráficas
    def get_stats(self) -> Dict[str, Any]:
        numeric_stats = {}
        schema_result = self.conn.execute(f"DESCRIBE SELECT * FROM '{self.filepath}'").fetchall()
        
        for column_name, column_type in schema_result:
            if any(t in column_type.upper() for t in ['INT', 'DOUBLE', 'FLOAT', 'DECIMAL', 'NUMERIC']):
                try:
                    stats_query = f"""
                    SELECT 
                        MIN("{column_name}") as min_val,
                        MAX("{column_name}") as max_val,
                        AVG("{column_name}") as avg_val,
                        COUNT(DISTINCT "{column_name}") as unique_count,
                        COUNT("{column_name}") as non_null_count
                    FROM '{self.filepath}'
                    """
                    result = self.conn.execute(stats_query).fetchone()
                    if result:
                        numeric_stats[column_name] = {
                            "min": result[0],
                            "max": result[1],
                            "avg": result[2],
                            "unique_count": result[3],
                            "non_null_count": result[4]
                        }
                except:
                    continue
        
        return {"numeric_stats": numeric_stats}