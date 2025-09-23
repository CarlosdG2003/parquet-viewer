import json
import os
import zipfile
import tempfile
from pathlib import Path
from typing import Dict, List, Any
import xml.etree.ElementTree as ET
from xml.dom import minidom
import logging
from datetime import datetime
import uuid

from .parquet_processor import TableMetadata, RelationshipMetadata

logger = logging.getLogger(__name__)

class TabularModelGenerator:
    """Generador de modelos tabulares para Power BI"""
    
    def __init__(self, project_name: str):
        self.project_name = project_name
        self.model_id = str(uuid.uuid4())
        self.tables_metadata: Dict[str, TableMetadata] = {}
        self.relationships: List[RelationshipMetadata] = []
        
    def set_tables_metadata(self, tables_metadata: Dict[str, TableMetadata]):
        """Establece los metadatos de las tablas"""
        self.tables_metadata = tables_metadata
        
    def set_relationships(self, relationships: List[RelationshipMetadata]):
        """Establece las relaciones del modelo"""
        self.relationships = relationships
    
    def generate_bim_json(self) -> Dict[str, Any]:
        """Genera el archivo BIM (Business Intelligence Model) en formato JSON"""
        
        bim_model = {
            "name": self.project_name,
            "compatibilityLevel": 1520,  # Power BI Desktop compatible
            "model": {
                "culture": "es-ES",
                "dataSources": self._generate_data_sources(),
                "tables": self._generate_tables(),
                "relationships": self._generate_relationships_bim(),
                "annotations": [
                    {
                        "name": "ClientCompatibilityLevel",
                        "value": "600"
                    },
                    {
                        "name": "ResourcePackage", 
                        "value": "{\"version\":\"3.0.0.0\"}"
                    }
                ]
            }
        }
        
        return bim_model
    
    def _generate_data_sources(self) -> List[Dict[str, Any]]:
        """Genera las fuentes de datos para el modelo BIM"""
        # Para Parquet files, usamos un data source genérico
        data_sources = [{
            "type": "structured",
            "name": f"ParquetDataSource_{self.model_id[:8]}",
            "connectionDetails": {
                "protocol": "file",
                "address": {
                    "path": "./data"
                }
            },
            "credential": {
                "AuthenticationKind": "Anonymous",
                "kind": "Anonymous"
            }
        }]
        
        return data_sources
    
    def _generate_tables(self) -> List[Dict[str, Any]]:
        """Genera las definiciones de tabla para el modelo BIM"""
        tables = []
        
        for table_name, table_metadata in self.tables_metadata.items():
            
            table_def = {
                "name": table_metadata.friendly_name or table_name,
                "columns": self._generate_columns(table_metadata),
                "partitions": [{
                    "name": f"Partition_{table_name}",
                    "dataView": "full",
                    "source": {
                        "type": "m",
                        "expression": self._generate_m_query(table_metadata)
                    }
                }],
                "annotations": [
                    {
                        "name": "PBI_ResultType",
                        "value": "Table"
                    }
                ]
            }
            
            # Agregar medidas si las hay
            measures = self._generate_measures(table_metadata)
            if measures:
                table_def["measures"] = measures
            
            tables.append(table_def)
        
        return tables
    
    def _generate_columns(self, table_metadata: TableMetadata) -> List[Dict[str, Any]]:
        """Genera las definiciones de columna"""
        columns = []
        
        for col_meta in table_metadata.columns:
            column_def = {
                "name": col_meta["friendly_name"] or col_meta["column_name"],
                "dataType": self._map_to_bim_type(col_meta["data_type"]),
                "sourceColumn": col_meta["column_name"],
                "summarizeBy": self._get_default_summarization(col_meta["data_type"])
            }
            
            # Propiedades adicionales
            if not col_meta.get("is_visible", True):
                column_def["isHidden"] = True
                
            if col_meta.get("is_key", False):
                column_def["isKey"] = True
                column_def["summarizeBy"] = "none"
            
            if col_meta.get("description"):
                column_def["description"] = col_meta["description"]
                
            if col_meta.get("format_string"):
                column_def["formatString"] = col_meta["format_string"]
            
            columns.append(column_def)
        
        return columns
    
    def _map_to_bim_type(self, powerbi_type: str) -> str:
        """Mapea tipos Power BI a tipos BIM"""
        type_mapping = {
            'Text': 'string',
            'Integer': 'int64',
            'Decimal': 'double',
            'Date': 'dateTime',
            'DateTime': 'dateTime',
            'Time': 'dateTime',
            'True/False': 'boolean',
            'Currency': 'decimal'
        }
        return type_mapping.get(powerbi_type, 'string')
    
    def _get_default_summarization(self, data_type: str) -> str:
        """Obtiene la sumarización por defecto según el tipo de dato"""
        if data_type in ['Integer', 'Decimal', 'Currency']:
            return 'sum'
        elif data_type in ['Date', 'DateTime']:
            return 'none'
        else:
            return 'none'
    
    def _generate_m_query(self, table_metadata: TableMetadata) -> str:
        """Genera la consulta M (Power Query) para cargar los datos del Parquet"""
        # Obtener el nombre del archivo sin extensión
        file_name = f"{table_metadata.table_name}.parquet"
        
        m_query = f'''let
    Source = Parquet.Document(File.Contents("{file_name}")),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{'''
        
        # Agregar transformaciones de tipo para cada columna
        type_transformations = []
        for col in table_metadata.columns:
            m_type = self._get_m_data_type(col["data_type"])
            type_transformations.append(f'{{"{col["column_name"]}", {m_type}}}')
        
        m_query += ", ".join(type_transformations)
        m_query += "})"
        
        # Renombrar columnas si tienen nombres amigables diferentes
        renames = []
        for col in table_metadata.columns:
            if col["friendly_name"] and col["friendly_name"] != col["column_name"]:
                renames.append(f'{{"{col["column_name"]}", "{col["friendly_name"]}"}}')
        
        if renames:
            m_query += f''',
    #"Renamed Columns" = Table.RenameColumns(#"Changed Type", {{{", ".join(renames)}}})'''
            m_query += '''
in
    #"Renamed Columns"'''
        else:
            m_query += '''
in
    #"Changed Type"'''
        
        return m_query
    
    def _get_m_data_type(self, powerbi_type: str) -> str:
        """Obtiene el tipo de dato M correspondiente"""
        type_mapping = {
            'Text': 'type text',
            'Integer': 'Int64.Type',
            'Decimal': 'type number',
            'Date': 'type date',
            'DateTime': 'type datetimezone',
            'Time': 'type time',
            'True/False': 'type logical',
            'Currency': 'Currency.Type'
        }
        return type_mapping.get(powerbi_type, 'type text')
    
    def _generate_measures(self, table_metadata: TableMetadata) -> List[Dict[str, Any]]:
        """Genera medidas básicas para la tabla"""
        measures = []
        
        # Agregar medida de conteo de filas
        count_measure = {
            "name": f"Count of {table_metadata.friendly_name}",
            "expression": f"COUNTROWS('{table_metadata.friendly_name}')",
            "formatString": "#,0"
        }
        measures.append(count_measure)
        
        # Agregar medidas para columnas numéricas
        for col in table_metadata.columns:
            if col["data_type"] in ['Integer', 'Decimal', 'Currency'] and not col.get("is_key", False):
                col_name = col["friendly_name"] or col["column_name"]
                
                # Suma
                sum_measure = {
                    "name": f"Sum of {col_name}",
                    "expression": f"SUM('{table_metadata.friendly_name}'[{col_name}])",
                    "formatString": "#,0.00" if col["data_type"] in ['Decimal', 'Currency'] else "#,0"
                }
                measures.append(sum_measure)
                
                # Promedio
                avg_measure = {
                    "name": f"Average of {col_name}",
                    "expression": f"AVERAGE('{table_metadata.friendly_name}'[{col_name}])",
                    "formatString": "#,0.00"
                }
                measures.append(avg_measure)
        
        return measures
    
    def _generate_relationships_bim(self) -> List[Dict[str, Any]]:
        """Genera las definiciones de relación para el modelo BIM"""
        relationships_bim = []
        
        for i, rel in enumerate(self.relationships):
            # Buscar las tablas en los metadatos
            parent_table = None
            child_table = None
            
            for table_name, table_meta in self.tables_metadata.items():
                if table_name == rel.parent_table:
                    parent_table = table_meta.friendly_name or table_name
                elif table_name == rel.child_table:
                    child_table = table_meta.friendly_name or table_name
            
            if parent_table and child_table:
                relationship_def = {
                    "name": f"Relationship_{i+1}",
                    "fromTable": child_table,
                    "fromColumn": rel.child_column,
                    "toTable": parent_table,
                    "toColumn": rel.parent_column,
                    "crossFilteringBehavior": self._map_cross_filter_direction(rel.cross_filter_direction),
                    "isActive": rel.is_active,
                    "securityFilteringBehavior": "none"
                }
                
                relationships_bim.append(relationship_def)
        
        return relationships_bim
    
    def _map_cross_filter_direction(self, direction: str) -> str:
        """Mapea la dirección de filtrado cruzado"""
        mapping = {
            'single': 'oneDirection',
            'both': 'bothDirections',
            'none': 'none'
        }
        return mapping.get(direction.lower(), 'oneDirection')
    
    def generate_pbit_file(self, output_path: str) -> str:
        """Genera un archivo PBIT (Power BI Template)"""
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Generar el modelo BIM
            bim_content = self.generate_bim_json()
            
            # Crear estructura de archivos PBIT
            data_model_schema_path = os.path.join(temp_dir, "DataModelSchema")
            os.makedirs(data_model_schema_path, exist_ok=True)
            
            # Escribir el archivo BIM
            bim_file_path = os.path.join(data_model_schema_path, "model.bim")
            with open(bim_file_path, 'w', encoding='utf-8') as f:
                json.dump(bim_content, f, indent=2, ensure_ascii=False)
            
            # Crear archivo de metadatos
            metadata = {
                "version": "3.0",
                "datasetVersion": "1.0"
            }
            
            metadata_path = os.path.join(temp_dir, "Metadata")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f)
            
            # Crear archivo de configuración
            config = {
                "version": "5.49",
                "themeCollection": {
                    "baseTheme": {
                        "name": "CY22SU06"
                    }
                }
            }
            
            config_path = os.path.join(temp_dir, "Settings")
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f)
            
            # Crear el archivo ZIP (PBIT)
            pbit_path = output_path
            with zipfile.ZipFile(pbit_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Agregar todos los archivos al ZIP
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
            
            logger.info(f"Archivo PBIT generado: {pbit_path}")
            return pbit_path
            
        except Exception as e:
            logger.error(f"Error generando archivo PBIT: {str(e)}")
            raise
        
        finally:
            # Limpiar archivos temporales
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def generate_documentation(self) -> str:
        """Genera documentación del modelo"""
        doc = f"""# Documentación del Modelo Power BI: {self.project_name}

## Resumen
- **Nombre del Modelo**: {self.project_name}
- **Fecha de Generación**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Número de Tablas**: {len(self.tables_metadata)}
- **Número de Relaciones**: {len(self.relationships)}

## Tablas

"""
        
        for table_name, table_meta in self.tables_metadata.items():
            doc += f"""### {table_meta.friendly_name or table_name}
- **Nombre Técnico**: {table_name}
- **Archivo Origen**: {table_name}.parquet
- **Filas**: {table_meta.row_count:,}
- **Columnas**: {len(table_meta.columns)}
- **Tamaño**: {table_meta.file_size / (1024*1024):.2f} MB

#### Columnas:
"""
            for col in table_meta.columns:
                key_indicator = " 🔑" if col.get("is_key") else ""
                hidden_indicator = " (Oculta)" if not col.get("is_visible", True) else ""
                doc += f"- **{col['friendly_name']}** ({col['data_type']}){key_indicator}{hidden_indicator}\n"
                if col.get("description"):
                    doc += f"  - {col['description']}\n"
            
            doc += "\n"
        
        doc += "## Relaciones\n\n"
        
        if self.relationships:
            for i, rel in enumerate(self.relationships, 1):
                doc += f"""### Relación {i}
- **Tabla Padre**: {rel.parent_table} (Columna: {rel.parent_column})
- **Tabla Hija**: {rel.child_table} (Columna: {rel.child_column})  
- **Cardinalidad**: {rel.cardinality}
- **Filtrado Cruzado**: {rel.cross_filter_direction}
- **Estado**: {'Activa' if rel.is_active else 'Inactiva'}

"""
        else:
            doc += "No se encontraron relaciones definidas.\n\n"
        
        doc += """## Instrucciones de Uso

### Abrir en Power BI Desktop
1. Descarga e instala Power BI Desktop
2. Abre el archivo .pbit generado
3. Configura la ruta a los archivos Parquet cuando se solicite
4. Actualiza los datos (Inicio > Actualizar)

### Verificar el Modelo
1. Ve a la vista de Modelo (icono de diagrama)
2. Verifica que todas las tablas están presentes
3. Confirma que las relaciones se muestran correctamente
4. Verifica los tipos de datos en cada tabla

### Solución de Problemas
- Si los datos no cargan, verifica que los archivos Parquet están en la ruta correcta
- Si faltan relaciones, puede que no se hayan detectado automáticamente
- Para relaciones personalizadas, créalas manualmente en la vista de Modelo

"""
        
        return doc

    def export_to_xmla(self, server_url: str, database_name: str) -> Dict[str, Any]:
        """Exporta el modelo usando XMLA (Analysis Services)"""
        # Esta funcionalidad requiere librerías adicionales como python-ssas
        # Por ahora retornamos la estructura que se usaría
        
        xmla_script = {
            "create_database": {
                "database": {
                    "name": database_name,
                    "compatibilityLevel": 1520,
                    "model": self.generate_bim_json()["model"]
                }
            },
            "server_url": server_url,
            "instructions": [
                "Instalar: pip install python-ssas",
                "Configurar conexión al servidor Analysis Services",
                "Ejecutar script de creación de base de datos",
                "Procesar el modelo para cargar datos"
            ]
        }
        
        return xmla_script

class PowerBIExporter:
    """Clase auxiliar para exportar modelos Power BI"""
    
    def __init__(self, tables_metadata: Dict[str, TableMetadata], relationships: List[RelationshipMetadata]):
        self.tables_metadata = tables_metadata
        self.relationships = relationships
    
    def export_model(self, project_name: str, export_type: str, output_path: str) -> Dict[str, Any]:
        """Exporta el modelo en el formato especificado"""
        
        generator = TabularModelGenerator(project_name)
        generator.set_tables_metadata(self.tables_metadata)
        generator.set_relationships(self.relationships)
        
        result = {
            "export_type": export_type,
            "project_name": project_name,
            "status": "success",
            "output_path": output_path,
            "documentation": generator.generate_documentation()
        }
        
        try:
            if export_type == "pbit":
                pbit_path = generator.generate_pbit_file(output_path)
                result["file_path"] = pbit_path
                result["instructions"] = [
                    "1. Descarga Power BI Desktop desde Microsoft Store o sitio oficial",
                    "2. Abre el archivo .pbit generado",
                    "3. Cuando se solicite, configura la ruta a los archivos Parquet",
                    "4. Haz clic en 'Actualizar' para cargar los datos",
                    "5. Ve a la vista de Modelo para verificar las relaciones"
                ]
                
            elif export_type == "xmla":
                xmla_result = generator.export_to_xmla("localhost", project_name)
                result["xmla_script"] = xmla_result
                result["instructions"] = xmla_result["instructions"]
                
            elif export_type == "json":
                bim_model = generator.generate_bim_json()
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(bim_model, f, indent=2, ensure_ascii=False)
                result["file_path"] = output_path
                result["instructions"] = [
                    "Archivo BIM JSON generado",
                    "Puede importarse usando Tabular Editor",
                    "O convertirse a PBIX usando herramientas de Microsoft"
                ]
            
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.error(f"Error exportando modelo {export_type}: {str(e)}")
        
        return result