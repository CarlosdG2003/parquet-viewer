/**
 * API Client - Centraliza todas las llamadas al backend
 */
class ApiClient {
    constructor() {
        this.baseUrl = window.location.origin;
    }

    /**
     * Realiza una petición HTTP genérica
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    }

    /**
     * Obtiene todos los archivos/catálogos con datos combinados (DuckDB + PostgreSQL)
     */
    async getFiles(filters = {}) {
        let endpoint = '/files';
        const params = new URLSearchParams();
        
        if (filters.search) params.append('search', filters.search);
        if (filters.responsible) params.append('responsible', filters.responsible);
        if (filters.permissions) params.append('permissions', filters.permissions);
        if (filters.tags && filters.tags.length > 0) {
            params.append('tags', filters.tags.join(','));
        }
        
        if (params.toString()) {
            endpoint += `?${params.toString()}`;
        }
        
        return this.request(endpoint);
    }

    /**
     * Obtiene información combinada de un archivo específico
     */
    async getFileInfo(filename) {
        return this.request(`/files/${filename}/info`);
    }

    /**
     * Obtiene metadatos específicos de un archivo (solo PostgreSQL)
     */
    async getFileMetadata(filename) {
        try {
            return await this.request(`/metadata/${filename}`);
        } catch (error) {
            console.warn(`Metadata not available for ${filename}`);
            return null;
        }
    }

    /**
     * Crea nuevos metadatos para un archivo
     */
    async createFileMetadata(metadata) {
        return this.request('/metadata', {
            method: 'POST',
            body: JSON.stringify(metadata)
        });
    }

    /**
     * Actualiza metadatos de un archivo
     */
    async updateFileMetadata(filename, metadata, changedBy = 'user') {
        const endpoint = `/metadata/${filename}?changed_by=${encodeURIComponent(changedBy)}`;
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(metadata)
        });
    }

    /**
     * Elimina metadatos de un archivo
     */
    async deleteFileMetadata(filename) {
        return this.request(`/metadata/${filename}`, {
            method: 'DELETE'
        });
    }

    /**
     * Obtiene historial de cambios de metadatos
     */
    async getFileMetadataHistory(filename) {
        return this.request(`/metadata/${filename}/history`);
    }

    /**
     * Obtiene filtros únicos para el frontend
     */
    async getUniqueResponsibles() {
        return this.request('/metadata/filters/responsibles');
    }

    async getUniqueTags() {
        return this.request('/metadata/filters/tags');
    }

    /**
     * Sincroniza estadísticas técnicas de un archivo
     */
    async syncFileStats(filename) {
        return this.request(`/sync/file/${filename}`, {
            method: 'POST'
        });
    }

    /**
     * Sincroniza estadísticas de todos los archivos
     */
    async syncAllFilesStats() {
        return this.request('/sync/all-files', {
            method: 'POST'
        });
    }

    /**
     * Obtiene datos paginados de un archivo (versión básica)
     */
    async getFileData(filename, options = {}) {
        const {
            page = 1,
            pageSize = 50,
            columns = null
        } = options;

        let endpoint = `/files/${filename}/data?page=${page}&page_size=${pageSize}`;
        
        if (columns && columns.length > 0) {
            endpoint += `&columns=${columns.join(',')}`;
        }

        return this.request(endpoint);
    }

    /**
     * Obtiene datos paginados de un archivo con funcionalidades mejoradas
     */
    async getFileDataEnhanced(filename, options = {}) {
        const {
            page = 1,
            page_size = 50,
            columns = null,
            search = '',
            sort_column = null,
            sort_order = 'asc'
        } = options;

        const params = new URLSearchParams();
        params.append('page', page);
        params.append('page_size', page_size);
        
        if (columns) {
            params.append('columns', columns);
        }
        
        if (search && search.trim()) {
            params.append('search', search.trim());
        }
        
        if (sort_column) {
            params.append('sort_column', sort_column);
            params.append('sort_order', sort_order);
        }

        return this.request(`/files/${filename}/data/enhanced?${params.toString()}`);
    }

    /**
     * Obtiene el esquema de un archivo (versión básica)
     */
    async getFileSchema(filename) {
        return this.request(`/files/${filename}/schema`);
    }

    /**
     * Obtiene el esquema de un archivo con metadatos mejorados
     */
    async getFileSchemaEnhanced(filename) {
        return this.request(`/files/${filename}/schema/enhanced`);
    }

    /**
     * Obtiene estadísticas de un archivo
     */
    async getFileStats(filename) {
        return this.request(`/files/${filename}/stats`);
    }

    /**
     * Obtiene información de columnas para crear gráficas manualmente
     */
    async getFileColumnsForCharts(filename) {
        return this.request(`/files/${filename}/charts/columns`);
    }

    /**
     * Genera una gráfica personalizada
     */
    async generateCustomChart(filename, chartConfig) {
        return this.request(`/files/${filename}/charts/custom`, {
            method: 'POST',
            body: JSON.stringify(chartConfig)
        });
    }

    // === NUEVOS MÉTODOS PARA ADMINISTRACIÓN DE COLUMNAS ===

    /**
     * Obtiene metadatos de columnas para administración (requiere autenticación de admin)
     */
    async getFileColumnsAdmin(filename) {
        return this.request(`/admin/files/${filename}/columns`);
    }

    /**
     * Actualiza metadatos de una columna específica
     */
    async updateColumnMetadata(filename, columnName, updates) {
        return this.request(`/admin/files/${filename}/columns/${columnName}`, {
            method: 'PUT',
            body: JSON.stringify(updates)
        });
    }

    /**
     * Actualiza metadatos de múltiples columnas
     */
    async bulkUpdateColumnsMetadata(filename, columnsUpdates) {
        return this.request(`/admin/files/${filename}/columns/bulk-update`, {
            method: 'POST',
            body: JSON.stringify(columnsUpdates)
        });
    }

    /**
     * Sincroniza metadatos de columnas con el esquema del archivo
     */
    async syncFileColumnsMetadata(filename) {
        return this.request(`/admin/files/${filename}/columns/sync`, {
            method: 'POST'
        });
    }

    /**
     * Obtiene esquema de visualización con nombres personalizados
     */
    async getColumnsDisplaySchema(filename) {
        return this.request(`/admin/files/${filename}/columns/display-schema`);
    }

    /**
     * Resetea metadatos de una columna
     */
    async resetColumnMetadata(filename, columnName) {
        return this.request(`/admin/files/${filename}/columns/${columnName}/reset`, {
            method: 'POST'
        });
    }

    /**
     * Exporta configuración de columnas
     */
    async exportColumnsConfig(filename) {
        return this.request(`/admin/files/${filename}/columns/export`);
    }

    /**
     * Importa configuración de columnas
     */
    async importColumnsConfig(filename, configData) {
        return this.request(`/admin/files/${filename}/columns/import`, {
            method: 'POST',
            body: JSON.stringify(configData)
        });
    }

    /**
     * Vista previa con nombres personalizados
     */
    async previewFileWithCustomNames(filename, limit = 20) {
        return this.request(`/admin/files/${filename}/preview-with-custom-names?limit=${limit}`);
    }

    // === MÉTODOS DE ADMINISTRACIÓN GENERAL ===

    /**
     * Obtiene estadísticas del dashboard de admin
     */
    async getAdminDashboardStats() {
        return this.request('/admin/dashboard');
    }

    /**
     * Obtiene archivos sin metadatos
     */
    async getFilesWithoutMetadata() {
        return this.request('/admin/files-without-metadata');
    }

    /**
     * Obtiene resumen de metadatos para admin
     */
    async getMetadataSummaryForAdmin(filters = {}) {
        const params = new URLSearchParams();
        
        if (filters.search) params.append('search', filters.search);
        if (filters.responsible) params.append('responsible', filters.responsible);
        if (filters.permissions) params.append('permissions', filters.permissions);
        
        const queryString = params.toString();
        const endpoint = `/admin/metadata${queryString ? '?' + queryString : ''}`;
        
        return this.request(endpoint);
    }

    /**
     * Obtiene opciones para filtros de admin
     */
    async getAdminFilterOptions() {
        return this.request('/admin/filter-options');
    }

    /**
     * Obtiene información detallada de archivo para admin
     */
    async getFileMetadataForAdmin(filename) {
        return this.request(`/admin/metadata/${filename}`);
    }

    /**
     * Crea metadatos como admin
     */
    async createMetadataAsAdmin(metadata) {
        return this.request('/admin/metadata', {
            method: 'POST',
            body: JSON.stringify(metadata)
        });
    }

    /**
     * Actualiza metadatos como admin
     */
    async updateMetadataAsAdmin(filename, metadata) {
        return this.request(`/admin/metadata/${filename}`, {
            method: 'PUT',
            body: JSON.stringify(metadata)
        });
    }

    /**
     * Elimina metadatos como admin
     */
    async deleteMetadataAsAdmin(filename) {
        return this.request(`/admin/metadata/${filename}`, {
            method: 'DELETE'
        });
    }

    /**
     * Obtiene información del usuario admin actual
     */
    async getCurrentAdminUser() {
        return this.request('/admin/user-info');
    }
}

// Crear instancia global
window.apiClient = new ApiClient();