/**
 * DataTable Component - Maneja la visualización de datos tabulares con funcionalidades avanzadas
 */
class DataTable {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = DOM.$(containerId);
        this.paginationContainer = DOM.$('#paginationContainer');
        
        this.onPageChange = options.onPageChange || (() => {});
        this.onColumnSelect = options.onColumnSelect || (() => {});
        this.onDataChange = options.onDataChange || (() => {});
        
        this.currentPage = 1;
        this.totalPages = 1;
        this.totalRows = 0;
        this.columns = [];
        this.data = [];
        this.searchTerm = '';
        
        // NUEVO: Sistema de ordenamiento múltiple
        this.sortColumns = []; // Array de objetos {column: 'name', order: 'asc'}
        this.maxSortColumns = 3; // Máximo 3 columnas ordenadas
        
        // Mantener compatibilidad con el sistema anterior
        this.sortColumn = null;
        this.sortOrder = 'asc';
        
        this.hasCustomNames = false;
        
        this._initializeFilters();
    }

    /**
     * Inicializa los filtros y controles
     */
    _initializeFilters() {
        // Buscar input de filtro de datos
        const dataFilterInput = DOM.$('#dataFilter');
        if (dataFilterInput) {
            // Debounce para evitar muchas peticiones
            let searchTimeout;
            dataFilterInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.searchTerm = e.target.value.trim();
                    this._triggerDataReload();
                }, 500);
            });
        }
    }

    /**
     * Renderiza la tabla con datos y funcionalidades mejoradas
     */
    render(result) {
        if (!this.container) {
            console.error(`Container ${this.containerId} not found`);
            return;
        }

        const { data, pagination, columns, has_custom_names } = result;
        
        this.data = data;
        this.columns = columns || [];
        this.currentPage = pagination.page;
        this.totalPages = pagination.total_pages;
        this.totalRows = pagination.total_rows;
        this.hasCustomNames = has_custom_names || false;

        if (!data || data.length === 0) {
            this._renderEmpty();
            return;
        }

        this._renderTable();
        this._renderPagination();
        this._updateDataInfo(result);
    }

    /**
     * Renderiza la tabla de datos con controles de ordenamiento múltiple
     */
    _renderTable() {
        const tableHTML = `
            <div class="table-controls">
                <button class="btn-reset-sort" ${this.sortColumns.length === 0 ? 'disabled' : ''} 
                        title="Limpiar todos los filtros">
                     Limpiar filtros
                </button>
                <div class="sort-info">
                    ${this.sortColumns.length > 0 ? 
                        `<span class="sort-count">${this.sortColumns.length} columna${this.sortColumns.length > 1 ? 's' : ''} ordenada${this.sortColumns.length > 1 ? 's' : ''}</span>` : 
                        '<span class="sort-hint">Ctrl+Clic para ordenamiento múltiple</span>'
                    }
                </div>
            </div>
            <div class="table-wrapper">
                <table class="data-table enhanced">
                    <thead>
                        <tr>
                            ${this.columns.map(col => this._renderColumnHeader(col)).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${this._renderTableRows()}
                    </tbody>
                </table>
            </div>
        `;

        this.container.innerHTML = tableHTML;
        this._bindColumnSortEvents();
        this._bindResetButton();
    }

    /**
     * Renderiza el header de una columna con controles de ordenamiento múltiple
     */
    _renderColumnHeader(col) {
        const sortInfo = this.sortColumns.find(s => s.column === col);
        const sortIndex = this.sortColumns.findIndex(s => s.column === col);
        
        let sortIcon = '↕';
        let sortClass = '';
        let sortPriority = '';
        
        if (sortInfo) {
            sortIcon = sortInfo.order === 'asc' ? '↑' : '↓';
            sortClass = `sorted-${sortInfo.order}`;
            if (this.sortColumns.length > 1) {
                sortPriority = `<span class="sort-priority">${sortIndex + 1}</span>`;
            }
        }
        
        return `
            <th class="sortable-column ${sortClass}" 
                data-column="${DOM.escapeHtml(col)}" 
                title="Clic: ordenar | Ctrl+Clic: ordenamiento múltiple | Clic repetido: quitar orden">
                <div class="column-header">
                    <span class="column-name">${DOM.escapeHtml(col)}</span>
                    <div class="sort-controls">
                        ${sortPriority}
                        <span class="sort-indicator">${sortIcon}</span>
                    </div>
                </div>
            </th>
        `;
    }

    /**
     * Renderiza las filas de la tabla con mejor formato
     */
    _renderTableRows() {
        return this.data.map((row, rowIndex) => {
            const cells = this.columns.map(col => {
                const value = row[col];
                const formattedValue = this._formatCellValue(value, col);
                const cellClass = this._getCellClass(value);
                
                return `<td class="${cellClass}" title="${DOM.escapeHtml(String(formattedValue))}">${formattedValue}</td>`;
            }).join('');
            
            return `<tr class="data-row" data-row-index="${rowIndex}">${cells}</tr>`;
        }).join('');
    }

    /**
     * Formatea el valor de una celda según su tipo
     */
    _formatCellValue(value, columnName) {
        if (value === null || value === undefined) {
            return '<span class="null-value">NULL</span>';
        }
        
        // Detectar y formatear fechas
        if (this._isDateString(value)) {
            return this._formatDate(value);
        }
        
        // Formatear números
        if (typeof value === 'number') {
            return this._formatNumber(value);
        }
        
        // Formatear booleanos
        if (typeof value === 'boolean') {
            return `<span class="boolean-value ${value}">${value ? 'Verdadero' : 'Falso'}</span>`;
        }
        
        // Texto normal - escapar HTML
        return DOM.escapeHtml(String(value));
    }

    /**
     * Detecta si un string es una fecha
     */
    _isDateString(value) {
        if (typeof value !== 'string') return false;
        
        // Patrones de fecha comunes
        const datePatterns = [
            /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/, // ISO
            /^\d{4}-\d{2}-\d{2}/, // YYYY-MM-DD
            /^\d{2}\/\d{2}\/\d{4}/, // MM/DD/YYYY
        ];
        
        return datePatterns.some(pattern => pattern.test(value)) && !isNaN(Date.parse(value));
    }

    /**
     * Formatea fechas de forma amigable
     */
    _formatDate(dateString) {
        try {
            const date = new Date(dateString);
            const now = new Date();
            const diffTime = Math.abs(now - date);
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            
            // Mostrar formato relativo para fechas recientes
            if (diffDays <= 7) {
                const options = { 
                    weekday: 'long', 
                    hour: '2-digit', 
                    minute: '2-digit' 
                };
                return `<span class="date-value recent" title="${dateString}">${date.toLocaleDateString('es-ES', options)}</span>`;
            } else {
                const options = { 
                    year: 'numeric', 
                    month: 'short', 
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                };
                return `<span class="date-value" title="${dateString}">${date.toLocaleDateString('es-ES', options)}</span>`;
            }
        } catch (e) {
            return DOM.escapeHtml(String(dateString));
        }
    }

    /**
     * Formatea números de forma legible
     */
    _formatNumber(value) {
        if (Number.isInteger(value)) {
            return `<span class="number-value integer">${value.toLocaleString('es-ES')}</span>`;
        } else {
            return `<span class="number-value decimal">${value.toLocaleString('es-ES', { maximumFractionDigits: 4 })}</span>`;
        }
    }

    /**
     * Obtiene la clase CSS para una celda según su valor
     */
    _getCellClass(value) {
        if (value === null || value === undefined) return 'cell-null';
        if (typeof value === 'boolean') return 'cell-boolean';
        if (typeof value === 'number') return 'cell-number';
        if (this._isDateString(value)) return 'cell-date';
        return 'cell-text';
    }

    /**
     * Vincula eventos de ordenamiento de columnas con soporte múltiple
     */
    _bindColumnSortEvents() {
        const sortableColumns = this.container.querySelectorAll('.sortable-column');
        sortableColumns.forEach(col => {
            col.addEventListener('click', (event) => {
                const columnName = col.dataset.column;
                this._handleColumnSort(columnName, event);
            });
        });
    }

    /**
     * Vincula el evento del botón de reseteo
     */
    _bindResetButton() {
        const resetButton = this.container.querySelector('.btn-reset-sort');
        if (resetButton) {
            resetButton.addEventListener('click', () => {
                this.resetAllSorting();
            });
        }
    }

    /**
     * NUEVO: Maneja el ordenamiento múltiple de columnas
     */
    _handleColumnSort(columnName, event) {
        // Verificar si Ctrl/Cmd está presionado para ordenamiento múltiple
        const isMultiSort = event.ctrlKey || event.metaKey;
        
        if (!isMultiSort) {
            // Ordenamiento simple - limpiar otros y solo esta columna
            const existing = this.sortColumns.find(s => s.column === columnName);
            if (existing) {
                // Si ya existe, alternar orden o quitar si es desc
                if (existing.order === 'asc') {
                    existing.order = 'desc';
                } else {
                    // Quitar ordenamiento
                    this.sortColumns = [];
                }
            } else {
                // Nueva columna
                this.sortColumns = [{column: columnName, order: 'asc'}];
            }
        } else {
            // Ordenamiento múltiple
            const existingIndex = this.sortColumns.findIndex(s => s.column === columnName);
            
            if (existingIndex >= 0) {
                const existing = this.sortColumns[existingIndex];
                if (existing.order === 'asc') {
                    existing.order = 'desc';
                } else {
                    // Quitar esta columna del ordenamiento
                    this.sortColumns.splice(existingIndex, 1);
                }
            } else {
                // Agregar nueva columna (máximo 3)
                if (this.sortColumns.length < this.maxSortColumns) {
                    this.sortColumns.push({column: columnName, order: 'asc'});
                } else {
                    // Reemplazar la más antigua
                    this.sortColumns.shift();
                    this.sortColumns.push({column: columnName, order: 'asc'});
                }
            }
        }
        
        // Actualizar variables de compatibilidad
        this._updateLegacySortVariables();
        
        this._triggerDataReload();
    }

    /**
     * NUEVO: Actualiza las variables de ordenamiento legacy para compatibilidad
     */
    _updateLegacySortVariables() {
        if (this.sortColumns.length > 0) {
            this.sortColumn = this.sortColumns[0].column;
            this.sortOrder = this.sortColumns[0].order;
        } else {
            this.sortColumn = null;
            this.sortOrder = 'asc';
        }
    }

    /**
     * NUEVO: Resetea todos los ordenamientos
     */
    resetAllSorting() {
        this.sortColumns = [];
        this.sortColumn = null;
        this.sortOrder = 'asc';
        this._triggerDataReload();
    }

    /**
     * Dispara la recarga de datos con filtros actuales
     */
    _triggerDataReload() {
        if (this.onDataChange) {
            // Convertir array de sort a string para el backend
            let sortColumn = null;
            let sortOrder = 'asc';
            
            if (this.sortColumns.length > 0) {
                // Solo enviar la primera columna al backend (limitación actual)
                sortColumn = this.sortColumns[0].column;
                sortOrder = this.sortColumns[0].order;
            }
            
            this.onDataChange({
                page: 1, // Volver a la primera página
                search: this.searchTerm,
                sortColumn: sortColumn,
                sortOrder: sortOrder
            });
        }
    }

    /**
     * Actualiza la información de datos mostrados
     */
    _updateDataInfo(result) {
        const recordsInfo = DOM.$('#recordsInfo');
        if (recordsInfo) {
            const { pagination, search_applied, sort_applied } = result;
            let infoText = `${DOM.formatNumber(pagination.total_rows)} registros`;
            
            if (search_applied) {
                infoText += ` (filtrados)`;
            }
            
            if (sort_applied || this.sortColumns.length > 0) {
                if (this.sortColumns.length > 1) {
                    infoText += ` • Ordenado por ${this.sortColumns.length} columnas`;
                } else if (this.sortColumns.length === 1) {
                    infoText += ` • Ordenado por ${this.sortColumns[0].column}`;
                }
            }
            
            if (this.hasCustomNames) {
                infoText += ` • Nombres personalizados`;
            }
            
            recordsInfo.innerHTML = `
                <div class="records-info-content">
                    <span class="records-count">${infoText}</span>
                    ${search_applied ? '<span class="filter-badge">Filtrado</span>' : ''}
                    ${(sort_applied || this.sortColumns.length > 0) ? '<span class="sort-badge">Ordenado</span>' : ''}
                </div>
            `;
        }
    }

    /**
     * Renderiza estado vacío mejorado
     */
    _renderEmpty() {
        const emptyHTML = `
            <div class="empty-state-enhanced">
                <div class="empty-icon">📄</div>
                <h3>No hay datos disponibles</h3>
                <p>No se encontraron registros que coincidan con los filtros aplicados.</p>
                ${this.searchTerm ? `<button class="btn-clear-search" onclick="this.clearSearch()">Limpiar búsqueda</button>` : ''}
            </div>
        `;
        
        this.container.innerHTML = emptyHTML;
        if (this.paginationContainer) {
            this.paginationContainer.innerHTML = '';
        }
    }

    /**
     * Limpia la búsqueda actual
     */
    clearSearch() {
        const searchInput = DOM.$('#dataFilter');
        if (searchInput) {
            searchInput.value = '';
            this.searchTerm = '';
            this._triggerDataReload();
        }
    }

    /**
     * Renderiza los controles de paginación mejorados
     */
    _renderPagination() {
        if (!this.paginationContainer) return;

        const paginationHTML = `
            <div class="pagination-enhanced">
                <div class="pagination-info">
                    <span>Página ${this.currentPage} de ${this.totalPages}</span>
                    <span class="page-size-info">${this.data.length} de ${this.totalRows} registros</span>
                </div>
                <div class="pagination-controls">
                    <button class="pagination-button first" 
                            data-page="1" 
                            ${this.currentPage === 1 ? 'disabled' : ''}
                            title="Primera página">
                        ⏮
                    </button>
                    <button class="pagination-button prev" 
                            data-page="${this.currentPage - 1}" 
                            ${this.currentPage === 1 ? 'disabled' : ''}
                            title="Página anterior">
                        ◀
                    </button>
                    
                    ${this._renderPageNumbers()}
                    
                    <button class="pagination-button next" 
                            data-page="${this.currentPage + 1}" 
                            ${this.currentPage === this.totalPages ? 'disabled' : ''}
                            title="Página siguiente">
                        ▶
                    </button>
                    <button class="pagination-button last" 
                            data-page="${this.totalPages}" 
                            ${this.currentPage === this.totalPages ? 'disabled' : ''}
                            title="Última página">
                        ⏭
                    </button>
                </div>
            </div>
        `;

        this.paginationContainer.innerHTML = paginationHTML;
        this._bindPaginationEvents();
    }

    /**
     * Renderiza números de página
     */
    _renderPageNumbers() {
        const maxVisible = 5;
        const start = Math.max(1, this.currentPage - Math.floor(maxVisible / 2));
        const end = Math.min(this.totalPages, start + maxVisible - 1);
        
        let pages = '';
        
        for (let i = start; i <= end; i++) {
            const isActive = i === this.currentPage;
            pages += `
                <button class="pagination-button page-number ${isActive ? 'active' : ''}" 
                        data-page="${i}" 
                        ${isActive ? 'disabled' : ''}>${i}</button>
            `;
        }
        
        return pages;
    }

    /**
     * Vincula eventos de paginación mejorados
     */
    _bindPaginationEvents() {
        const buttons = this.paginationContainer.querySelectorAll('.pagination-button:not([disabled])');
        
        buttons.forEach(button => {
            button.addEventListener('click', () => {
                const page = parseInt(button.dataset.page);
                this.goToPage(page);
            });
        });
    }

    /**
     * Navega a una página específica
     */
    goToPage(page) {
        if (page < 1 || page > this.totalPages || page === this.currentPage) {
            return;
        }

        if (this.onPageChange) {
            this.onPageChange(page, {
                search: this.searchTerm,
                sortColumn: this.sortColumn,
                sortOrder: this.sortOrder
            });
        }
    }

    /**
     * Muestra estado de carga mejorado
     */
    showLoading(message = 'Cargando datos...') {
        const loadingHTML = `
            <div class="loading-state-enhanced">
                <div class="loading-spinner"></div>
                <p>${message}</p>
            </div>
        `;
        
        this.container.innerHTML = loadingHTML;
        if (this.paginationContainer) {
            this.paginationContainer.innerHTML = '';
        }
    }

    /**
     * Muestra estado de error mejorado
     */
    showError(message) {
        const errorHTML = `
            <div class="error-state-enhanced">
                <div class="error-icon">⚠️</div>
                <h3>Error al cargar datos</h3>
                <p>${DOM.escapeHtml(message)}</p>
                <button class="retry-button" onclick="location.reload()">Reintentar</button>
            </div>
        `;
        
        this.container.innerHTML = errorHTML;
        if (this.paginationContainer) {
            this.paginationContainer.innerHTML = '';
        }
    }

    /**
     * Obtiene el estado actual de filtros y ordenamiento
     */
    getCurrentFilters() {
        return {
            search: this.searchTerm,
            sortColumn: this.sortColumn,
            sortOrder: this.sortOrder,
            sortColumns: this.sortColumns, // NUEVO: Información completa de ordenamiento múltiple
            page: this.currentPage
        };
    }

    /**
     * ACTUALIZADO: Restablece todos los filtros incluyendo ordenamiento múltiple
     */
    resetFilters() {
        this.searchTerm = '';
        this.sortColumns = [];
        this.sortColumn = null;
        this.sortOrder = 'asc';
        
        const searchInput = DOM.$('#dataFilter');
        if (searchInput) {
            searchInput.value = '';
        }
        
        this._triggerDataReload();
    }

    // Mantener métodos existentes para compatibilidad
    getRecordsInfo() {
        return {
            currentPage: this.currentPage,
            totalPages: this.totalPages,
            totalRows: this.totalRows,
            displayedRows: this.data.length,
            hasCustomNames: this.hasCustomNames,
            searchTerm: this.searchTerm,
            sortColumn: this.sortColumn,
            sortOrder: this.sortOrder,
            sortColumns: this.sortColumns // NUEVO
        };
    }

    getCurrentData() {
        return {
            columns: this.columns,
            data: this.data,
            hasCustomNames: this.hasCustomNames
        };
    }

    clear() {
        DOM.clearContainer(this.container);
        if (this.paginationContainer) {
            DOM.clearContainer(this.paginationContainer);
        }
        
        this.currentPage = 1;
        this.totalPages = 1;
        this.totalRows = 0;
        this.columns = [];
        this.data = [];
        this.searchTerm = '';
        this.sortColumns = []; // NUEVO
        this.sortColumn = null;
        this.sortOrder = 'asc';
        this.hasCustomNames = false;
    }

    /**
     * Exporta los datos actuales con filtros aplicados
     */
    exportData(format = 'csv') {
        return {
            format,
            columns: this.columns,
            data: this.data,
            totalRows: this.totalRows,
            filters: this.getCurrentFilters(),
            hasCustomNames: this.hasCustomNames
        };
    }

    /**
     * Actualiza solo los datos sin cambiar la estructura
     */
    updateData(newData) {
        this.data = newData;
        if (this.container.querySelector('.data-table')) {
            const tbody = this.container.querySelector('tbody');
            if (tbody) {
                tbody.innerHTML = this._renderTableRows();
            }
        }
    }
}

window.DataTable = DataTable;