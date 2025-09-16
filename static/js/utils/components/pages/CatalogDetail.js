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
     * Inicializa la tabla de datos con funcionalidades mejoradas
     */
    _initializeDataTable() {
        this.dataTable = new DataTable('#dataTableContainer', {
            onPageChange: (page, filters) => this._loadCatalogData(page, filters),
            onColumnSelect: (columns) => this._handleColumnSelection(columns),
            onDataChange: (filters) => this._loadCatalogDataWithFilters(filters)
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
     * Carga los datos del catálogo con filtros y paginación mejorada
     */
    async _loadCatalogData(page = 1, additionalFilters = {}) {
        if (!this.currentCatalog) return;

        try {
            this.dataTable.showLoading('Cargando datos...');

            // Combinar filtros
            const filters = {
                page: page,
                page_size: 50,
                columns: this.selectedColumns.length > 0 ? this.selectedColumns.join(',') : null,
                search: additionalFilters.search || '',
                sort_column: additionalFilters.sortColumn || null,
                sort_order: additionalFilters.sortOrder || 'asc',
                ...additionalFilters
            };

            // Usar el endpoint mejorado
            const result = await apiClient.getFileDataEnhanced(this.currentCatalog.name, filters);
            
            this.dataTable.render(result);
            this._updateRecordsInfo(result.pagination, result);

        } catch (error) {
            console.error('Error loading catalog data:', error);
            this.dataTable.showError('Error al cargar datos: ' + error.message);
        }
    }

    /**
     * Maneja cambios de datos (filtros, búsqueda, ordenamiento)
     */
    async _loadCatalogDataWithFilters(filters) {
        await this._loadCatalogData(filters.page || 1, filters);
    }

    /**
     * Carga el esquema del catálogo con metadatos mejorados
     */
    async _loadSchema() {
        try {
            DOM.showLoading('#schemaContent', 'Cargando esquema...');
            
            // Usar el endpoint mejorado de esquema
            const result = await apiClient.getFileSchemaEnhanced(this.currentCatalog.name);
            this._renderEnhancedSchema(result);

        } catch (error) {
            console.error('Error loading schema:', error);
            DOM.showError('#schemaContent', 'Error al cargar esquema: ' + error.message);
        }
    }

    /**
     * Renderiza el esquema mejorado con metadatos personalizados
     */
    _renderEnhancedSchema(schemaResult) {
        const schemaContent = DOM.$('#schemaContent');
        if (!schemaContent) return;

        const { schema, has_custom_names, total_columns } = schemaResult;

        const tableHTML = `
            <div class="schema-header">
                <h4>Esquema de Datos</h4>
                <div class="schema-info">
                    <span class="schema-stat">Columnas: <strong>${total_columns}</strong></span>
                    ${has_custom_names ? '<span class="custom-names-badge">Nombres Personalizados</span>' : ''}
                </div>
            </div>
            
            <table class="schema-table enhanced">
                <thead>
                    <tr>
                        <th>Columna</th>
                        ${has_custom_names ? '<th>Nombre Original</th>' : ''}
                        <th>Tipo</th>
                        <th>Descripción</th>
                        <th>Valores Nulos</th>
                        <th>Valores Únicos</th>
                    </tr>
                </thead>
                <tbody>
                    ${schema.map(col => `
                        <tr class="schema-row ${col.has_custom_metadata ? 'customized' : ''}">
                            <td class="column-name">
                                <strong>${DOM.escapeHtml(col.display_name)}</strong>
                                ${col.has_custom_metadata ? '<span class="custom-indicator">★</span>' : ''}
                            </td>
                            ${has_custom_names ? `
                                <td class="original-name">
                                    <code>${DOM.escapeHtml(col.original_name)}</code>
                                </td>
                            ` : ''}
                            <td class="column-type">
                                <span class="type-badge">${DOM.escapeHtml(col.type)}</span>
                            </td>
                            <td class="column-description">
                                ${col.description ? 
                                    `<span class="description-text">${DOM.escapeHtml(col.description)}</span>` : 
                                    '<span class="no-description">Sin descripción</span>'
                                }
                            </td>
                            <td class="stat-value">${DOM.formatNumber(col.null_count)}</td>
                            <td class="stat-value">${DOM.formatNumber(col.unique_count)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
            
            ${has_custom_names ? `
                <div class="schema-footer">
                    <p class="schema-note">
                        <span class="custom-indicator">★</span> Columnas con metadatos personalizados
                    </p>
                </div>
            ` : ''}
        `;

        schemaContent.innerHTML = tableHTML;
    }

    /**
     * Configuración mejorada del selector de columnas
     */
    _setupColumnsSelector() {
        const columnsList = DOM.$('#columnsList');
        if (columnsList && this.availableColumns.length > 0) {
            columnsList.innerHTML = this.availableColumns.map(col => 
                `<option value="${DOM.escapeHtml(col)}" title="${DOM.escapeHtml(col)}">${DOM.escapeHtml(col)}</option>`
            ).join('');
            
            // Agregar información sobre nombres personalizados si los hay
            if (this.catalogInfo && this.catalogInfo.has_custom_names) {
                const info = document.createElement('div');
                info.className = 'columns-info';
                info.innerHTML = '<small>★ Algunas columnas tienen nombres personalizados</small>';
                columnsList.parentElement.insertBefore(info, columnsList);
            }
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
     * Maneja la exportación con filtros aplicados
     */
    _handleExport() {
        const exportData = this.dataTable.exportData('csv');
        const filters = this.dataTable.getCurrentFilters();
        
        console.log('Exporting with filters:', {
            ...exportData,
            appliedFilters: filters
        });
        
        // Aquí puedes implementar la lógica de exportación real
        // Por ejemplo, hacer una llamada al backend para generar el archivo
        this._showExportDialog(exportData);
    }

    /**
     * Muestra diálogo de exportación
     */
    _showExportDialog(exportData) {
        const message = `
            Exportando ${exportData.totalRows} registros
            ${exportData.filters.search ? `\nBúsqueda: "${exportData.filters.search}"` : ''}
            ${exportData.filters.sortColumn ? `\nOrdenado por: ${exportData.filters.sortColumn} (${exportData.filters.sortOrder})` : ''}
        `;
        
        if (confirm(message + '\n\n¿Continuar con la exportación?')) {
            // Implementar exportación real aquí
            alert('Función de exportación pendiente de implementación');
        }
    }

    /**
     * Actualiza la información de registros con datos mejorados
     */
    _updateRecordsInfo(pagination, result) {
        const recordsInfo = DOM.$('#recordsInfo');
        if (recordsInfo) {
            const { search_applied, sort_applied, has_custom_names } = result;
            
            let infoText = `${DOM.formatNumber(pagination.total_rows)} registros`;
            
            const badges = [];
            if (search_applied) badges.push('<span class="info-badge search">Filtrado</span>');
            if (sort_applied) badges.push('<span class="info-badge sort">Ordenado</span>');
            if (has_custom_names) badges.push('<span class="info-badge custom">Nombres Personalizados</span>');
            
            recordsInfo.innerHTML = `
                <div class="records-info-enhanced">
                    <span class="records-count">${infoText}</span>
                    <div class="records-badges">${badges.join('')}</div>
                </div>
            `;
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