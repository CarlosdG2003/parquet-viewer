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
     * Obtiene todos los archivos/catálogos
     */
    async getFiles() {
        return this.request('/files');
    }

    /**
     * Obtiene información de un archivo específico
     */
    async getFileInfo(filename) {
        return this.request(`/files/${filename}/info`);
    }

    /**
     * Obtiene metadatos de un archivo (opcional, puede fallar)
     */
    async getFileMetadata(filename) {
        try {
            return await this.request(`/files/${filename}/metadata`);
        } catch (error) {
            console.warn(`Metadata not available for ${filename}`);
            return null;
        }
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
}

// Crear instancia global
window.apiClient = new ApiClient();