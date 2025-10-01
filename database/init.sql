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

-- TABLAS PRINCIPALES DE LA APLICACIÓN

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

-- TABLAS PARA POWER BI

-- Tabla de metadatos de columnas para Power BI
CREATE TABLE IF NOT EXISTS powerbi_column_metadata (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    original_column_name VARCHAR(255) NOT NULL,
    friendly_name VARCHAR(255) NOT NULL,
    data_type VARCHAR(100),
    format_string VARCHAR(255),
    description TEXT,
    is_hidden BOOLEAN DEFAULT false,
    is_key BOOLEAN DEFAULT false,
    aggregation_function VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_powerbi_filename_column UNIQUE (filename, original_column_name)
);

-- Tabla de metadatos de tablas para Power BI
CREATE TABLE IF NOT EXISTS powerbi_table_metadata (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) UNIQUE NOT NULL,
    table_name VARCHAR(255) NOT NULL,
    friendly_name VARCHAR(255) NOT NULL,
    description TEXT,
    is_hidden BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de relaciones entre tablas para Power BI
CREATE TABLE IF NOT EXISTS powerbi_relationships (
    id SERIAL PRIMARY KEY,
    project_name VARCHAR(255),
    from_table_id INTEGER NOT NULL REFERENCES powerbi_table_metadata(id) ON DELETE CASCADE,
    to_table_id INTEGER NOT NULL REFERENCES powerbi_table_metadata(id) ON DELETE CASCADE,
    from_column VARCHAR(255) NOT NULL,
    to_column VARCHAR(255) NOT NULL,
    cardinality VARCHAR(20) NOT NULL DEFAULT '1:N',
    cross_filter_direction VARCHAR(20) DEFAULT 'single',
    is_active BOOLEAN DEFAULT true,
    description TEXT,
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (cardinality IN ('1:1', '1:N', 'N:1', 'N:N')),
    CHECK (cross_filter_direction IN ('single', 'both', 'none'))
);

-- Tabla de medidas calculadas para Power BI
CREATE TABLE IF NOT EXISTS powerbi_measures (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    measure_name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    dax_expression TEXT NOT NULL,
    format_string VARCHAR(255),
    description TEXT,
    folder VARCHAR(255),
    is_hidden BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_powerbi_measure UNIQUE (filename, measure_name)
);

-- Tabla de registro de exportaciones a Power BI Service
CREATE TABLE IF NOT EXISTS powerbi_export_log (
    id SERIAL PRIMARY KEY,
    project_name VARCHAR(255) NOT NULL,
    filenames JSONB,
    workspace_id VARCHAR(255),
    dataset_id VARCHAR(255),
    dataset_url TEXT,
    export_status VARCHAR(50) DEFAULT 'processing',
    error_message TEXT,
    tables_count INTEGER,
    relationships_count INTEGER,
    measures_count INTEGER,
    exported_by VARCHAR(255),
    exported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (export_status IN ('processing', 'success', 'error'))
);

-- ÍNDICES PARA MEJORAR RENDIMIENTO

-- Índices de tablas principales
CREATE INDEX IF NOT EXISTS idx_file_metadata_filename ON file_metadata(filename);
CREATE INDEX IF NOT EXISTS idx_file_metadata_responsible ON file_metadata(responsible);
CREATE INDEX IF NOT EXISTS idx_file_metadata_permissions ON file_metadata(permissions);
CREATE INDEX IF NOT EXISTS idx_file_metadata_tags ON file_metadata USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_file_metadata_updated_at ON file_metadata(updated_at);

CREATE INDEX IF NOT EXISTS idx_metadata_history_file_id ON metadata_history(file_id);
CREATE INDEX IF NOT EXISTS idx_metadata_history_changed_at ON metadata_history(changed_at);

CREATE INDEX IF NOT EXISTS ix_column_metadata_filename ON column_metadata(filename);
CREATE INDEX IF NOT EXISTS ix_column_metadata_filename_column ON column_metadata(filename, original_column_name);

-- Índices de tablas Power BI
CREATE INDEX IF NOT EXISTS idx_powerbi_col_filename ON powerbi_column_metadata(filename);
CREATE INDEX IF NOT EXISTS idx_powerbi_col_friendly_name ON powerbi_column_metadata(friendly_name);

CREATE INDEX IF NOT EXISTS idx_powerbi_table_filename ON powerbi_table_metadata(filename);
CREATE INDEX IF NOT EXISTS idx_powerbi_table_name ON powerbi_table_metadata(table_name);

CREATE INDEX IF NOT EXISTS idx_powerbi_rel_project ON powerbi_relationships(project_name);
CREATE INDEX IF NOT EXISTS idx_powerbi_rel_from_table ON powerbi_relationships(from_table_id);
CREATE INDEX IF NOT EXISTS idx_powerbi_rel_to_table ON powerbi_relationships(to_table_id);
CREATE INDEX IF NOT EXISTS idx_powerbi_rel_active ON powerbi_relationships(is_active);

CREATE INDEX IF NOT EXISTS idx_powerbi_measure_filename ON powerbi_measures(filename);
CREATE INDEX IF NOT EXISTS idx_powerbi_measure_name ON powerbi_measures(measure_name);

CREATE INDEX IF NOT EXISTS idx_powerbi_export_project ON powerbi_export_log(project_name);
CREATE INDEX IF NOT EXISTS idx_powerbi_export_status ON powerbi_export_log(export_status);
CREATE INDEX IF NOT EXISTS idx_powerbi_export_date ON powerbi_export_log(exported_at);

-- FUNCIÓN PARA ACTUALIZAR updated_at AUTOMÁTICAMENTE

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- TRIGGERS PARA ACTUALIZAR updated_at

-- Triggers de tablas principales
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

-- Triggers de tablas Power BI
DROP TRIGGER IF EXISTS update_powerbi_column_metadata_updated_at ON powerbi_column_metadata;
CREATE TRIGGER update_powerbi_column_metadata_updated_at 
    BEFORE UPDATE ON powerbi_column_metadata 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_powerbi_table_metadata_updated_at ON powerbi_table_metadata;
CREATE TRIGGER update_powerbi_table_metadata_updated_at 
    BEFORE UPDATE ON powerbi_table_metadata 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_powerbi_relationships_updated_at ON powerbi_relationships;
CREATE TRIGGER update_powerbi_relationships_updated_at 
    BEFORE UPDATE ON powerbi_relationships 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_powerbi_measures_updated_at ON powerbi_measures;
CREATE TRIGGER update_powerbi_measures_updated_at 
    BEFORE UPDATE ON powerbi_measures 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- PERMISOS FINALES

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO parquet_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO parquet_user;

-- COMENTARIOS PARA DOCUMENTACIÓN

COMMENT ON TABLE file_metadata IS 'Metadatos de negocio de archivos Parquet';
COMMENT ON TABLE metadata_history IS 'Historial de cambios en metadatos';
COMMENT ON TABLE column_metadata IS 'Metadatos de columnas para visualización en la aplicación';

COMMENT ON TABLE powerbi_column_metadata IS 'Metadatos de columnas específicos para exportación a Power BI';
COMMENT ON TABLE powerbi_table_metadata IS 'Metadatos de tablas para Power BI (nombres amigables, descripciones)';
COMMENT ON TABLE powerbi_relationships IS 'Relaciones entre tablas para el modelo de datos de Power BI';
COMMENT ON TABLE powerbi_measures IS 'Medidas calculadas DAX para Power BI';
COMMENT ON TABLE powerbi_export_log IS 'Registro de exportaciones realizadas a Power BI Service';

COMMIT;