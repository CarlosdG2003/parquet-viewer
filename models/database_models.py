from sqlalchemy import Column, Boolean, Index, UniqueConstraint, Integer, String, Text, TIMESTAMP, DECIMAL, BIGINT, ForeignKey, ARRAY, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.database import Base
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class FileMetadata(Base):
    """Modelo SQLAlchemy para metadatos de archivos"""
    __tablename__ = "file_metadata"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    responsible = Column(String(255), index=True)
    frequency = Column(String(100))
    permissions = Column(String(50), default="public", index=True)
    tags = Column(ARRAY(String), default=list)
    file_size_mb = Column(DECIMAL(10, 2))
    row_count = Column(BIGINT)
    column_count = Column(Integer)
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())

    # Relación con historial
    history = relationship("MetadataHistory", back_populates="file", cascade="all, delete-orphan")

class MetadataHistory(Base):
    """Modelo SQLAlchemy para historial de cambios"""
    __tablename__ = "metadata_history"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("file_metadata.id", ondelete="CASCADE"), nullable=False)
    field_changed = Column(String(100), nullable=False)
    old_value = Column(Text)
    new_value = Column(Text)
    changed_by = Column(String(255))
    changed_at = Column(TIMESTAMP, default=func.now())

    # Relación con archivo
    file = relationship("FileMetadata", back_populates="history")

# Schemas Pydantic para validación de datos

class FileMetadataBase(BaseModel):
    """Schema base para metadatos"""
    filename: str
    title: str
    description: Optional[str] = None
    responsible: Optional[str] = None
    frequency: Optional[str] = None
    permissions: str = "public"
    tags: List[str] = []

class FileMetadataCreate(FileMetadataBase):
    """Schema para crear metadatos"""
    pass

class FileMetadataUpdate(BaseModel):
    """Schema para actualizar metadatos"""
    title: Optional[str] = None
    description: Optional[str] = None
    responsible: Optional[str] = None
    frequency: Optional[str] = None
    permissions: Optional[str] = None
    tags: Optional[List[str]] = None

class FileMetadataResponse(FileMetadataBase):
    """Schema para respuesta de metadatos"""
    id: int
    file_size_mb: Optional[float] = None
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MetadataHistoryResponse(BaseModel):
    """Schema para respuesta de historial"""
    id: int
    field_changed: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_by: Optional[str] = None
    changed_at: datetime

    class Config:
        from_attributes = True

class CombinedFileInfo(BaseModel):
    """Schema combinado: datos técnicos (DuckDB) + metadatos (PostgreSQL)"""
    # Datos técnicos del archivo (DuckDB)
    name: str
    size_bytes: int
    size_mb: float
    modified: str
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    columns: List[dict] = []
    
    # Metadatos del negocio (PostgreSQL)
    id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    responsible: Optional[str] = None
    frequency: Optional[str] = None
    permissions: str = "public"
    tags: List[str] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ColumnMetadata(Base):
    __tablename__ = "column_metadata"
    
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    original_column_name = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    data_type = Column(String(100), nullable=True)
    is_visible = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())
    
    # Índices y restricciones
    __table_args__ = (
        Index('ix_column_metadata_filename', 'filename'),
        Index('ix_column_metadata_filename_column', 'filename', 'original_column_name'),
        UniqueConstraint('filename', 'original_column_name', name='uq_filename_column')
    )

# Modelos Pydantic para la API
class ColumnMetadataBase(BaseModel):
    original_column_name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    data_type: Optional[str] = None
    is_visible: bool = True
    sort_order: int = 0

class ColumnMetadataCreate(ColumnMetadataBase):
    filename: str

class ColumnMetadataUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    is_visible: Optional[bool] = None
    sort_order: Optional[int] = None

class ColumnMetadataResponse(ColumnMetadataBase):
    id: int
    filename: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== MODELOS SQLALCHEMY PARA POWER BI ====================

class PowerBIColumnMetadata(Base):
    """Metadatos específicos de Power BI para columnas"""
    __tablename__ = "powerbi_column_metadata"
    
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False, index=True)
    original_column_name = Column(String(255), nullable=False)
    friendly_name = Column(String(255), nullable=False)
    data_type = Column(String(100))
    format_string = Column(String(255))  # Formato Power BI: "#,##0.00", "dd/mm/yyyy", etc.
    description = Column(Text)
    is_hidden = Column(Boolean, default=False)
    is_key = Column(Boolean, default=False)  # Es clave primaria
    aggregation_function = Column(String(50))  # "SUM", "AVERAGE", "COUNT", etc.
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('ix_powerbi_col_filename', 'filename'),
        UniqueConstraint('filename', 'original_column_name', name='uq_powerbi_filename_column')
    )

class PowerBITableMetadata(Base):
    """Metadatos de tabla para Power BI"""
    __tablename__ = "powerbi_table_metadata"
    
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), unique=True, nullable=False, index=True)
    table_name = Column(String(255), nullable=False)  # Nombre técnico en Power BI
    friendly_name = Column(String(255), nullable=False)  # Nombre amigable
    description = Column(Text)
    is_hidden = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())
    
    # Relación con relaciones donde esta tabla participa
    relationships_as_from = relationship(
        "PowerBIRelationship", 
        foreign_keys="PowerBIRelationship.from_table_id",
        back_populates="from_table"
    )
    relationships_as_to = relationship(
        "PowerBIRelationship",
        foreign_keys="PowerBIRelationship.to_table_id",
        back_populates="to_table"
    )

class PowerBIRelationship(Base):
    """Relaciones entre tablas para Power BI"""
    __tablename__ = "powerbi_relationships"
    
    id = Column(Integer, primary_key=True)
    project_name = Column(String(255), index=True)  # Opcional: agrupar por proyecto
    
    from_table_id = Column(Integer, ForeignKey("powerbi_table_metadata.id", ondelete="CASCADE"), nullable=False)
    to_table_id = Column(Integer, ForeignKey("powerbi_table_metadata.id", ondelete="CASCADE"), nullable=False)
    
    from_column = Column(String(255), nullable=False)
    to_column = Column(String(255), nullable=False)
    
    cardinality = Column(String(20), nullable=False, default="1:N")  # "1:1", "1:N", "N:1", "N:N"
    cross_filter_direction = Column(String(20), default="single")  # "single", "both", "none"
    is_active = Column(Boolean, default=True)
    
    description = Column(Text)
    created_by = Column(String(255))
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())
    
    # Relaciones
    from_table = relationship(
        "PowerBITableMetadata",
        foreign_keys=[from_table_id],
        back_populates="relationships_as_from"
    )
    to_table = relationship(
        "PowerBITableMetadata",
        foreign_keys=[to_table_id],
        back_populates="relationships_as_to"
    )
    
    __table_args__ = (
        Index('ix_powerbi_rel_project', 'project_name'),
        Index('ix_powerbi_rel_from_table', 'from_table_id'),
        Index('ix_powerbi_rel_to_table', 'to_table_id'),
    )

class PowerBIMeasure(Base):
    """Medidas calculadas para Power BI"""
    __tablename__ = "powerbi_measures"
    
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False, index=True)
    measure_name = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    dax_expression = Column(Text, nullable=False)  # Expresión DAX
    format_string = Column(String(255))
    description = Column(Text)
    folder = Column(String(255))  # Carpeta organizativa en Power BI
    is_hidden = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('ix_powerbi_measure_filename', 'filename'),
        UniqueConstraint('filename', 'measure_name', name='uq_powerbi_measure')
    )

class PowerBIExportLog(Base):
    """Registro de exportaciones a Power BI Service"""
    __tablename__ = "powerbi_export_log"
    
    id = Column(Integer, primary_key=True)
    project_name = Column(String(255), nullable=False, index=True)
    filenames = Column(JSON)  # Lista de archivos exportados
    
    workspace_id = Column(String(255))
    dataset_id = Column(String(255))
    dataset_url = Column(Text)
    
    export_status = Column(String(50), default="processing")  # "processing", "success", "error"
    error_message = Column(Text)
    
    tables_count = Column(Integer)
    relationships_count = Column(Integer)
    measures_count = Column(Integer)
    
    exported_by = Column(String(255))
    exported_at = Column(TIMESTAMP, default=func.now())
    
    __table_args__ = (
        Index('ix_powerbi_export_project', 'project_name'),
        Index('ix_powerbi_export_status', 'export_status'),
    )

# ==================== SCHEMAS PYDANTIC PARA POWER BI ====================

class PowerBIColumnMetadataBase(BaseModel):
    original_column_name: str
    friendly_name: str
    data_type: Optional[str] = None
    format_string: Optional[str] = None
    description: Optional[str] = None
    is_hidden: bool = False
    is_key: bool = False
    aggregation_function: Optional[str] = None

class PowerBIColumnMetadataCreate(PowerBIColumnMetadataBase):
    filename: str

class PowerBIColumnMetadataUpdate(BaseModel):
    friendly_name: Optional[str] = None
    data_type: Optional[str] = None
    format_string: Optional[str] = None
    description: Optional[str] = None
    is_hidden: Optional[bool] = None
    is_key: Optional[bool] = None
    aggregation_function: Optional[str] = None

class PowerBIColumnMetadataResponse(PowerBIColumnMetadataBase):
    id: int
    filename: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class PowerBITableMetadataBase(BaseModel):
    table_name: str
    friendly_name: str
    description: Optional[str] = None
    is_hidden: bool = False

class PowerBITableMetadataCreate(PowerBITableMetadataBase):
    filename: str

class PowerBITableMetadataResponse(PowerBITableMetadataBase):
    id: int
    filename: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class PowerBIRelationshipBase(BaseModel):
    from_table_filename: str  # Se usa para encontrar el ID
    to_table_filename: str
    from_column: str
    to_column: str
    cardinality: str = "1:N"
    cross_filter_direction: str = "single"
    is_active: bool = True
    description: Optional[str] = None

class PowerBIRelationshipCreate(PowerBIRelationshipBase):
    project_name: Optional[str] = None
    created_by: Optional[str] = None

class PowerBIRelationshipResponse(BaseModel):
    id: int
    project_name: Optional[str]
    from_table_name: str
    to_table_name: str
    from_column: str
    to_column: str
    cardinality: str
    cross_filter_direction: str
    is_active: bool
    description: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class PowerBIMeasureBase(BaseModel):
    measure_name: str
    display_name: str
    dax_expression: str
    format_string: Optional[str] = None
    description: Optional[str] = None
    folder: Optional[str] = None
    is_hidden: bool = False

class PowerBIMeasureCreate(PowerBIMeasureBase):
    filename: str

class PowerBIMeasureResponse(PowerBIMeasureBase):
    id: int
    filename: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class PowerBIExportRequest(BaseModel):
    """Request para exportar a Power BI Service"""
    project_name: str
    filenames: List[str]
    workspace_id: Optional[str] = None  # Si None, se crea nuevo workspace
    dataset_name: Optional[str] = None

class PowerBIExportResponse(BaseModel):
    """Response de exportación a Power BI"""
    success: bool
    workspace_id: Optional[str]
    dataset_id: Optional[str]
    dataset_url: Optional[str]
    message: str
    tables_count: int
    relationships_count: int
    
class PowerBIExportLogResponse(BaseModel):
    id: int
    project_name: str
    filenames: List[str]
    workspace_id: Optional[str]
    dataset_id: Optional[str]
    dataset_url: Optional[str]
    export_status: str
    error_message: Optional[str]
    tables_count: Optional[int]
    relationships_count: Optional[int]
    measures_count: Optional[int]
    exported_by: Optional[str]
    exported_at: datetime
    
    class Config:
        from_attributes = True

# Schema para extracción de metadatos desde Parquet
class ParquetEmbeddedMetadata(BaseModel):
    """Metadatos extraídos de un archivo Parquet"""
    table_metadata: Optional[PowerBITableMetadataBase] = None
    columns_metadata: List[PowerBIColumnMetadataBase] = []
    relationships: List[Dict[str, Any]] = []  # Relaciones pendientes de resolver IDs
    measures: List[PowerBIMeasureBase] = []