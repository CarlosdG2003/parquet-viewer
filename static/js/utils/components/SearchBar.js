/**
 * SearchBar Component - Maneja la búsqueda y filtros
 */
class SearchBar {
    constructor(options = {}) {
        this.onSearch = options.onSearch || (() => {});
        this.onFilterChange = options.onFilterChange || (() => {});
        this.debounceDelay = options.debounceDelay || 300;
        
        this.searchInput = DOM.$('#searchInput');
        this.searchButton = DOM.$('#searchButton');
        this.filtersButton = DOM.$('#filtersButton');
        this.filtersPanel = DOM.$('#filtersPanel');
        this.filterSelects = DOM.$$('.filter-select');
        
        this.init();
    }

    /**
     * Inicializa el componente
     */
    init() {
        this._bindEvents();
    }

    /**
     * Vincula los eventos
     */
    _bindEvents() {
        // Búsqueda con debounce
        if (this.searchInput) {
            const debouncedSearch = DOM.debounce(() => {
                this._handleSearch();
            }, this.debounceDelay);

            this.searchInput.addEventListener('input', debouncedSearch);
        }

        // Botón de búsqueda
        if (this.searchButton) {
            this.searchButton.addEventListener('click', () => {
                this._handleSearch();
            });
        }

        // Toggle de filtros
        if (this.filtersButton) {
            this.filtersButton.addEventListener('click', () => {
                this._toggleFilters();
            });
        }

        // Cambios en filtros
        this.filterSelects.forEach(select => {
            select.addEventListener('change', () => {
                this._handleFilterChange();
            });
        });

        // Enter en búsqueda
        if (this.searchInput) {
            this.searchInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    this._handleSearch();
                }
            });
        }
    }

    /**
     * Maneja la búsqueda
     */
    _handleSearch() {
        const searchTerm = this.searchInput ? this.searchInput.value.trim() : '';
        this.onSearch(searchTerm);
    }

    /**
     * Maneja cambios en filtros
     */
    _handleFilterChange() {
        const filters = this._getFilterValues();
        this.onFilterChange(filters);
    }

    /**
     * Obtiene los valores actuales de los filtros
     */
    _getFilterValues() {
        const filters = {};
        
        this.filterSelects.forEach(select => {
            const filterName = select.id.replace('Filter', '');
            filters[filterName] = select.value || null;
        });

        return filters;
    }

    /**
     * Alterna la visibilidad del panel de filtros
     */
    _toggleFilters() {
        if (this.filtersPanel) {
            DOM.toggle(this.filtersPanel);
        }
    }

    /**
     * Muestra/oculta el panel de filtros
     */
    showFilters() {
        DOM.show(this.filtersPanel);
    }

    hideFilters() {
        DOM.hide(this.filtersPanel);
    }

    /**
     * Obtiene el término de búsqueda actual
     */
    getSearchTerm() {
        return this.searchInput ? this.searchInput.value.trim() : '';
    }

    /**
     * Establece el término de búsqueda
     */
    setSearchTerm(term) {
        if (this.searchInput) {
            this.searchInput.value = term;
        }
    }

    /**
     * Limpia la búsqueda y filtros
     */
    clear() {
        if (this.searchInput) {
            this.searchInput.value = '';
        }
        
        this.filterSelects.forEach(select => {
            select.value = '';
        });

        this.hideFilters();
    }

    /**
     * Actualiza las opciones de un filtro específico
     */
    updateFilterOptions(filterName, options) {
        const select = DOM.$(`#${filterName}Filter`);
        if (!select) return;

        // Mantener valor actual si existe
        const currentValue = select.value;
        
        // Limpiar opciones
        select.innerHTML = '<option value="">Todos</option>';
        
        // Añadir nuevas opciones
        options.forEach(option => {
            const optionElement = DOM.createElement('option', {
                value: option.value || option,
            }, option.label || option);
            
            select.appendChild(optionElement);
        });

        // Restaurar valor si aún existe
        if (currentValue && [...select.options].some(opt => opt.value === currentValue)) {
            select.value = currentValue;
        }
    }

    /**
     * Valida los filtros actuales
     */
    validateFilters() {
        const filters = this._getFilterValues();
        const isValid = Object.values(filters).some(value => value !== null && value !== '');
        return isValid;
    }
}

window.SearchBar = SearchBar;