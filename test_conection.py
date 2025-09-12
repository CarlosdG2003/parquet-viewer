"""
Script para testear las conexiones a PostgreSQL y DuckDB
Ejecutar: python test_connections.py
"""

import asyncio
import os
from core.database import db_manager, AsyncSessionLocal
from models.database_models import FileMetadata
from sqlalchemy import text

async def test_postgres_connection():
    """Testea la conexión a PostgreSQL"""
    print("Testeando PostgreSQL...")
    
    try:
        async with AsyncSessionLocal() as session:
            # Test de conexión básica
            result = await session.execute(text("SELECT 1"))
            print("✅ PostgreSQL: Conexión exitosa")
            
            # Test de tablas
            result = await session.execute(text("SELECT COUNT(*) FROM file_metadata"))
            count = result.scalar()
            print(f"✅ PostgreSQL: {count} registros en file_metadata")
            
            # Test de datos de ejemplo
            result = await session.execute(text("SELECT title FROM file_metadata LIMIT 3"))
            titles = result.fetchall()
            print("✅ PostgreSQL: Datos de ejemplo encontrados:")
            for title in titles:
                print(f"   - {title[0]}")
                
    except Exception as e:
        print(f"❌ PostgreSQL Error: {e}")
        return False
    
    return True

def test_duckdb_connection():
    """Testea la conexión a DuckDB"""
    print("\nTesteando DuckDB...")
    
    try:
        conn = db_manager.get_duckdb_connection()
        
        # Test básico
        result = conn.execute("SELECT 1").fetchone()
        print("✅ DuckDB: Conexión exitosa")
        
        # Test con archivos parquet (si existen)
        parquet_dir = "./parquet_files"
        if os.path.exists(parquet_dir):
            parquet_files = [f for f in os.listdir(parquet_dir) if f.endswith('.parquet')]
            print(f"✅ DuckDB: {len(parquet_files)} archivos .parquet encontrados")
            
            if parquet_files:
                # Test de lectura de un archivo
                test_file = os.path.join(parquet_dir, parquet_files[0])
                try:
                    result = conn.execute(f"SELECT COUNT(*) FROM '{test_file}'").fetchone()
                    print(f"✅ DuckDB: Archivo {parquet_files[0]} tiene {result[0]} filas")
                except Exception as e:
                    print(f"⚠️  DuckDB: No se pudo leer {parquet_files[0]}: {e}")
        else:
            print("ℹ️  DuckDB: Carpeta parquet_files no encontrada")
            
    except Exception as e:
        print(f"❌ DuckDB Error: {e}")
        return False
    
    return True

async def main():
    """Función principal de testing"""
    print("=== Test de Conexiones de Base de Datos ===\n")
    
    # Variables de entorno
    print("Variables de entorno:")
    print(f"DATABASE_URL: {os.getenv('DATABASE_URL', 'No definida')}")
    print(f"POSTGRES_HOST: {os.getenv('POSTGRES_HOST', 'localhost')}")
    print(f"POSTGRES_PORT: {os.getenv('POSTGRES_PORT', '5432')}")
    print()
    
    # Tests
    postgres_ok = await test_postgres_connection()
    duckdb_ok = test_duckdb_connection()
    
    print("\n=== Resumen ===")
    if postgres_ok and duckdb_ok:
        print("🎉 Todas las conexiones funcionan correctamente!")
        print("Ready para continuar con Fase 3")
    else:
        print("⚠️  Hay problemas con las conexiones")
        print("Revisa la configuración de Docker y las variables de entorno")

if __name__ == "__main__":
    asyncio.run(main())