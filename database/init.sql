-- Crear base de datos y usuario si no existen
-- Este script debe ejecutarse como superusuario de PostgreSQL

-- Crear usuario si no existe
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'parquet_user') THEN
        CREATE USER parquet_user WITH PASSWORD 'parquet_pass';
    END IF;
END
$$;

-- Crear base de datos si no existe
SELECT 'CREATE DATABASE parquet_viewer OWNER parquet_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'parquet_viewer')\gexec

-- Conectar a la base de datos parquet_viewer
\c parquet_viewer;

-- Dar permisos al usuario
GRANT ALL PRIVILEGES ON DATABASE parquet_viewer TO parquet_user;
GRANT ALL ON SCHEMA public TO parquet_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO parquet_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO parquet_user;

-- Tabla principal de metadatos de archivos
CREATE TABLE IF NOT EXISTS file_metadata (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    responsible VARCHAR(255),
    frequency VARCHAR(100),
    permissions VARCHAR(50) DEFAULT 'public',
    tags TEXT[],
    file_size_mb DECIMAL(10, 2),
    row_count BIGINT,
    column_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de historial de cambios en metadatos
CREATE TABLE IF NOT EXISTS metadata_history (
    id SERIAL PRIMARY KEY,
    file_id INTEGER NOT NULL REFERENCES file_metadata(id) ON DELETE CASCADE,
    field_changed VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by VARCHAR(255),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de metadatos de columnas
CREATE TABLE IF NOT EXISTS column_metadata (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    original_column_name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    description TEXT,
    data_type VARCHAR(100),
    is_visible BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_filename_column UNIQUE (filename, original_column_name)
);

-- Índices para mejorar rendimiento
CREATE INDEX IF NOT EXISTS idx_file_metadata_filename ON file_metadata(filename);
CREATE INDEX IF NOT EXISTS idx_file_metadata_responsible ON file_metadata(responsible);
CREATE INDEX IF NOT EXISTS idx_file_metadata_permissions ON file_metadata(permissions);
CREATE INDEX IF NOT EXISTS idx_file_metadata_tags ON file_metadata USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_file_metadata_updated_at ON file_metadata(updated_at);

CREATE INDEX IF NOT EXISTS idx_metadata_history_file_id ON metadata_history(file_id);
CREATE INDEX IF NOT EXISTS idx_metadata_history_changed_at ON metadata_history(changed_at);

CREATE INDEX IF NOT EXISTS ix_column_metadata_filename ON column_metadata(filename);
CREATE INDEX IF NOT EXISTS ix_column_metadata_filename_column ON column_metadata(filename, original_column_name);

-- Función para actualizar automáticamente updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger para actualizar updated_at automáticamente
DROP TRIGGER IF EXISTS update_file_metadata_updated_at ON file_metadata;
CREATE TRIGGER update_file_metadata_updated_at 
    BEFORE UPDATE ON file_metadata 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_column_metadata_updated_at ON column_metadata;
CREATE TRIGGER update_column_metadata_updated_at 
    BEFORE UPDATE ON column_metadata 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Dar permisos finales al usuario
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO parquet_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO parquet_user;

-- Datos de ejemplo (opcional)
-- INSERT INTO file_metadata (filename, title, description, responsible, frequency, permissions, tags)
-- VALUES 
--     ('sample_data.parquet', 'Datos de Ejemplo', 'Archivo de prueba con datos sintéticos', 'Admin', 'monthly', 'public', ARRAY['ejemplo', 'test']),
--     ('production_data.parquet', 'Datos de Producción', 'Datos reales de minería', 'Data Team', 'daily', 'internal', ARRAY['minería', 'producción']);

COMMIT;