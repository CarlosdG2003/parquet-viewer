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
            
            this._populateFilters();
            this._renderCatalogs();
            this._updateResultsCount();
            
        } catch (error) {
            this._showErrorState('Error al cargar catálogos: ' + error.message);
        }
    }

    /**
     * Maneja la búsqueda de catálogos
     */
    _handleSearch(searchTerm) {
        if (!searchTerm.trim()) {
            this.filteredCatalogs = [...this.allCatalogs];
        } else {
            this.filteredCatalogs = this.allCatalogs.filter(catalog => 
                this._matchesSearch(catalog, searchTerm.toLowerCase())
            );
        }

        this._applyCurrentFilters();
    }

    /**
     * Verifica si un catálogo coincide con el término de búsqueda
     */
    _matchesSearch(catalog, searchTerm) {
        const searchableFields = [
            catalog.title || catalog.name,
            catalog.description || '',
            catalog.responsible || '',
            ...(catalog.tags || [])
        ];

        const searchableText = searchableFields.join(' ').toLowerCase();
        return searchableText.includes(searchTerm);
    }

    /**
     * Maneja cambios en los filtros
     */
    _handleFilterChange(filters) {
        this._applyCurrentFilters();
    }

    /**
     * Aplica los filtros actuales a los catálogos
     */
    _applyCurrentFilters() {
        const filters = this.searchBar.validateFilters() ? this.searchBar._getFilterValues() : {};
        
        let filtered = [...this.filteredCatalogs];

        // Aplicar filtro por responsable
        if (filters.responsible) {
            filtered = filtered.filter(catalog => 
                catalog.responsible === filters.responsible
            );
        }

        // Aplicar filtro por permisos
        if (filters.permissions) {
            filtered = filtered.filter(catalog => 
                (catalog.permissions || 'public') === filters.permissions
            );
        }

        // Aplicar filtro por formato (siempre parquet por ahora)
        if (filters.format && filters.format !== 'parquet') {
            filtered = [];
        }

        this.filteredCatalogs = filtered;
        this._renderCatalogs();
        this._updateResultsCount();
    }

    /**
     * Popula los filtros con valores únicos de los catálogos
     */
    _populateFilters() {
        // Extraer responsables únicos
        const responsibles = [...new Set(
            this.allCatalogs
                .map(catalog => catalog.responsible)
                .filter(Boolean)
        )].sort();

        // Actualizar filtro de responsables
        this.searchBar.updateFilterOptions('responsible', responsibles);
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