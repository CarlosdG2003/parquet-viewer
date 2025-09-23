from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class PowerBIProject(Base):
    """Proyecto de Power BI que agrupa múltiples tablas y relaciones"""
    __tablename__ = 'power_bi_projects'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String(50), default='draft')  # draft, validated, exported
    
    # Relaciones
    tables = relationship("PowerBITable", back_populates="project", cascade="all, delete-orphan")
    relationships = relationship("PowerBIRelationship", back_populates="project", cascade="all, delete-orphan")

class PowerBITable(Base):
    """Tabla individual en el modelo Power BI"""
    __tablename__ = 'power_bi_tables'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('power_bi_projects.id'), nullable=False)
    table_name = Column(String(255), nullable=False)
    friendly_name = Column(String(255))
    parquet_file_path = Column(String(500), nullable=False)
    row_count = Column(Integer)
    file_size = Column(Integer)  # en bytes
    metadata_source = Column(String(50))  # 'embedded', 'json', 'xml'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    project = relationship("PowerBIProject", back_populates="tables")
    columns = relationship("PowerBIColumn", back_populates="table", cascade="all, delete-orphan")
    
    # Relaciones donde esta tabla participa
    parent_relationships = relationship(
        "PowerBIRelationship", 
        foreign_keys="PowerBIRelationship.parent_table_id",
        back_populates="parent_table"
    )
    child_relationships = relationship(
        "PowerBIRelationship",
        foreign_keys="PowerBIRelationship.child_table_id", 
        back_populates="child_table"
    )

class PowerBIColumn(Base):
    """Columna de una tabla Power BI"""
    __tablename__ = 'power_bi_columns'
    
    id = Column(Integer, primary_key=True)
    table_id = Column(Integer, ForeignKey('power_bi_tables.id'), nullable=False)
    column_name = Column(String(255), nullable=False)
    friendly_name = Column(String(255))
    data_type = Column(String(100), nullable=False)
    is_key = Column(Boolean, default=False)
    is_nullable = Column(Boolean, default=True)
    description = Column(Text)
    format_string = Column(String(255))  # Para fechas, números, etc.
    sort_order = Column(Integer, default=0)
    is_visible = Column(Boolean, default=True)
    
    # Relaciones
    table = relationship("PowerBITable", back_populates="columns")

class PowerBIRelationship(Base):
    """Relación entre tablas Power BI"""
    __tablename__ = 'power_bi_relationships'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('power_bi_projects.id'), nullable=False)
    parent_table_id = Column(Integer, ForeignKey('power_bi_tables.id'), nullable=False)
    child_table_id = Column(Integer, ForeignKey('power_bi_tables.id'), nullable=False)
    parent_column = Column(String(255), nullable=False)
    child_column = Column(String(255), nullable=False)
    cardinality = Column(String(20), nullable=False)  # '1:1', '1:N', 'N:1', 'N:N'
    cross_filter_direction = Column(String(20), default='single')  # 'single', 'both'
    is_active = Column(Boolean, default=True)
    relationship_type = Column(String(50), default='regular')  # 'regular', 'weak'
    status = Column(String(50), default='pending')  # pending, validated, error
    validation_message = Column(Text)
    
    # Relaciones
    project = relationship("PowerBIProject", back_populates="relationships")
    parent_table = relationship(
        "PowerBITable", 
        foreign_keys=[parent_table_id],
        back_populates="parent_relationships"
    )
    child_table = relationship(
        "PowerBITable",
        foreign_keys=[child_table_id],
        back_populates="child_relationships"
    )

class PowerBIExport(Base):
    """Registro de exportaciones realizadas"""
    __tablename__ = 'power_bi_exports'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('power_bi_projects.id'), nullable=False)
    export_type = Column(String(50), nullable=False)  # 'pbit', 'pbix', 'xmla'
    file_path = Column(String(500))
    export_status = Column(String(50), default='pending')  # pending, success, error
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Configuración de exportación
    export_config = Column(JSON)  # Configuración específica para cada tipo de exportación