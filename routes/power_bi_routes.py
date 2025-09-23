from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any
import os
import tempfile
import shutil
from pathlib import Path
import json
import logging

from core.database import get_db_session
from models.power_bi_models import PowerBIProject, PowerBITable, PowerBIColumn, PowerBIRelationship, PowerBIExport
from models.parquet_processor import ParquetProcessor
from models.tabular_model import PowerBIExporter
from core.security import verify_admin_credentials

router = APIRouter(prefix="/power-bi", tags=["Power BI"])
logger = logging.getLogger(__name__)

# Directorio para archivos temporales de Power BI
POWERBI_UPLOAD_DIR = "data/powerbi_uploads"
POWERBI_EXPORT_DIR = "exports/powerbi"

# Crear directorios si no existen
os.makedirs(POWERBI_UPLOAD_DIR, exist_ok=True)
os.makedirs(POWERBI_EXPORT_DIR, exist_ok=True)

@router.get("/projects")
async def get_projects(db: AsyncSession = Depends(get_db_session), current_admin = Depends(verify_admin_credentials)):
    """Obtiene todos los proyectos Power BI"""
    from sqlalchemy.orm import selectinload
    
    # Cargar proyectos con sus relaciones de forma asíncrona
    result = await db.execute(
        select(PowerBIProject)
        .options(selectinload(PowerBIProject.tables))
        .options(selectinload(PowerBIProject.relationships))
    )
    projects = result.scalars().all()
    
    return [{
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "status": project.status,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "tables_count": len(project.tables),
        "relationships_count": len(project.relationships)
    } for project in projects]

@router.post("/projects")
async def create_project(
    name: str = Form(...),
    description: str = Form(""),
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db_session),
    current_admin = Depends(verify_admin_credentials)
):
    """Crea un nuevo proyecto Power BI subiendo archivos Parquet"""
    
    if not files:
        raise HTTPException(status_code=400, detail="Se requiere al menos un archivo Parquet")
    
    # Validar que todos los archivos sean Parquet
    for file in files:
        if not file.filename.endswith('.parquet'):
            raise HTTPException(
                status_code=400, 
                detail=f"El archivo {file.filename} no es un archivo Parquet válido"
            )
    
    try:
        # Crear proyecto en la base de datos
        project = PowerBIProject(
            name=name,
            description=description,
            status="processing"
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)
        
        # Crear directorio para el proyecto
        project_dir = os.path.join(POWERBI_UPLOAD_DIR, str(project.id))
        os.makedirs(project_dir, exist_ok=True)
        
        # Guardar archivos Parquet
        saved_files = []
        for file in files:
            file_path = os.path.join(project_dir, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_files.append(file_path)
        
        # Procesar archivos en segundo plano
        background_tasks = BackgroundTasks()
        background_tasks.add_task(process_parquet_files_task, project.id, project_dir)
        
        return {
            "project_id": project.id,
            "name": name,
            "status": "processing",
            "message": f"Proyecto creado. Procesando {len(files)} archivos...",
            "files_uploaded": [f.filename for f in files]
        }
        
    except Exception as e:
        logger.error(f"Error creando proyecto: {str(e)}")
        # Limpiar si hay error
        if 'project' in locals():
            await db.delete(project)
            await db.commit()
        raise HTTPException(status_code=500, detail=f"Error procesando archivos: {str(e)}")

async def process_parquet_files_task(project_id: int, project_dir: str):
    """Tarea en segundo plano para procesar archivos Parquet"""
    try:
        # Crear nueva sesión para la tarea en segundo plano
        from core.database import db_manager
        async for db in db_manager.get_postgres_session():
            # Obtener el proyecto
            result = await db.execute(select(PowerBIProject).filter(PowerBIProject.id == project_id))
            project = result.scalar_one_or_none()
            if not project:
                return
            
            # Procesar archivos con ParquetProcessor
            processor = ParquetProcessor(project_dir)
            tables_metadata = processor.process_all_files()
            
            # Guardar tablas en la base de datos
            for table_name, table_meta in tables_metadata.items():
                db_table = PowerBITable(
                    project_id=project_id,
                    table_name=table_name,
                    friendly_name=table_meta.friendly_name,
                    parquet_file_path=os.path.join(project_dir, f"{table_name}.parquet"),
                    row_count=table_meta.row_count,
                    file_size=table_meta.file_size,
                    metadata_source="auto_detected"
                )
                db.add(db_table)
                await db.commit()
                await db.refresh(db_table)
                
                # Guardar columnas
                for col_meta in table_meta.columns:
                    db_column = PowerBIColumn(
                        table_id=db_table.id,
                        column_name=col_meta["column_name"],
                        friendly_name=col_meta.get("friendly_name"),
                        data_type=col_meta["data_type"],
                        is_key=col_meta.get("is_key", False),
                        is_nullable=col_meta.get("is_nullable", True),
                        description=col_meta.get("description"),
                        sort_order=col_meta.get("sort_order", 0),
                        is_visible=col_meta.get("is_visible", True)
                    )
                    db.add(db_column)
            
            # Guardar relaciones
            for rel in processor.global_relationships:
                # Buscar las tablas por nombre
                parent_result = await db.execute(
                    select(PowerBITable).filter(
                        PowerBITable.project_id == project_id,
                        PowerBITable.table_name == rel.parent_table
                    )
                )
                parent_table = parent_result.scalar_one_or_none()
                
                child_result = await db.execute(
                    select(PowerBITable).filter(
                        PowerBITable.project_id == project_id,
                        PowerBITable.table_name == rel.child_table
                    )
                )
                child_table = child_result.scalar_one_or_none()
                
                if parent_table and child_table:
                    db_relationship = PowerBIRelationship(
                        project_id=project_id,
                        parent_table_id=parent_table.id,
                        child_table_id=child_table.id,
                        parent_column=rel.parent_column,
                        child_column=rel.child_column,
                        cardinality=rel.cardinality,
                        cross_filter_direction=rel.cross_filter_direction,
                        is_active=rel.is_active,
                        status="detected"
                    )
                    db.add(db_relationship)
            
            # Actualizar estado del proyecto
            project.status = "ready"
            await db.commit()
            
            logger.info(f"Proyecto {project_id} procesado exitosamente")
            break
        
    except Exception as e:
        logger.error(f"Error procesando proyecto {project_id}: {str(e)}")
        # Actualizar estado a error
        async for db in db_manager.get_postgres_session():
            result = await db.execute(select(PowerBIProject).filter(PowerBIProject.id == project_id))
            project = result.scalar_one_or_none()
            if project:
                project.status = "error"
                await db.commit()
            break

@router.get("/projects/{project_id}")
async def get_project_details(
    project_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_admin = Depends(verify_admin_credentials)
):
    """Obtiene los detalles completos de un proyecto"""
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(PowerBIProject)
        .filter(PowerBIProject.id == project_id)
        .options(selectinload(PowerBIProject.tables).selectinload(PowerBITable.columns))
        .options(selectinload(PowerBIProject.relationships)
                .selectinload(PowerBIRelationship.parent_table))
        .options(selectinload(PowerBIProject.relationships)
                .selectinload(PowerBIRelationship.child_table))
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Obtener tablas con sus columnas
    tables_data = []
    for table in project.tables:
        table_data = {
            "id": table.id,
            "table_name": table.table_name,
            "friendly_name": table.friendly_name,
            "row_count": table.row_count,
            "file_size": table.file_size,
            "columns": [{
                "id": col.id,
                "column_name": col.column_name,
                "friendly_name": col.friendly_name,
                "data_type": col.data_type,
                "is_key": col.is_key,
                "is_visible": col.is_visible,
                "description": col.description
            } for col in table.columns]
        }
        tables_data.append(table_data)
    
    # Obtener relaciones
    relationships_data = []
    for rel in project.relationships:
        rel_data = {
            "id": rel.id,
            "parent_table": rel.parent_table.friendly_name or rel.parent_table.table_name,
            "child_table": rel.child_table.friendly_name or rel.child_table.table_name,
            "parent_column": rel.parent_column,
            "child_column": rel.child_column,
            "cardinality": rel.cardinality,
            "cross_filter_direction": rel.cross_filter_direction,
            "is_active": rel.is_active,
            "status": rel.status
        }
        relationships_data.append(rel_data)
    
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "status": project.status,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "tables": tables_data,
        "relationships": relationships_data
    }

@router.put("/projects/{project_id}/relationships/{relationship_id}")
async def update_relationship(
    project_id: int,
    relationship_id: int,
    relationship_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    current_admin = Depends(verify_admin_credentials)
):
    """Actualiza una relación específica"""
    
    result = await db.execute(
        select(PowerBIRelationship).filter(
            PowerBIRelationship.id == relationship_id,
            PowerBIRelationship.project_id == project_id
        )
    )
    relationship = result.scalar_one_or_none()
    
    if not relationship:
        raise HTTPException(status_code=404, detail="Relación no encontrada")
    
    # Actualizar campos permitidos
    if "cardinality" in relationship_data:
        relationship.cardinality = relationship_data["cardinality"]
    if "cross_filter_direction" in relationship_data:
        relationship.cross_filter_direction = relationship_data["cross_filter_direction"]
    if "is_active" in relationship_data:
        relationship.is_active = relationship_data["is_active"]
    
    relationship.status = "validated"
    
    await db.commit()
    
    return {"message": "Relación actualizada exitosamente"}

@router.post("/projects/{project_id}/relationships")
async def create_relationship(
    project_id: int,
    relationship_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    current_admin = Depends(verify_admin_credentials)
):
    """Crea una nueva relación manualmente"""
    
    # Validar que las tablas existan
    parent_result = await db.execute(
        select(PowerBITable).filter(
            PowerBITable.project_id == project_id,
            PowerBITable.id == relationship_data["parent_table_id"]
        )
    )
    parent_table = parent_result.scalar_one_or_none()
    
    child_result = await db.execute(
        select(PowerBITable).filter(
            PowerBITable.project_id == project_id,
            PowerBITable.id == relationship_data["child_table_id"]
        )
    )
    child_table = child_result.scalar_one_or_none()
    
    if not parent_table or not child_table:
        raise HTTPException(status_code=400, detail="Tablas padre o hija no encontradas")
    
    # Crear relación
    new_relationship = PowerBIRelationship(
        project_id=project_id,
        parent_table_id=relationship_data["parent_table_id"],
        child_table_id=relationship_data["child_table_id"],
        parent_column=relationship_data["parent_column"],
        child_column=relationship_data["child_column"],
        cardinality=relationship_data.get("cardinality", "1:N"),
        cross_filter_direction=relationship_data.get("cross_filter_direction", "single"),
        is_active=relationship_data.get("is_active", True),
        status="manual"
    )
    
    db.add(new_relationship)
    await db.commit()
    
    return {"message": "Relación creada exitosamente", "relationship_id": new_relationship.id}

@router.delete("/projects/{project_id}/relationships/{relationship_id}")
async def delete_relationship(
    project_id: int,
    relationship_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_admin = Depends(verify_admin_credentials)
):
    """Elimina una relación"""
    
    result = await db.execute(
        select(PowerBIRelationship).filter(
            PowerBIRelationship.id == relationship_id,
            PowerBIRelationship.project_id == project_id
        )
    )
    relationship = result.scalar_one_or_none()
    
    if not relationship:
        raise HTTPException(status_code=404, detail="Relación no encontrada")
    
    await db.delete(relationship)
    await db.commit()
    
    return {"message": "Relación eliminada exitosamente"}

@router.post("/projects/{project_id}/export")
async def export_project(
    project_id: int,
    export_config: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
    current_admin = Depends(verify_admin_credentials)
):
    """Exporta un proyecto a Power BI"""
    
    result = await db.execute(select(PowerBIProject).filter(PowerBIProject.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    if project.status != "ready":
        raise HTTPException(status_code=400, detail="El proyecto debe estar en estado 'ready' para exportar")
    
    export_type = export_config.get("export_type", "pbit")
    if export_type not in ["pbit", "xmla", "json"]:
        raise HTTPException(status_code=400, detail="Tipo de exportación no válido")
    
    # Crear registro de exportación
    export_record = PowerBIExport(
        project_id=project_id,
        export_type=export_type,
        export_status="processing",
        export_config=export_config
    )
    db.add(export_record)
    await db.commit()
    await db.refresh(export_record)
    
    # Procesar exportación en segundo plano
    background_tasks.add_task(
        export_project_task, 
        project_id, 
        export_record.id, 
        export_config
    )
    
    return {
        "export_id": export_record.id,
        "status": "processing",
        "message": f"Iniciando exportación {export_type.upper()}..."
    }

async def export_project_task(
    project_id: int, 
    export_id: int, 
    export_config: Dict[str, Any]
):
    """Tarea en segundo plano para exportar proyecto"""
    try:
        from core.database import db_manager
        async for db in db_manager.get_postgres_session():
            # Obtener proyecto y datos
            project_result = await db.execute(select(PowerBIProject).filter(PowerBIProject.id == project_id))
            project = project_result.scalar_one_or_none()
            
            export_result = await db.execute(select(PowerBIExport).filter(PowerBIExport.id == export_id))
            export_record = export_result.scalar_one_or_none()
            
            if not project or not export_record:
                return
            
            # Preparar metadatos para exportación
            tables_metadata = {}
            relationships = []
            
            for table in project.tables:
                # Convertir a formato esperado por el exportador
                columns_data = []
                for col in table.columns:
                    columns_data.append({
                        "column_name": col.column_name,
                        "friendly_name": col.friendly_name,
                        "data_type": col.data_type,
                        "is_key": col.is_key,
                        "is_nullable": col.is_nullable,
                        "description": col.description,
                        "sort_order": col.sort_order,
                        "is_visible": col.is_visible
                    })
                
                from models.parquet_processor import TableMetadata
                table_meta = TableMetadata(
                    table_name=table.table_name,
                    friendly_name=table.friendly_name,
                    columns=columns_data,
                    relationships=[],
                    row_count=table.row_count,
                    file_size=table.file_size
                )
                tables_metadata[table.table_name] = table_meta
            
            # Preparar relaciones
            from models.parquet_processor import RelationshipMetadata
            for rel in project.relationships:
                if rel.is_active:
                    rel_meta = RelationshipMetadata(
                        parent_table=rel.parent_table.table_name,
                        child_table=rel.child_table.table_name,
                        parent_column=rel.parent_column,
                        child_column=rel.child_column,
                        cardinality=rel.cardinality,
                        cross_filter_direction=rel.cross_filter_direction,
                        is_active=rel.is_active
                    )
                    relationships.append(rel_meta)
            
            # Crear exportador
            exporter = PowerBIExporter(tables_metadata, relationships)
            
            # Generar archivo de salida
            export_filename = f"{project.name}_{export_config['export_type']}_{export_record.id}"
            if export_config['export_type'] == 'pbit':
                export_filename += '.pbit'
            elif export_config['export_type'] == 'json':
                export_filename += '.json'
            
            output_path = os.path.join(POWERBI_EXPORT_DIR, export_filename)
            
            # Exportar
            result = exporter.export_model(
                project.name, 
                export_config['export_type'], 
                output_path
            )
            
            if result["status"] == "success":
                export_record.export_status = "success"
                export_record.file_path = output_path
            else:
                export_record.export_status = "error"
                export_record.error_message = result.get("error", "Error desconocido")
            
            await db.commit()
            
            logger.info(f"Exportación {export_id} completada: {result['status']}")
            break
        
    except Exception as e:
        logger.error(f"Error en exportación {export_id}: {str(e)}")
        async for db in db_manager.get_postgres_session():
            export_result = await db.execute(select(PowerBIExport).filter(PowerBIExport.id == export_id))
            export_record = export_result.scalar_one_or_none()
            if export_record:
                export_record.export_status = "error"
                export_record.error_message = str(e)
                await db.commit()
            break

@router.get("/projects/{project_id}/exports")
async def get_project_exports(
    project_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_admin = Depends(verify_admin_credentials)
):
    """Obtiene todas las exportaciones de un proyecto"""
    
    result = await db.execute(
        select(PowerBIExport)
        .filter(PowerBIExport.project_id == project_id)
        .order_by(PowerBIExport.created_at.desc())
    )
    exports = result.scalars().all()
    
    return [{
        "id": export.id,
        "export_type": export.export_type,
        "export_status": export.export_status,
        "created_at": export.created_at,
        "file_path": export.file_path,
        "error_message": export.error_message,
        "has_file": bool(export.file_path and os.path.exists(export.file_path))
    } for export in exports]

@router.get("/exports/{export_id}/download")
async def download_export(
    export_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_admin = Depends(verify_admin_credentials)
):
    """Descarga un archivo exportado"""
    
    result = await db.execute(select(PowerBIExport).filter(PowerBIExport.id == export_id))
    export = result.scalar_one_or_none()
    
    if not export:
        raise HTTPException(status_code=404, detail="Exportación no encontrada")
    
    if export.export_status != "success" or not export.file_path:
        raise HTTPException(status_code=400, detail="Exportación no disponible para descarga")
    
    if not os.path.exists(export.file_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    filename = os.path.basename(export.file_path)
    return FileResponse(
        export.file_path,
        filename=filename,
        media_type='application/octet-stream'
    )

@router.get("/projects/{project_id}/relationships/diagram")
async def get_relationships_diagram(
    project_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_admin = Depends(verify_admin_credentials)
):
    """Obtiene datos para el diagrama de relaciones"""
    
    result = await db.execute(select(PowerBIProject).filter(PowerBIProject.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Preparar nodos (tablas)
    nodes = []
    for table in project.tables:
        node = {
            "id": table.id,
            "label": table.friendly_name or table.table_name,
            "table_name": table.table_name,
            "row_count": table.row_count,
            "columns": [{
                "name": col.column_name,
                "friendly_name": col.friendly_name,
                "data_type": col.data_type,
                "is_key": col.is_key
            } for col in table.columns],
            "x": 0,  # Posición será calculada por el frontend
            "y": 0
        }
        nodes.append(node)
    
    # Preparar aristas (relaciones)
    edges = []
    for rel in project.relationships:
        if rel.is_active:
            edge = {
                "id": rel.id,
                "source": rel.parent_table_id,
                "target": rel.child_table_id,
                "source_column": rel.parent_column,
                "target_column": rel.child_column,
                "cardinality": rel.cardinality,
                "cross_filter_direction": rel.cross_filter_direction,
                "status": rel.status,
                "label": f"{rel.parent_column} → {rel.child_column}"
            }
            edges.append(edge)
    
    return {
        "nodes": nodes,
        "edges": edges,
        "project_name": project.name
    }

@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_admin = Depends(verify_admin_credentials)
):
    """Elimina un proyecto y todos sus archivos asociados"""
    
    result = await db.execute(select(PowerBIProject).filter(PowerBIProject.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    try:
        # Eliminar archivos del proyecto
        project_dir = os.path.join(POWERBI_UPLOAD_DIR, str(project_id))
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir)
        
        # Eliminar archivos de exportación
        exports_result = await db.execute(select(PowerBIExport).filter(PowerBIExport.project_id == project_id))
        exports = exports_result.scalars().all()
        
        for export in exports:
            if export.file_path and os.path.exists(export.file_path):
                os.remove(export.file_path)
        
        # Eliminar proyecto de la base de datos (cascade eliminará tablas, columnas, etc.)
        await db.delete(project)
        await db.commit()
        
        return {"message": "Proyecto eliminado exitosamente"}
        
    except Exception as e:
        logger.error(f"Error eliminando proyecto {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error eliminando proyecto")

@router.post("/projects/{project_id}/validate")
async def validate_project_relationships(
    project_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_admin = Depends(verify_admin_credentials)
):
    """Valida las relaciones de un proyecto"""
    
    result = await db.execute(select(PowerBIProject).filter(PowerBIProject.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    validation_results = []
    
    for relationship in project.relationships:
        validation = {
            "relationship_id": relationship.id,
            "parent_table": relationship.parent_table.friendly_name,
            "child_table": relationship.child_table.friendly_name,
            "parent_column": relationship.parent_column,
            "child_column": relationship.child_column,
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Verificar que las columnas existan
        parent_columns = [col.column_name for col in relationship.parent_table.columns]
        if relationship.parent_column not in parent_columns:
            validation["is_valid"] = False
            validation["errors"].append(f"Columna '{relationship.parent_column}' no existe en tabla padre")
        
        child_columns = [col.column_name for col in relationship.child_table.columns]  
        if relationship.child_column not in child_columns:
            validation["is_valid"] = False
            validation["errors"].append(f"Columna '{relationship.child_column}' no existe en tabla hija")
        
        # Actualizar estado de la relación
        if validation["is_valid"]:
            relationship.status = "validated"
            relationship.validation_message = None
        else:
            relationship.status = "error"
            relationship.validation_message = "; ".join(validation["errors"])
        
        validation_results.append(validation)
    
    await db.commit()
    
    valid_count = sum(1 for v in validation_results if v["is_valid"])
    
    return {
        "total_relationships": len(validation_results),
        "valid_relationships": valid_count,
        "invalid_relationships": len(validation_results) - valid_count,
        "validation_details": validation_results
    }