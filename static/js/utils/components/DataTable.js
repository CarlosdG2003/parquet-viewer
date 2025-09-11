/**
 * DataTable Component - Maneja la visualización de datos tabulares con paginación
 */
class DataTable {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = DOM.$(containerId);
        this.paginationContainer = DOM.$('#paginationContainer');
        
        this.onPageChange = options.onPageChange || (() => {});
        this.onColumnSelect = options.onColumnSelect || (() => {});
        
        this.currentPage = 1;
        this.totalPages = 1;
        this.totalRows = 0;
        this.columns = [];
        this.data = [];
    }

    /**
     * Renderiza la tabla con datos
     */
    render(result) {
        if (!this.container) {
            console.error(`Container ${this.containerId} not found`);
            return;
        }

        const { data, pagination, columns } = result;
        
        this.data = data;
        this.columns = columns;
        this.currentPage = pagination.page;
        this.totalPages = pagination.total_pages;
        this.totalRows = pagination.total_rows;

        if (!data || data.length === 0) {
            this._renderEmpty();
            return;
        }

        this._renderTable();
        this._renderPagination();
    }

    /**
     * Renderiza la tabla de datos
     */
    _renderTable() {
        const tableHTML = `
            <table class="data-table">
                <thead>
                    <tr>
                        ${this.columns.map(col => 
                            `<th title="${DOM.escapeHtml(col)}">${DOM.escapeHtml(col)}</th>`
                        ).join('')}
                    </tr>
                </thead>
                <tbody>
                    ${this._renderTableRows()}
                </tbody>
            </table>
        `;

        this.container.innerHTML = tableHTML;
    }

    /**
     * Renderiza las filas de la tabla
     */
    _renderTableRows() {
        return this.data.map(row => {
            const cells = this.columns.map(col => {
                const value = row[col];
                const displayValue = value !== null && value !== undefined ? value : 'NULL';
                return `<td title="${DOM.escapeHtml(String(displayValue))}">${DOM.escapeHtml(String(displayValue))}</td>`;
            }).join('');
            
            return `<tr>${cells}</tr>`;
        }).join('');
    }

    /**
     * Renderiza estado vacío
     */
    _renderEmpty() {
        this.container.innerHTML = '<div class="loading-state">No hay datos disponibles</div>';
        if (this.paginationContainer) {
            this.paginationContainer.innerHTML = '';
        }
    }

    /**
     * Renderiza los controles de paginación
     */
    _renderPagination() {
        if (!this.paginationContainer) return;

        const paginationHTML = `
            <button class="pagination-button" 
                    data-page="1" 
                    ${this.currentPage === 1 ? 'disabled' : ''}>
                Primero
            </button>
            <button class="pagination-button" 
                    data-page="${this.currentPage - 1}" 
                    ${this.currentPage === 1 ? 'disabled' : ''}>
                Anterior
            </button>
            <span class="pagination-info">
                Página ${this.currentPage} de ${this.totalPages}
            </span>
            <button class="pagination-button" 
                    data-page="${this.currentPage + 1}" 
                    ${this.currentPage === this.totalPages ? 'disabled' : ''}>
                Siguiente
            </button>
            <button class="pagination-button" 
                    data-page="${this.totalPages}" 
                    ${this.currentPage === this.totalPages ? 'disabled' : ''}>
                Último
            </button>
        `;

        this.paginationContainer.innerHTML = paginationHTML;
        this._bindPaginationEvents();
    }

    /**
     * Vincula eventos de paginación
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

        this.onPageChange(page);
    }

    /**
     * Muestra estado de carga
     */
    showLoading(message = 'Cargando datos...') {
        DOM.showLoading(this.containerId, message);
        if (this.paginationContainer) {
            this.paginationContainer.innerHTML = '';
        }
    }

    /**
     * Muestra estado de error
     */
    showError(message) {
        DOM.showError(this.containerId, message);
        if (this.paginationContainer) {
            this.paginationContainer.innerHTML = '';
        }
    }

    /**
     * Obtiene información de registros
     */
    getRecordsInfo() {
        return {
            currentPage: this.currentPage,
            totalPages: this.totalPages,
            totalRows: this.totalRows,
            displayedRows: this.data.length
        };
    }

    /**
     * Obtiene los datos actuales
     */
    getCurrentData() {
        return {
            columns: this.columns,
            data: this.data
        };
    }

    /**
     * Limpia la tabla
     */
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

    /**
     * Exporta los datos actuales (placeholder)
     */
    exportData(format = 'csv') {
        console.log('Export functionality - to be implemented');
        return {
            format,
            columns: this.columns,
            data: this.data,
            totalRows: this.totalRows
        };
    }
}

window.DataTable = DataTable;