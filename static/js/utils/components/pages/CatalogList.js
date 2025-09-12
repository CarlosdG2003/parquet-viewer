/**
 * CatalogList Page - Maneja la vista principal de lista de catálogos
 */
class CatalogListPage {
    constructor() {
        this.allCatalogs = [];
        this.filteredCatalogs = [];
        this.searchBar = null;
        this.catalogsGrid = DOM.$('#catalogsGrid');
        this.resultsCount = DOM.$('#resultsCount');
        
        this.onCatalogSelect = null;
        
        this.init();
    }

    /**
     * Inicializa la página
     */
    init() {
        this._initializeSearchBar();
        this.loadCatalogs();
    }

    /**
     * Inicializa la barra de búsqueda
     */
    _initializeSearchBar() {
        this.searchBar = new SearchBar({
            onSearch: (searchTerm) => this._handleSearch(searchTerm),
            onFilterChange: (filters) => this._handleFilterChange(filters),
            debounceDelay: 300
        });
    }

    /**
     * Carga todos los catálogos desde la API
     */
    async loadCatalogs() {
        try {
            this._showLoadingState();
            
            this.allCatalogs = await apiClient.getFiles();
            this.filteredCatalogs = [...this.allCatalogs];
            
            await this._loadFilterOptions();
            this._renderCatalogs();
            this._updateResultsCount();
            
        } catch (error) {
            this._showErrorState('Error al cargar catálogos: ' + error.message);
        }
    }

    /**
     * Carga opciones para filtros desde la API
     */
    async _loadFilterOptions() {
        try {
            const [responsiblesResult, tagsResult] = await Promise.all([
                apiClient.getUniqueResponsibles(),
                apiClient.getUniqueTags()
            ]);
            
            this.searchBar.updateFilterOptions('responsible', responsiblesResult.responsibles);
            // Tags se manejan diferente, se podrían agregar como opciones multi-select
            
        } catch (error) {
            console.warn('Error loading filter options:', error);
        }
    }

    /**
     * Maneja la búsqueda de catálogos usando el backend
     */
    async _handleSearch(searchTerm) {
        try {
            this._showLoadingState();
            
            const filters = this.searchBar._getFilterValues();
            const searchFilters = {
                search: searchTerm.trim() || undefined,
                responsible: filters.responsible || undefined,
                permissions: filters.permissions || undefined
                // Tags se pueden agregar aquí cuando se implemente el selector
            };
            
            // Si no hay filtros, cargar todos
            if (!searchFilters.search && !searchFilters.responsible && !searchFilters.permissions) {
                this.filteredCatalogs = await apiClient.getFiles();
            } else {
                this.filteredCatalogs = await apiClient.getFiles(searchFilters);
            }
            
            this._renderCatalogs();
            this._updateResultsCount();
            
        } catch (error) {
            this._showErrorState('Error en búsqueda: ' + error.message);
        }
    }

    /**
     * Maneja cambios en los filtros usando el backend
     */
    async _handleFilterChange(filters) {
        const searchTerm = this.searchBar.getSearchTerm();
        await this._handleSearch(searchTerm);
    }

    /**
     * Renderiza la lista de catálogos
     */
    _renderCatalogs() {
        if (!this.catalogsGrid) return;

        if (this.filteredCatalogs.length === 0) {
            this._showEmptyState();
            return;
        }

        // Limpiar contenedor
        DOM.clearContainer(this.catalogsGrid);

        // Crear fragment para mejor performance
        const fragment = document.createDocumentFragment();

        // Renderizar cada catálogo
        this.filteredCatalogs.forEach(catalog => {
            const catalogCard = new CatalogCard(catalog, (selectedCatalog) => {
                this._handleCatalogSelect(selectedCatalog);
            });

            fragment.appendChild(catalogCard.render());
        });

        this.catalogsGrid.appendChild(fragment);
    }

    /**
     * Maneja la selección de un catálogo
     */
    _handleCatalogSelect(catalog) {
        if (this.onCatalogSelect) {
            this.onCatalogSelect(catalog);
        }
    }

    /**
     * Actualiza el contador de resultados
     */
    _updateResultsCount() {
        if (this.resultsCount) {
            this.resultsCount.textContent = `Total de catálogos: ${this.filteredCatalogs.length}`;
        }
    }

    /**
     * Estados de la interfaz
     */
    _showLoadingState() {
        DOM.showLoading('#catalogsGrid', 'Cargando catálogos...');
    }

    _showErrorState(message) {
        DOM.showError('#catalogsGrid', message);
    }

    _showEmptyState() {
        const emptyMessage = this.searchBar.getSearchTerm() || this.searchBar.validateFilters()
            ? 'No se encontraron catálogos que coincidan con los criterios de búsqueda'
            : 'No hay catálogos disponibles';

        this.catalogsGrid.innerHTML = `<div class="loading-state">${emptyMessage}</div>`;
    }

    /**
     * Muestra/oculta la página
     */
    show() {
        DOM.show('#catalogListView');
    }

    hide() {
        DOM.hide('#catalogListView');
    }

    /**
     * Refresca los datos
     */
    async refresh() {
        await this.loadCatalogs();
    }

    /**
     * Obtiene el catálogo actual por nombre
     */
    getCatalogByName(filename) {
        return this.allCatalogs.find(catalog => catalog.name === filename);
    }

    /**
     * Limpia búsqueda y filtros
     */
    clearFilters() {
        this.searchBar.clear();
        this.filteredCatalogs = [...this.allCatalogs];
        this._renderCatalogs();
        this._updateResultsCount();
    }

    /**
     * Establece el callback para selección de catálogo
     */
    onCatalogSelectCallback(callback) {
        this.onCatalogSelect = callback;
    }

    /**
     * Obtiene estadísticas de los catálogos
     */
    getStats() {
        return {
            total: this.allCatalogs.length,
            filtered: this.filteredCatalogs.length,
            responsibles: new Set(this.allCatalogs.map(c => c.responsible).filter(Boolean)).size,
            totalRecords: this.allCatalogs.reduce((sum, c) => sum + (c.row_count || 0), 0)
        };
    }
}

window.CatalogListPage = CatalogListPage;