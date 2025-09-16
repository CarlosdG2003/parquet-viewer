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

CREATE INDEX IF NOT EXISTS ix_column_metadata_filename ON column_metadata(filename);
CREATE INDEX IF NOT EXISTS ix_column_metadata_filename_column ON column_metadata(filename, original_column_name);

DROP TRIGGER IF EXISTS update_column_metadata_updated_at ON column_metadata;
CREATE TRIGGER update_column_metadata_updated_at 
    BEFORE UPDATE ON column_metadata 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Dar permisos al usuario
GRANT ALL PRIVILEGES ON TABLE column_metadata TO parquet_user;
GRANT ALL PRIVILEGES ON SEQUENCE column_metadata_id_seq TO parquet_user;