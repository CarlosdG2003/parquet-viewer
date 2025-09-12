-- Inicialización de la base de datos PostgreSQL para Parquet Viewer
-- Este script se ejecuta automáticamente al crear el contenedor

-- Crear extensión para arrays si no existe
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

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
    file_size_mb DECIMAL(10,2),
    row_count BIGINT,
    column_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de historial de cambios (auditoria)
CREATE TABLE IF NOT EXISTS metadata_history (
    id SERIAL PRIMARY KEY,
    file_id INTEGER REFERENCES file_metadata(id) ON DELETE CASCADE,
    field_changed VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by VARCHAR(255),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para optimizar consultas
CREATE INDEX IF NOT EXISTS idx_file_metadata_filename ON file_metadata(filename);
CREATE INDEX IF NOT EXISTS idx_file_metadata_responsible ON file_metadata(responsible);
CREATE INDEX IF NOT EXISTS idx_file_metadata_permissions ON file_metadata(permissions);
CREATE INDEX IF NOT EXISTS idx_file_metadata_tags ON file_metadata USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_metadata_history_file_id ON metadata_history(file_id);
CREATE INDEX IF NOT EXISTS idx_metadata_history_changed_at ON metadata_history(changed_at);

-- Función para actualizar timestamp automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger para actualizar updated_at automáticamente
CREATE TRIGGER update_file_metadata_updated_at 
    BEFORE UPDATE ON file_metadata 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Insertar algunos datos de ejemplo
INSERT INTO file_metadata (
    filename, 
    title, 
    description, 
    responsible, 
    frequency, 
    permissions, 
    tags
) VALUES 
(
    'ventas_retail_2024.parquet',
    'Ventas Retail 2024',
    'Datos de transacciones de ventas del sistema de retail incluyendo productos, precios, cantidades y información del vendedor.',
    'María González',
    'Diario',
    'public',
    ARRAY['ventas', 'retail', 'transacciones', 'productos']
),
(
    'inventario_almacenes.parquet',
    'Inventario Almacenes',
    'Control de stock y movimientos de inventario en todos los almacenes de la compañía con trazabilidad completa.',
    'Carlos Ruiz',
    'Tiempo Real',
    'restricted',
    ARRAY['inventario', 'almacen', 'stock', 'logistica']
),
(
    'datos_financieros_q4.parquet',
    'Datos Financieros Q4',
    'Información financiera consolidada del cuarto trimestre incluyendo P&L, balance y flujo de caja.',
    'Ana Martínez',
    'Trimestral',
    'private',
    ARRAY['financiero', 'contabilidad', 'balance', 'P&L']
)
ON CONFLICT (filename) DO NOTHING;