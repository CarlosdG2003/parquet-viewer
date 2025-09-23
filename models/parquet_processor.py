import os
import json
import xml.etree.ElementTree as ET
import pyarrow.parquet as pq
import pyarrow as pa
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TableMetadata:
    """Metadatos de una tabla"""
    table_name: str
    friendly_name: str
    columns: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    row_count: int
    file_size: int

@dataclass
class RelationshipMetadata:
    """Metadatos de una relación entre tablas"""
    parent_table: str
    child_table: str
    parent_column: str
    child_column: str
    cardinality: str
    cross_filter_direction: str = 'single'
    is_active: bool = True

class ParquetProcessor:
    """Procesador principal para archivos Parquet y sus metadatos"""
    
    def __init__(self, data_directory: str):
        self.data_directory = Path(data_directory)
        self.tables_metadata: Dict[str, TableMetadata] = {}
        self.global_relationships: List[RelationshipMetadata] = []
        
    def discover_parquet_files(self) -> List[Path]:
        """Descubre todos los archivos Parquet en el directorio"""
        parquet_files = list(self.data_directory.glob("*.parquet"))
        logger.info(f"Encontrados {len(parquet_files)} archivos Parquet")
        return parquet_files
    
    def read_parquet_file(self, file_path: Path) -> Tuple[pd.DataFrame, pa.Table]:
        """Lee un archivo Parquet y retorna DataFrame y PyArrow Table"""
        try:
            # Leer con PyArrow para acceder a metadatos
            parquet_file = pq.ParquetFile(file_path)
            arrow_table = parquet_file.read()
            
            # Convertir a DataFrame para análisis
            df = arrow_table.to_pandas()
            
            logger.info(f"Leído {file_path.name}: {len(df)} filas, {len(df.columns)} columnas")
            return df, arrow_table
            
        except Exception as e:
            logger.error(f"Error leyendo {file_path}: {str(e)}")
            raise
    
    def extract_embedded_metadata(self, arrow_table: pa.Table, table_name: str) -> Dict[str, Any]:
        """Extrae metadatos incrustados en el archivo Parquet"""
        metadata = {}
        
        try:
            # Metadatos del archivo
            if arrow_table.schema.metadata:
                file_metadata = arrow_table.schema.metadata
                
                # Buscar metadatos específicos de Power BI
                for key, value in file_metadata.items():
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else str(key)
                    value_str = value.decode('utf-8') if isinstance(value, bytes) else str(value)
                    
                    if key_str.startswith('powerbi_'):
                        try:
                            metadata[key_str] = json.loads(value_str)
                        except json.JSONDecodeError:
                            metadata[key_str] = value_str
            
            # Metadatos de columnas
            column_metadata = {}
            for i, field in enumerate(arrow_table.schema):
                if field.metadata:
                    col_meta = {}
                    for key, value in field.metadata.items():
                        key_str = key.decode('utf-8') if isinstance(key, bytes) else str(key)
                        value_str = value.decode('utf-8') if isinstance(value, bytes) else str(value)
                        col_meta[key_str] = value_str
                    
                    if col_meta:
                        column_metadata[field.name] = col_meta
            
            if column_metadata:
                metadata['columns'] = column_metadata
                
            logger.info(f"Metadatos extraídos de {table_name}: {len(metadata)} elementos")
            
        except Exception as e:
            logger.warning(f"No se pudieron extraer metadatos de {table_name}: {str(e)}")
        
        return metadata
    
    def read_external_metadata_json(self, parquet_file: Path) -> Dict[str, Any]:
        """Lee metadatos desde un archivo JSON externo"""
        # Buscar archivo JSON con el mismo nombre
        json_file = parquet_file.with_suffix('.json')
        
        if not json_file.exists():
            # Buscar archivo de metadatos general
            json_file = parquet_file.parent / f"{parquet_file.stem}_metadata.json"
        
        if json_file.exists():
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                logger.info(f"Metadatos JSON leídos de {json_file.name}")
                return metadata
            except Exception as e:
                logger.warning(f"Error leyendo metadatos JSON de {json_file}: {str(e)}")
        
        return {}
    
    def read_external_metadata_xml(self, parquet_file: Path) -> Dict[str, Any]:
        """Lee metadatos desde un archivo XML externo"""
        xml_file = parquet_file.with_suffix('.xml')
        
        if not xml_file.exists():
            xml_file = parquet_file.parent / f"{parquet_file.stem}_metadata.xml"
        
        if xml_file.exists():
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()
                metadata = self._parse_xml_metadata(root)
                logger.info(f"Metadatos XML leídos de {xml_file.name}")
                return metadata
            except Exception as e:
                logger.warning(f"Error leyendo metadatos XML de {xml_file}: {str(e)}")
        
        return {}
    
    def _parse_xml_metadata(self, element: ET.Element) -> Dict[str, Any]:
        """Convierte XML a diccionario"""
        result = {}
        
        # Si el elemento tiene texto y no tiene hijos, devolver el texto
        if element.text and not list(element):
            return element.text.strip()
        
        # Procesar atributos
        if element.attrib:
            result.update(element.attrib)
        
        # Procesar elementos hijos
        for child in element:
            child_data = self._parse_xml_metadata(child)
            
            if child.tag in result:
                # Si ya existe, convertir a lista
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data
        
        return result
    
    def infer_column_metadata(self, df: pd.DataFrame, arrow_table: pa.Table) -> List[Dict[str, Any]]:
        """Infiere metadatos de columnas basado en los datos"""
        columns = []
        
        for i, (col_name, dtype) in enumerate(zip(df.columns, df.dtypes)):
            arrow_field = arrow_table.schema.field(i)
            
            # Mapear tipos de pandas/arrow a tipos Power BI
            powerbi_type = self._map_to_powerbi_type(dtype, arrow_field.type)
            
            column_meta = {
                'column_name': col_name,
                'friendly_name': col_name.replace('_', ' ').title(),
                'data_type': powerbi_type,
                'is_nullable': arrow_field.nullable,
                'is_key': self._detect_key_column(df[col_name]),
                'sort_order': i,
                'is_visible': True
            }
            
            columns.append(column_meta)
        
        return columns
    
    def _map_to_powerbi_type(self, pandas_dtype, arrow_type) -> str:
        """Mapea tipos de datos a tipos compatibles con Power BI"""
        # Mapeo de tipos PyArrow a Power BI
        type_mapping = {
            pa.int8(): 'Integer',
            pa.int16(): 'Integer', 
            pa.int32(): 'Integer',
            pa.int64(): 'Integer',
            pa.uint8(): 'Integer',
            pa.uint16(): 'Integer',
            pa.uint32(): 'Integer',
            pa.uint64(): 'Integer',
            pa.float32(): 'Decimal',
            pa.float64(): 'Decimal',
            pa.string(): 'Text',
            pa.bool_(): 'True/False',
            pa.date32(): 'Date',
            pa.date64(): 'Date',
            pa.timestamp('ns'): 'DateTime',
            pa.timestamp('us'): 'DateTime',
            pa.timestamp('ms'): 'DateTime',
            pa.timestamp('s'): 'DateTime',
        }
        
        # Buscar coincidencia exacta
        for pa_type, pbi_type in type_mapping.items():
            if arrow_type.equals(pa_type):
                return pbi_type
        
        # Buscar por tipo base
        if pa.types.is_integer(arrow_type):
            return 'Integer'
        elif pa.types.is_floating(arrow_type):
            return 'Decimal'
        elif pa.types.is_string(arrow_type) or pa.types.is_large_string(arrow_type):
            return 'Text'
        elif pa.types.is_boolean(arrow_type):
            return 'True/False'
        elif pa.types.is_date(arrow_type):
            return 'Date'
        elif pa.types.is_timestamp(arrow_type):
            return 'DateTime'
        elif pa.types.is_time(arrow_type):
            return 'Time'
        
        # Por defecto
        return 'Text'
    
    def _detect_key_column(self, series: pd.Series) -> bool:
        """Detecta si una columna podría ser una clave"""
        # Heurísticas para detectar claves
        if len(series) == 0:
            return False
        
        # Si todos los valores son únicos y no hay nulos
        if series.nunique() == len(series) and not series.isnull().any():
            # Si el nombre sugiere que es una clave
            col_name_lower = series.name.lower()
            if any(keyword in col_name_lower for keyword in ['id', 'key', 'pk', 'codigo']):
                return True
            
            # Si es numérico entero y secuencial
            if pd.api.types.is_integer_dtype(series):
                sorted_values = sorted(series.dropna())
                if len(sorted_values) > 1:
                    differences = [sorted_values[i+1] - sorted_values[i] for i in range(len(sorted_values)-1)]
                    if all(diff == 1 for diff in differences):  # Secuencial
                        return True
        
        return False
    
    def parse_relationships_metadata(self, metadata: Dict[str, Any]) -> List[RelationshipMetadata]:
        """Parsea relaciones desde metadatos"""
        relationships = []
        
        # Buscar relaciones en diferentes formatos
        relationships_data = (
            metadata.get('relationships') or 
            metadata.get('powerbi_relationships') or 
            metadata.get('relations') or
            []
        )
        
        for rel_data in relationships_data:
            try:
                relationship = RelationshipMetadata(
                    parent_table=rel_data['parent_table'],
                    child_table=rel_data['child_table'],
                    parent_column=rel_data['parent_column'],
                    child_column=rel_data['child_column'],
                    cardinality=rel_data.get('cardinality', '1:N'),
                    cross_filter_direction=rel_data.get('cross_filter_direction', 'single'),
                    is_active=rel_data.get('is_active', True)
                )
                relationships.append(relationship)
            except KeyError as e:
                logger.warning(f"Relación incompleta, falta campo: {e}")
        
        return relationships
    
    def process_all_files(self) -> Dict[str, TableMetadata]:
        """Procesa todos los archivos Parquet en el directorio"""
        parquet_files = self.discover_parquet_files()
        
        for file_path in parquet_files:
            try:
                table_name = file_path.stem
                logger.info(f"Procesando tabla: {table_name}")
                
                # Leer archivo Parquet
                df, arrow_table = self.read_parquet_file(file_path)
                
                # Obtener metadatos de diferentes fuentes
                embedded_metadata = self.extract_embedded_metadata(arrow_table, table_name)
                json_metadata = self.read_external_metadata_json(file_path)
                xml_metadata = self.read_external_metadata_xml(file_path)
                
                # Combinar metadatos (prioridad: JSON > XML > embedded)
                combined_metadata = {}
                combined_metadata.update(embedded_metadata)
                combined_metadata.update(xml_metadata)
                combined_metadata.update(json_metadata)
                
                # Inferir metadatos de columnas
                columns_metadata = self.infer_column_metadata(df, arrow_table)
                
                # Aplicar metadatos personalizados de columnas si existen
                if 'columns' in combined_metadata:
                    columns_metadata = self._merge_column_metadata(
                        columns_metadata, 
                        combined_metadata['columns']
                    )
                
                # Extraer relaciones
                table_relationships = self.parse_relationships_metadata(combined_metadata)
                self.global_relationships.extend(table_relationships)
                
                # Crear metadatos de tabla
                table_metadata = TableMetadata(
                    table_name=table_name,
                    friendly_name=combined_metadata.get('friendly_name', table_name.replace('_', ' ').title()),
                    columns=columns_metadata,
                    relationships=table_relationships,
                    row_count=len(df),
                    file_size=file_path.stat().st_size
                )
                
                self.tables_metadata[table_name] = table_metadata
                logger.info(f"Procesada tabla {table_name}: {len(df)} filas, {len(columns_metadata)} columnas")
                
            except Exception as e:
                logger.error(f"Error procesando {file_path}: {str(e)}")
        
        logger.info(f"Procesamiento completado: {len(self.tables_metadata)} tablas, {len(self.global_relationships)} relaciones")
        return self.tables_metadata
    
    def _merge_column_metadata(self, inferred_columns: List[Dict[str, Any]], custom_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Combina metadatos inferidos con metadatos personalizados"""
        for column in inferred_columns:
            col_name = column['column_name']
            if col_name in custom_metadata:
                custom_col = custom_metadata[col_name]
                
                # Actualizar con metadatos personalizados
                if 'friendly_name' in custom_col:
                    column['friendly_name'] = custom_col['friendly_name']
                if 'description' in custom_col:
                    column['description'] = custom_col['description']
                if 'format_string' in custom_col:
                    column['format_string'] = custom_col['format_string']
                if 'is_visible' in custom_col:
                    column['is_visible'] = custom_col['is_visible']
                if 'is_key' in custom_col:
                    column['is_key'] = custom_col['is_key']
        
        return inferred_columns
    
    def validate_relationships(self) -> List[Dict[str, Any]]:
        """Valida las relaciones encontradas"""
        validation_results = []
        table_names = set(self.tables_metadata.keys())
        
        for relationship in self.global_relationships:
            validation = {
                'relationship': relationship,
                'is_valid': True,
                'errors': [],
                'warnings': []
            }
            
            # Verificar que las tablas existen
            if relationship.parent_table not in table_names:
                validation['is_valid'] = False
                validation['errors'].append(f"Tabla padre '{relationship.parent_table}' no encontrada")
            
            if relationship.child_table not in table_names:
                validation['is_valid'] = False
                validation['errors'].append(f"Tabla hija '{relationship.child_table}' no encontrada")
            
            # Verificar que las columnas existen
            if relationship.parent_table in table_names:
                parent_columns = [col['column_name'] for col in self.tables_metadata[relationship.parent_table].columns]
                if relationship.parent_column not in parent_columns:
                    validation['is_valid'] = False
                    validation['errors'].append(f"Columna padre '{relationship.parent_column}' no encontrada en tabla '{relationship.parent_table}'")
            
            if relationship.child_table in table_names:
                child_columns = [col['column_name'] for col in self.tables_metadata[relationship.child_table].columns]
                if relationship.child_column not in child_columns:
                    validation['is_valid'] = False
                    validation['errors'].append(f"Columna hija '{relationship.child_column}' no encontrada en tabla '{relationship.child_table}'")
            
            # Validar cardinalidad
            valid_cardinalities = ['1:1', '1:N', 'N:1', 'N:N']
            if relationship.cardinality not in valid_cardinalities:
                validation['warnings'].append(f"Cardinalidad '{relationship.cardinality}' no estándar, se usará '1:N'")
            
            validation_results.append(validation)
        
        return validation_results