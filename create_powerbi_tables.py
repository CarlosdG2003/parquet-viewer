#!/usr/bin/env python3
"""
Script para crear las tablas de Power BI en PostgreSQL
"""
import os
import sys
from sqlalchemy import create_engine

# Importar directamente los modelos
sys.path.append('/app')
from models.power_bi_models import Base

def create_powerbi_tables():
    """Crea todas las tablas del módulo Power BI"""
    
    # URL de conexión a PostgreSQL (síncrona)
    DATABASE_URL = os.getenv(
        "DATABASE_URL", 
        "postgresql://parquet_user:parquet_pass@localhost:5432/parquet_viewer"
    )
    
    # Si la URL tiene asyncpg, cambiarla por psycopg2
    if '+asyncpg' in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace('+asyncpg', '')
    
    try:
        print("Conectando a la base de datos...")
        engine = create_engine(DATABASE_URL)
        
        print("Creando tablas de Power BI...")
        Base.metadata.create_all(bind=engine)
        
        print("Tablas creadas exitosamente:")
        print("  - power_bi_projects")
        print("  - power_bi_tables") 
        print("  - power_bi_columns")
        print("  - power_bi_relationships")
        print("  - power_bi_exports")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando tablas: {e}")
        return False

if __name__ == "__main__":
    success = create_powerbi_tables()
    if not success:
        sys.exit(1)