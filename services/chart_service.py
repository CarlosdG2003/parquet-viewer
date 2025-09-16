from typing import List, Dict, Any, Optional
import duckdb
import pandas as pd
import numpy as np
from pathlib import Path
from config import settings

class ChartService:
    """Servicio para generar gráficas manuales desde archivos Parquet"""
    
    def __init__(self, duckdb_conn):
        self.duckdb_conn = duckdb_conn

    def _convert_numpy_types(self, obj):
        """Convierte tipos numpy a tipos Python nativos para serialización JSON"""
        if isinstance(obj, np.bool_):  
            return bool(obj)
        elif isinstance(obj, (np.integer, np.signedinteger, np.unsignedinteger)):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, pd.Series):  
            return obj.tolist()
        elif isinstance(obj, dict):
            return {key: self._convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_types(item) for item in obj]
        elif pd.isna(obj):  
            return None
        else:
            return obj

    async def get_file_columns_info(self, filename: str) -> Dict[str, Any]:
        """Obtiene información de las columnas para el generador manual"""
        file_path = settings.PARQUET_DIR / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Archivo {filename} no encontrado")

        try:
            # Obtener esquema
            schema_query = f'DESCRIBE SELECT * FROM parquet_scan("{file_path}")'
            schema_df = self.duckdb_conn.execute(schema_query).fetchdf()
            
            # Obtener muestra de datos para análisis
            sample_query = f'SELECT * FROM parquet_scan("{file_path}") LIMIT 50'
            sample_df = self.duckdb_conn.execute(sample_query).fetchdf()
            
            columns_info = []
            for _, row in schema_df.iterrows():
                col_name = row['column_name']
                col_type = row['column_type']
                
                # Analizar contenido de la columna
                if col_name in sample_df.columns:
                    col_data = sample_df[col_name]
                    
                    # Convertir sample_values de forma más segura
                    sample_values_raw = col_data.dropna().head(3)
                    sample_values = [self._convert_numpy_types(val) for val in sample_values_raw.tolist()]
                    
                    unique_count = self._convert_numpy_types(col_data.nunique())
                    has_nulls = self._convert_numpy_types(col_data.isnull().sum() > 0)
                else:
                    sample_values = []
                    unique_count = 0
                    has_nulls = False
                
                columns_info.append({
                    "name": col_name,
                    "type": col_type,
                    "category": self._categorize_column_type(col_type),
                    "sample_values": sample_values,
                    "unique_count": unique_count,
                    "has_nulls": has_nulls,
                    "suitable_for_x": self._is_suitable_for_x_axis(col_type, unique_count),
                    "suitable_for_y": self._is_suitable_for_y_axis(col_type)
                })
            
            total_rows = self._get_row_count(file_path)
            
            result = {
                "filename": filename,
                "total_rows": total_rows,
                "columns": columns_info
            }
            
            return self._convert_numpy_types(result)
            
        except Exception as e:
            raise Exception(f"Error obteniendo información de columnas: {str(e)}")

    def _categorize_column_type(self, col_type: str) -> str:
        """Categoriza el tipo de columna"""
        col_type_lower = col_type.lower()
        
        if 'date' in col_type_lower or 'timestamp' in col_type_lower:
            return 'datetime'
        elif 'varchar' in col_type_lower or 'string' in col_type_lower:
            return 'text'
        elif 'integer' in col_type_lower or 'bigint' in col_type_lower:
            return 'integer'
        elif 'double' in col_type_lower or 'decimal' in col_type_lower or 'float' in col_type_lower:
            return 'decimal'
        elif 'boolean' in col_type_lower:
            return 'boolean'
        else:
            return 'other'

    def _is_suitable_for_x_axis(self, col_type: str, unique_count: int) -> bool:
        """Determina si una columna es adecuada para eje X"""
        category = self._categorize_column_type(col_type)
        
        if category in ['datetime', 'integer', 'decimal']:
            return True
        elif category == 'text' and unique_count <= 50:  # Categorías con pocas opciones
            return True
        else:
            return False

    def _is_suitable_for_y_axis(self, col_type: str) -> bool:
        """Determina si una columna es adecuada para eje Y"""
        category = self._categorize_column_type(col_type)
        return category in ['integer', 'decimal']

    def _get_row_count(self, file_path: Path) -> int:
        """Obtiene el número total de filas"""
        try:
            count_query = f'SELECT COUNT(*) as total FROM parquet_scan("{file_path}")'
            result = self.duckdb_conn.execute(count_query).fetchone()
            return int(result[0]) if result else 0
        except:
            return 0

    async def generate_custom_chart(self, filename: str, chart_config: Dict[str, Any]) -> Dict[str, Any]:
        """Genera una gráfica personalizada según la configuración del usuario"""
        file_path = settings.PARQUET_DIR / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Archivo {filename} no encontrado")

        chart_type = chart_config.get("chart_type")
        x_column = chart_config.get("x_column")
        y_column = chart_config.get("y_column")
        title = chart_config.get("title", f"{y_column} vs {x_column}")
        limit = chart_config.get("limit", 1000)
        
        try:
            if chart_type == "line":
                return await self._generate_line_chart(file_path, x_column, y_column, title, limit)
            elif chart_type == "bar":
                return await self._generate_bar_chart(file_path, x_column, y_column, title, limit)
            elif chart_type == "histogram":
                return await self._generate_histogram_chart(file_path, x_column, title, limit)
            elif chart_type == "scatter":
                return await self._generate_scatter_chart(file_path, x_column, y_column, title, limit)
            else:
                raise ValueError(f"Tipo de gráfica no soportado: {chart_type}")
                
        except Exception as e:
            raise Exception(f"Error generando gráfica personalizada: {str(e)}")

    async def _generate_line_chart(self, file_path: Path, x_column: str, y_column: str, title: str, limit: int) -> Dict[str, Any]:
        """Genera gráfica de líneas"""
        query = f'''
        SELECT "{x_column}" as x, "{y_column}" as y
        FROM parquet_scan("{file_path}")
        WHERE "{x_column}" IS NOT NULL AND "{y_column}" IS NOT NULL
        ORDER BY "{x_column}"
        LIMIT {limit}
        '''
        
        df = self.duckdb_conn.execute(query).fetchdf()
        
        # Convertir DataFrame a dict de forma más segura
        data_records = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                record[col] = self._convert_numpy_types(row[col])
            data_records.append(record)
        
        result = {
            "chart_type": "line",
            "title": title,
            "data": data_records,
            "x_label": x_column,
            "y_label": y_column,
            "total_points": len(df)
        }
        
        return self._convert_numpy_types(result)

    async def _generate_bar_chart(self, file_path: Path, x_column: str, y_column: str, title: str, limit: int) -> Dict[str, Any]:
        """Genera gráfica de barras (agrupa por X y promedia Y)"""
        query = f'''
        SELECT "{x_column}" as x, AVG("{y_column}") as y, COUNT(*) as count
        FROM parquet_scan("{file_path}")
        WHERE "{x_column}" IS NOT NULL AND "{y_column}" IS NOT NULL
        GROUP BY "{x_column}"
        ORDER BY y DESC
        LIMIT {limit}
        '''
        
        df = self.duckdb_conn.execute(query).fetchdf()
        
        # Convertir DataFrame a dict de forma más segura
        data_records = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                record[col] = self._convert_numpy_types(row[col])
            data_records.append(record)
        
        result = {
            "chart_type": "bar",
            "title": title,
            "data": data_records,
            "x_label": x_column,
            "y_label": f"Promedio de {y_column}",
            "total_groups": len(df)
        }
        
        return self._convert_numpy_types(result)

    async def _generate_histogram_chart(self, file_path: Path, x_column: str, title: str, limit: int) -> Dict[str, Any]:
        """Genera histograma"""
        query = f'''
        SELECT "{x_column}" as value
        FROM parquet_scan("{file_path}")
        WHERE "{x_column}" IS NOT NULL
        LIMIT {limit}
        '''
        
        df = self.duckdb_conn.execute(query).fetchdf()
        values = [self._convert_numpy_types(val) for val in df['value'].tolist()]
        
        result = {
            "chart_type": "histogram",
            "title": title,
            "data": values,
            "x_label": x_column,
            "y_label": "Frecuencia",
            "total_values": len(values)
        }
        
        return self._convert_numpy_types(result)

    async def _generate_scatter_chart(self, file_path: Path, x_column: str, y_column: str, title: str, limit: int) -> Dict[str, Any]:
        """Genera gráfica de dispersión"""
        query = f'''
        SELECT "{x_column}" as x, "{y_column}" as y
        FROM parquet_scan("{file_path}")
        WHERE "{x_column}" IS NOT NULL AND "{y_column}" IS NOT NULL
        LIMIT {limit}
        '''
        
        df = self.duckdb_conn.execute(query).fetchdf()
        
        # Convertir DataFrame a dict de forma más segura
        data_records = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                record[col] = self._convert_numpy_types(row[col])
            data_records.append(record)
        
        result = {
            "chart_type": "scatter",
            "title": title,
            "data": data_records,
            "x_label": x_column,
            "y_label": y_column,
            "total_points": len(df)
        }
        
        return self._convert_numpy_types(result)