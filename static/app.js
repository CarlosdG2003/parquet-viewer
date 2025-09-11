/**
 * Parquet Viewer - Aplicación Principal Modular
 * Orquesta las páginas y componentes de la aplicación
 */
class ParquetViewerApp {
    constructor() {
        this.catalogListPage = null;
        this.catalogDetailPage = null;
        this.currentView = 'list';
        
        this.init();
    }

    /**
     * Inicializa la aplicación
     */
    init() {
        this._validateDependencies();
        this._initializePages();
        this._setupNavigation();
        this._startApplication();
    }

    /**
     * Valida que todas las dependencias estén cargadas
     */
    _validateDependencies() {
        const requiredClasses = [
            'CatalogCard', 'SearchBar', 'DataTable', 'CatalogListPage', 'CatalogDetailPage'
        ];

        // Verificar objetos globales
        const requiredGlobals = ['apiClient', 'DOM'];
        const missingGlobals = requiredGlobals.filter(name => !window[name]);
        
        const missing = requiredClasses.filter(className => !window[className]);
        const allMissing = [...missing, ...missingGlobals];
        
        if (allMissing.length > 0) {
            console.error('Dependencias faltantes:', allMissing);
            throw new Error(`Dependencias requeridas no encontradas: ${allMissing.join(', ')}`);
        }

        console.log(' Todas las dependencias cargadas correctamente');
    }

    /**
     * Inicializa las páginas de la aplicación
     */
    _initializePages() {
        try {
            // Inicializar página de lista de catálogos
            this.catalogListPage = new CatalogListPage();
            this.catalogListPage.onCatalogSelectCallback((catalog) => {
                this._navigateToCatalogDetail(catalog);
            });

            // Inicializar página de detalle de catálogo
            this.catalogDetailPage = new CatalogDetailPage();
            this.catalogDetailPage.onBack(() => {
                this._navigateToCatalogList();
            });

            console.log(' Páginas inicializadas correctamente');
            
        } catch (error) {
            console.error('Error inicializando páginas:', error);
            this._showApplicationError('Error al inicializar la aplicación');
        }
    }

    /**
     * Configura la navegación entre páginas
     */
    _setupNavigation() {
        // Manejar botón de volver (si existe en el DOM)
        const backButton = DOM.$('#backToCatalogs');
        if (backButton) {
            backButton.addEventListener('click', () => {
                this._navigateToCatalogList();
            });
        }

        // Manejar navegación del navegador (opcional)
        window.addEventListener('popstate', (event) => {
            this._handleBrowserNavigation(event);
        });
    }

    /**
     * Inicia la aplicación mostrando la vista inicial
     */
    _startApplication() {
        try {
            this._navigateToCatalogList();
            console.log(' Aplicación iniciada correctamente');
            
        } catch (error) {
            console.error('Error al iniciar aplicación:', error);
            this._showApplicationError('Error al iniciar la aplicación');
        }
    }

    /**
     * Navega a la lista de catálogos
     */
    _navigateToCatalogList() {
        try {
            // Ocultar vista de detalle
            this.catalogDetailPage.hide();
            
            // Mostrar vista de lista
            this.catalogListPage.show();
            
            // Actualizar estado
            this.currentView = 'list';
            
            // Opcional: actualizar URL sin recargar
            this._updateURL('/');
            
        } catch (error) {
            console.error('Error navegando a lista:', error);
        }
    }

    /**
     * Navega al detalle de un catálogo
     */
    _navigateToCatalogDetail(catalog) {
        try {
            // Ocultar vista de lista
            this.catalogListPage.hide();
            
            // Abrir catálogo en vista de detalle
            this.catalogDetailPage.openCatalog(catalog);
            
            // Actualizar estado
            this.currentView = 'detail';
            
            // Opcional: actualizar URL sin recargar
            this._updateURL(`/catalog/${catalog.name}`);
            
        } catch (error) {
            console.error('Error navegando a detalle:', error);
            this._showApplicationError('Error al abrir el catálogo');
        }
    }

    /**
     * Maneja la navegación del navegador (back/forward)
     */
    _handleBrowserNavigation(event) {
        const path = window.location.pathname;
        
        if (path === '/' || path === '') {
            this._navigateToCatalogList();
        } else if (path.startsWith('/catalog/')) {
            // Extraer nombre del catálogo de la URL
            const catalogName = path.split('/catalog/')[1];
            const catalog = this.catalogListPage.getCatalogByName(catalogName);
            
            if (catalog) {
                this._navigateToCatalogDetail(catalog);
            } else {
                this._navigateToCatalogList();
            }
        }
    }

    /**
     * Actualiza la URL sin recargar la página
     */
    _updateURL(path) {
        if (window.history && window.history.pushState) {
            window.history.pushState({ path }, '', path);
        }
    }

    /**
     * Muestra error crítico de la aplicación
     */
    _showApplicationError(message) {
        const errorContainer = DOM.$('#catalogsGrid') || DOM.$('#dataTableContainer') || document.body;
        
        if (errorContainer) {
            errorContainer.innerHTML = `
                <div class="error-state">
                    <h3>Error de Aplicación</h3>
                    <p>${message}</p>
                    <button onclick="window.location.reload()" style="margin-top: 10px; padding: 8px 16px;">
                        Recargar Aplicación
                    </button>
                </div>
            `;
        }
    }

    /**
     * Refresca los datos de la aplicación
     */
    async refresh() {
        try {
            if (this.currentView === 'list') {
                await this.catalogListPage.refresh();
            }
            // El detalle se refresca automáticamente al abrirse
            
        } catch (error) {
            console.error('Error refrescando datos:', error);
        }
    }

    /**
     * Obtiene el estado actual de la aplicación
     */
    getState() {
        return {
            currentView: this.currentView,
            currentCatalog: this.catalogDetailPage.currentCatalog,
            catalogsCount: this.catalogListPage.allCatalogs.length,
            filteredCount: this.catalogListPage.filteredCatalogs.length
        };
    }

    /**
     * Limpia el estado de la aplicación
     */
    cleanup() {
        if (this.catalogDetailPage) {
            this.catalogDetailPage.clear();
        }
        
        if (this.catalogListPage) {
            this.catalogListPage.clearFilters();
        }
    }

    /**
     * Manejo de errores global
     */
    _setupErrorHandling() {
        window.addEventListener('error', (event) => {
            console.error('Error global:', event.error);
        });

        window.addEventListener('unhandledrejection', (event) => {
            console.error('Promise rechazada:', event.reason);
        });
    }
}

/**
 * Inicialización de la aplicación cuando el DOM esté listo
 */
document.addEventListener('DOMContentLoaded', () => {
    try {
        // Crear instancia global de la aplicación
        window.parquetViewerApp = new ParquetViewerApp();
        
        // Configurar manejo de errores global
        window.parquetViewerApp._setupErrorHandling();
        
        console.log(' Parquet Viewer iniciado correctamente');
        
    } catch (error) {
        console.error(' Error crítico al iniciar la aplicación:', error);
        
        // Mostrar error en la página
        document.body.innerHTML = `
            <div style="padding: 20px; text-align: center; color: #dc3545;">
                <h2>Error al cargar la aplicación</h2>
                <p>${error.message}</p>
                <button onclick="window.location.reload()" style="padding: 10px 20px; margin-top: 20px;">
                    Recargar Página
                </button>
            </div>
        `;
    }
});

/**
 * Funciones de utilidad global para debugging
 */
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    window.debugApp = () => {
        console.log('Estado de la aplicación:', window.parquetViewerApp?.getState());
        console.log('API Client:', window.apiClient);
        console.log('DOM Utils:', window.DOM);
    };
    
    console.log(' Modo desarrollo: usa debugApp() para inspeccionar el estado');
}