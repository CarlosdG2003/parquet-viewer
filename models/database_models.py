from sqlalchemy import Column, Boolean, Index, UniqueConstraint, Integer, String, Text, TIMESTAMP, DECIMAL, BIGINT, ForeignKey, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.database import Base
from datetime import datetime
from typing import List, Optional
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