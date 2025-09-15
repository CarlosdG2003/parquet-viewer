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
     * Obtiene datos paginados de un archivo
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
     * Obtiene el esquema de un archivo
     */
    async getFileSchema(filename) {
        return this.request(`/files/${filename}/schema`);
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
}

// Crear instancia global
window.apiClient = new ApiClient();