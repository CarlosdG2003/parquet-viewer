/**
 * CatalogDetail Page - Maneja la vista de detalle de un catálogo específico
 */
class CatalogDetailPage {
    constructor() {
        this.currentCatalog = null;
        this.catalogInfo = null;
        this.catalogMetadata = null;
        this.availableColumns = [];
        this.selectedColumns = [];
        
        this.dataTable = null;
        this.chartViewer = null;
        this.onBackCallback = null;
        
        this.init();
    }

    /**
     * Inicializa la página
     */
    init() {
        this._initializeDataTable();
        this._initializeChartViewer();
        this._bindEvents();
    }

    /**
     * Inicializa la tabla de datos
     */
    _initializeDataTable() {
        this.dataTable = new DataTable('#dataTableContainer', {
            onPageChange: (page) => this._loadCatalogData(page),
            onColumnSelect: (columns) => this._handleColumnSelection(columns)
        });
    }

    /**
     * Inicializa el visor de gráficas
     */
    _initializeChartViewer() {
        this.chartViewer = new ChartViewer('#chartsPanel');
    }

    /**
     * Vincula eventos de la página
     */
    _bindEvents() {
        // Botón de volver
        const backButton = DOM.$('#backToCatalogs');
        if (backButton) {
            backButton.addEventListener('click', () => this._handleBack());
        }

        // Tabs de datos
        const dataTabs = DOM.$$('.data-tab');
        dataTabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                const tabName = e.target.dataset.tab;
                this._switchTab(tabName);
            });
        });

        // Controles de datos
        const columnsButton = DOM.$('#columnsButton');
        const applyColumnsButton = DOM.$('#applyColumns');
        const exportButton = DOM.$('#exportButton');

        if (columnsButton) {
            columnsButton.addEventListener('click', () => this._toggleColumnsSelector());
        }

        if (applyColumnsButton) {
            applyColumnsButton.addEventListener('click', () => this._applyColumnSelection());
        }

        if (exportButton) {
            exportButton.addEventListener('click', () => this._handleExport());
        }
    }

    /**
     * Abre un catálogo específico
     */
    async openCatalog(catalog) {
        try {
            this.currentCatalog = catalog;
            
            // Mostrar estado de carga
            this._showLoadingStates();
            
            // Cargar información del catálogo
            await this._loadCatalogInfo();
            
            // Poblar la información en la UI
            this._populateCatalogInfo();
            
            // Cargar datos por defecto
            await this._loadCatalogData(1);
            
            // Inicializar gráficas para este archivo
            if (this.chartViewer) {
                await this.chartViewer.initialize(this.currentCatalog.name);
            }
            
            // Mostrar la vista
            this.show();
            
        } catch (error) {
            console.error('Error al abrir catálogo:', error);
            this._showErrorStates('Error al cargar el catálogo');
        }
    }

    /**
     * Carga la información del catálogo
     */
    async _loadCatalogInfo() {
        const [infoResponse, metadataResponse] = await Promise.all([
            apiClient.getFileInfo(this.currentCatalog.name),
            apiClient.getFileMetadata(this.currentCatalog.name)
        ]);

        this.catalogInfo = infoResponse;
        this.catalogMetadata = metadataResponse;
        this.availableColumns = this.catalogInfo.columns ? 
            this.catalogInfo.columns.map(col => col.name) : [];
        
        this._setupColumnsSelector();
    }

    /**
     * Popula la información del catálogo en la UI
     */
    _populateCatalogInfo() {
        // Título y permisos
        this._updateElement('#catalogTitle', this.currentCatalog.title || this.currentCatalog.name);
        this._updatePermissionsBadge();

        // Información del catálogo
        this._updateElement('#catalogDescription', 
            this.currentCatalog.description || 'Sin descripción disponible');
        this._updateElement('#catalogResponsible', this.currentCatalog.responsible || 'N/A');
        
        // Aplicar traducción a la frecuencia
        const frequency = this.currentCatalog.frequency || 'N/A';
        const translatedFrequency = this._translateFrequency(frequency);
        this._updateElement('#catalogFrequency', translatedFrequency);
        
        this._updateElement('#catalogRecords', 
            DOM.formatNumber(this.catalogInfo.row_count));
        this._updateElement('#catalogLastUpdated', 
            DOM.formatDate(this.currentCatalog.modified));

        // Tags
        this._updateTags();
    }

    /**
     * Traduce frecuencias al español
     */
    _translateFrequency(frequency) {
        const translations = {
            'daily': 'Diaria',
            'weekly': 'Semanal',
            'monthly': 'Mensual',
            'quarterly': 'Trimestral',
            'yearly': 'Anual',
            'on-demand': 'Bajo demanda'
        };
        return translations[frequency] || frequency;
    }

    /**
     * Actualiza el badge de permisos
     */
    _updatePermissionsBadge() {
        const permissionsElement = DOM.$('#catalogPermissions');
        if (permissionsElement) {
            const permissions = this.currentCatalog.permissions || 'public';
            // Aplicar traducción a los permisos
            const translatedPermissions = this._translatePermission(permissions);
            permissionsElement.textContent = translatedPermissions;
            permissionsElement.className = `permissions-badge ${permissions}`;
        }
    }

    /**
     * Traduce permisos al español
     */
    _translatePermission(permission) {
        const translations = {
            'public': 'Público',
            'internal': 'Interno',
            'confidential': 'Confidencial'
        };
        return translations[permission] || permission;
    }

    /**
     * Actualiza los tags
     */
    _updateTags() {
        const tagsContainer = DOM.$('#catalogTags');
        if (tagsContainer) {
            const tags = this.currentCatalog.tags || [];
            if (tags.length > 0) {
                tagsContainer.innerHTML = tags.map(tag => 
                    `<span class="tag">${DOM.escapeHtml(tag)}</span>`
                ).join('');
            } else {
                tagsContainer.innerHTML = '<span class="tag">sin-tags</span>';
            }
        }
    }

    /**
     * Cambia entre tabs
     */
    _switchTab(tabName) {
        // Actualizar tabs activos
        DOM.$$('.data-tab').forEach(tab => {
            DOM.removeClass(tab, 'active');
        });
        DOM.addClass(`[data-tab="${tabName}"]`, 'active');

        // Mostrar panel correspondiente
        DOM.$$('.tab-panel').forEach(panel => {
            DOM.addClass(panel, 'hidden');
        });
        DOM.removeClass(`#${tabName}Panel`, 'hidden');

        // Cargar contenido específico
        if (tabName === 'schema') {
            this._loadSchema();
        } else if (tabName === 'charts') {
            // Las gráficas ya se inicializan al abrir el catálogo
            // No es necesario cargar nada adicional aquí
        }
    }

    /**
     * Carga los datos del catálogo
     */
    async _loadCatalogData(page = 1) {
        if (!this.currentCatalog) return;

        try {
            this.dataTable.showLoading();

            const options = {
                page: page,
                pageSize: 50,
                columns: this.selectedColumns.length > 0 ? this.selectedColumns : null
            };

            const result = await apiClient.getFileData(this.currentCatalog.name, options);
            
            this.dataTable.render(result);
            this._updateRecordsInfo(result.pagination);

        } catch (error) {
            this.dataTable.showError('Error al cargar datos: ' + error.message);
        }
    }

    /**
     * Carga el esquema del catálogo
     */
    async _loadSchema() {
        try {
            DOM.showLoading('#schemaContent', 'Cargando esquema...');
            
            const result = await apiClient.getFileSchema(this.currentCatalog.name);
            this._renderSchema(result.schema);

        } catch (error) {
            DOM.showError('#schemaContent', 'Error al cargar esquema: ' + error.message);
        }
    }

    /**
     * Renderiza el esquema - MANTIENE LA VERSIÓN ORIGINAL QUE FUNCIONA
     */
    _renderSchema(schema) {
        const schemaContent = DOM.$('#schemaContent');
        if (!schemaContent) return;

        const tableHTML = `
            <table class="schema-table">
                <thead>
                    <tr>
                        <th>Columna</th>
                        <th>Tipo</th>
                        <th>Valores Nulos</th>
                        <th>Valores Únicos</th>
                    </tr>
                </thead>
                <tbody>
                    ${schema.map(col => `
                        <tr>
                            <td><strong>${DOM.escapeHtml(col.name)}</strong></td>
                            <td>${DOM.escapeHtml(col.type)}</td>
                            <td>${DOM.formatNumber(col.null_count)}</td>
                            <td>${DOM.formatNumber(col.unique_count)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;

        schemaContent.innerHTML = tableHTML;
    }

    /**
     * Configura el selector de columnas
     */
    _setupColumnsSelector() {
        const columnsList = DOM.$('#columnsList');
        if (columnsList) {
            columnsList.innerHTML = this.availableColumns.map(col => 
                `<option value="${DOM.escapeHtml(col)}">${DOM.escapeHtml(col)}</option>`
            ).join('');
        }
    }

    /**
     * Alterna el selector de columnas
     */
    _toggleColumnsSelector() {
        DOM.toggle('#columnsSelector');
    }

    /**
     * Aplica la selección de columnas
     */
    _applyColumnSelection() {
        const columnsList = DOM.$('#columnsList');
        if (columnsList) {
            this.selectedColumns = Array.from(columnsList.selectedOptions)
                .map(option => option.value);
            
            this._loadCatalogData(1);
            DOM.hide('#columnsSelector');
        }
    }

    /**
     * Maneja la exportación
     */
    _handleExport() {
        const exportData = this.dataTable.exportData('csv');
        console.log('Export data:', exportData);
        // Implementar lógica de exportación
    }

    /**
     * Actualiza la información de registros
     */
    _updateRecordsInfo(pagination) {
        const recordsInfo = DOM.$('#recordsInfo');
        if (recordsInfo) {
            recordsInfo.textContent = `${DOM.formatNumber(pagination.total)} registros`;
        }
    }

    /**
     * Maneja el botón de volver
     */
    _handleBack() {
        this.hide();
        if (this.onBackCallback) {
            this.onBackCallback();
        }
    }

    /**
     * Helpers de UI
     */
    _updateElement(selector, content) {
        const element = DOM.$(selector);
        if (element) {
            element.textContent = content;
        }
    }

    _showLoadingStates() {
        DOM.showLoading('#dataTableContainer');
    }

    _showErrorStates(message) {
        DOM.showError('#dataTableContainer', message);
    }

    /**
     * Muestra/oculta la página
     */
    show() {
        DOM.show('#catalogDetailView');
    }

    hide() {
        DOM.hide('#catalogDetailView');
    }

    /**
     * Establece callback para volver
     */
    onBack(callback) {
        this.onBackCallback = callback;
    }

    /**
     * Limpia el estado de la página
     */
    clear() {
        this.currentCatalog = null;
        this.catalogInfo = null;
        this.catalogMetadata = null;
        this.selectedColumns = [];
        
        if (this.dataTable) {
            this.dataTable.clear();
        }
        
        // Limpiar gráficas
        if (this.chartViewer) {
            this.chartViewer.clear();
        }
    }

    /**
     * Obtiene el catálogo actual por nombre (usado por navegación del navegador)
     */
    getCatalogByName(catalogName) {
        if (this.currentCatalog && this.currentCatalog.name === catalogName) {
            return this.currentCatalog;
        }
        return null;
    }
}

window.CatalogDetailPage = CatalogDetailPage;