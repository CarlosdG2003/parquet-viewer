/**
 * ChartViewer Component - Generador manual de gráficas
 */
class ChartViewer {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = DOM.$(containerId);
        this.filename = null;
        this.columnsInfo = null;
        this.chartInstances = [];
        this.chartCounter = 0;
    }

    /**
     * Inicializa el visor de gráficas para un archivo
     */
    async initialize(filename) {
        this.filename = filename;
        await this.loadColumnsInfo();
    }

    /**
     * Carga información de las columnas del archivo
     */
    async loadColumnsInfo() {
        if (!this.filename) return;

        try {
            this.columnsInfo = await apiClient.getFileColumnsForCharts(this.filename);
            this.renderChartGenerator();
        } catch (error) {
            console.error('Error cargando información de columnas:', error);
            this.renderError('Error al cargar información del archivo');
        }
    }

    /**
     * Renderiza el generador de gráficas manual
     */
    renderChartGenerator() {
        if (!this.container || !this.columnsInfo) return;

        const { columns, total_rows } = this.columnsInfo;

        // Separar columnas por aptitud
        const xColumns = columns.filter(col => col.suitable_for_x);
        const yColumns = columns.filter(col => col.suitable_for_y);

        this.container.innerHTML = `
            <div class="chart-generator">
                <div class="generator-header">
                    <h4>Generador de Gráficas</h4>
                    <p class="file-info">Archivo: <strong>${this.filename}</strong> • ${total_rows.toLocaleString()} registros</p>
                </div>

                <form id="chartForm" class="chart-form">
                    <div class="form-row">
                        <div class="form-group">
                            <label for="chartType">Tipo de Gráfica *</label>
                            <select id="chartType" required>
                                <option value="">Seleccionar tipo...</option>
                                <option value="line">Líneas</option>
                                <option value="bar">Barras</option>
                                <option value="scatter">Dispersión</option>
                                <option value="histogram">Histograma</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="chartTitle">Título</label>
                            <input type="text" id="chartTitle" placeholder="Título de la gráfica">
                        </div>
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label for="xColumn">Eje X (horizontal) *</label>
                            <select id="xColumn" required>
                                <option value="">Seleccionar columna...</option>
                                ${xColumns.map(col => `
                                    <option value="${col.name}" data-type="${col.category}">
                                        ${col.name} (${col.type})
                                    </option>
                                `).join('')}
                            </select>
                            <small class="help-text">Columnas adecuadas para eje X</small>
                        </div>
                        <div class="form-group" id="yColumnGroup">
                            <label for="yColumn">Eje Y (vertical) *</label>
                            <select id="yColumn" required>
                                <option value="">Seleccionar columna...</option>
                                ${yColumns.map(col => `
                                    <option value="${col.name}" data-type="${col.category}">
                                        ${col.name} (${col.type})
                                    </option>
                                `).join('')}
                            </select>
                            <small class="help-text">Solo columnas numéricas</small>
                        </div>
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label for="dataLimit">Límite de datos</label>
                            <select id="dataLimit">
                                <option value="100">100 registros</option>
                                <option value="500">500 registros</option>
                                <option value="1000" selected>1,000 registros</option>
                                <option value="5000">5,000 registros</option>
                                <option value="10000">10,000 registros</option>
                            </select>
                            <small class="help-text">Limitar datos para mejor rendimiento</small>
                        </div>
                        <div class="form-group">
                            <button type="submit" class="btn-generate" id="generateBtn">
                                Generar Gráfica
                            </button>
                        </div>
                    </div>
                </form>

                <div class="columns-info">
                    <details>
                        <summary>Ver todas las columnas (${columns.length})</summary>
                        <div class="columns-list">
                            ${columns.map(col => `
                                <div class="column-item">
                                    <span class="column-name">${col.name}</span>
                                    <span class="column-type">${col.type}</span>
                                    <span class="column-category ${col.category}">${col.category}</span>
                                    ${col.sample_values.length > 0 ? 
                                        `<span class="column-sample">Ej: ${col.sample_values.slice(0, 2).join(', ')}</span>` : ''
                                    }
                                </div>
                            `).join('')}
                        </div>
                    </details>
                </div>
            </div>

            <div id="chartsContainer" class="charts-container">
                <!-- Las gráficas generadas aparecerán aquí -->
            </div>
        `;

        this.setupFormEvents();
    }

    /**
     * Configura eventos del formulario
     */
    setupFormEvents() {
        const form = document.getElementById('chartForm');
        const chartType = document.getElementById('chartType');
        const yColumnGroup = document.getElementById('yColumnGroup');

        // Cambiar visibilidad del eje Y según el tipo de gráfica
        chartType.addEventListener('change', (e) => {
            if (e.target.value === 'histogram') {
                yColumnGroup.style.display = 'none';
            } else {
                yColumnGroup.style.display = 'block';
            }
            this.updateTitle();
        });

        // Actualizar título automáticamente
        document.getElementById('xColumn').addEventListener('change', () => this.updateTitle());
        document.getElementById('yColumn').addEventListener('change', () => this.updateTitle());

        // Envío del formulario
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.generateChart();
        });
    }

    /**
     * Actualiza el título automáticamente basado en la selección
     */
    updateTitle() {
        const chartType = document.getElementById('chartType').value;
        const xColumn = document.getElementById('xColumn').value;
        const yColumn = document.getElementById('yColumn').value;
        const titleInput = document.getElementById('chartTitle');

        if (!chartType || !xColumn) return;

        let autoTitle = '';
        switch (chartType) {
            case 'line':
                autoTitle = yColumn ? `${yColumn} a lo largo de ${xColumn}` : `Evolución de ${xColumn}`;
                break;
            case 'bar':
                autoTitle = yColumn ? `${yColumn} por ${xColumn}` : `Distribución de ${xColumn}`;
                break;
            case 'scatter':
                autoTitle = yColumn ? `${yColumn} vs ${xColumn}` : `Dispersión de ${xColumn}`;
                break;
            case 'histogram':
                autoTitle = `Distribución de ${xColumn}`;
                break;
        }

        if (!titleInput.value || titleInput.value === titleInput.dataset.autoTitle) {
            titleInput.value = autoTitle;
            titleInput.dataset.autoTitle = autoTitle;
        }
    }

    /**
     * Genera la gráfica según la configuración del formulario
     */
    async generateChart() {
        const formData = new FormData(document.getElementById('chartForm'));
        const chartType = document.getElementById('chartType').value;
        const xColumn = document.getElementById('xColumn').value;
        const yColumn = document.getElementById('yColumn').value;
        const title = document.getElementById('chartTitle').value || `Gráfica ${this.chartCounter + 1}`;
        const limit = parseInt(document.getElementById('dataLimit').value);

        // Validaciones
        if (!chartType || !xColumn) {
            alert('Por favor selecciona el tipo de gráfica y la columna X');
            return;
        }

        if (chartType !== 'histogram' && !yColumn) {
            alert('Por favor selecciona la columna Y');
            return;
        }

        const generateBtn = document.getElementById('generateBtn');
        generateBtn.textContent = 'Generando...';
        generateBtn.disabled = true;

        try {
            const chartConfig = {
                chart_type: chartType,
                x_column: xColumn,
                y_column: chartType === 'histogram' ? null : yColumn,
                title: title,
                limit: limit
            };

            const chartData = await apiClient.generateCustomChart(this.filename, chartConfig);
            this.renderChart(chartData);

        } catch (error) {
            console.error('Error generando gráfica:', error);
            alert('Error al generar la gráfica: ' + error.message);
        } finally {
            generateBtn.textContent = 'Generar Gráfica';
            generateBtn.disabled = false;
        }
    }

    /**
     * Renderiza una gráfica usando Chart.js
     */
    renderChart(chartData) {
        const chartsContainer = document.getElementById('chartsContainer');
        if (!chartsContainer) return;

        this.chartCounter++;
        const chartId = `chart-${this.chartCounter}`;

        // Crear contenedor para esta gráfica
        const chartWrapper = DOM.createElement('div', {
            className: 'chart-wrapper',
            id: chartId
        });

        chartWrapper.innerHTML = `
            <div class="chart-header">
                <h5>${chartData.title}</h5>
                <div class="chart-info">
                    ${chartData.total_points ? `${chartData.total_points.toLocaleString()} puntos` : ''}
                    ${chartData.total_groups ? `${chartData.total_groups.toLocaleString()} grupos` : ''}
                    ${chartData.total_values ? `${chartData.total_values.toLocaleString()} valores` : ''}
                </div>
                <button class="btn-close-chart" onclick="this.closest('.chart-wrapper').remove()">×</button>
            </div>
            <div class="chart-canvas-container">
                <canvas id="canvas-${this.chartCounter}" width="400" height="300"></canvas>
            </div>
        `;

        chartsContainer.appendChild(chartWrapper);

        // Crear la gráfica
        const canvas = document.getElementById(`canvas-${this.chartCounter}`);
        const ctx = canvas.getContext('2d');

        const chartInstance = new Chart(ctx, this.getChartConfig(chartData));
        this.chartInstances.push(chartInstance);

        // Scroll a la nueva gráfica
        chartWrapper.scrollIntoView({ behavior: 'smooth' });
    }

    /**
     * Obtiene la configuración para Chart.js según el tipo
     */
    getChartConfig(chartData) {
        const baseConfig = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: chartData.title,
                    font: {
                        size: 16,
                        weight: 'bold'
                    }
                },
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: chartData.x_label,
                        font: {
                            weight: 'bold'
                        }
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: chartData.y_label,
                        font: {
                            weight: 'bold'
                        }
                    }
                }
            }
        };

        switch (chartData.chart_type) {
            case 'line':
                return {
                    type: 'line',
                    data: {
                        datasets: [{
                            label: chartData.y_label,
                            data: chartData.data.map(item => ({ x: item.x, y: item.y })),
                            borderColor: '#2563eb',
                            backgroundColor: 'rgba(37, 99, 235, 0.1)',
                            tension: 0.1,
                            pointRadius: 2,
                            pointHoverRadius: 4
                        }]
                    },
                    options: baseConfig
                };

            case 'bar':
                return {
                    type: 'bar',
                    data: {
                        labels: chartData.data.map(item => item.x),
                        datasets: [{
                            label: chartData.y_label,
                            data: chartData.data.map(item => item.y),
                            backgroundColor: '#2563eb',
                            borderColor: '#1d4ed8',
                            borderWidth: 1
                        }]
                    },
                    options: baseConfig
                };

            case 'scatter':
                return {
                    type: 'scatter',
                    data: {
                        datasets: [{
                            label: `${chartData.y_label} vs ${chartData.x_label}`,
                            data: chartData.data.map(item => ({ x: item.x, y: item.y })),
                            backgroundColor: 'rgba(37, 99, 235, 0.6)',
                            borderColor: '#2563eb',
                            pointRadius: 3
                        }]
                    },
                    options: baseConfig
                };

            case 'histogram':
                const bins = this.createHistogramBins(chartData.data);
                return {
                    type: 'bar',
                    data: {
                        labels: bins.labels,
                        datasets: [{
                            label: 'Frecuencia',
                            data: bins.counts,
                            backgroundColor: '#2563eb',
                            borderColor: '#1d4ed8',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        ...baseConfig,
                        scales: {
                            ...baseConfig.scales,
                            x: {
                                ...baseConfig.scales.x,
                                title: {
                                    display: true,
                                    text: chartData.x_label + ' (rangos)'
                                }
                            }
                        }
                    }
                };

            default:
                return {
                    type: 'bar',
                    data: {
                        labels: ['Error'],
                        datasets: [{
                            data: [0],
                            backgroundColor: '#dc2626'
                        }]
                    },
                    options: baseConfig
                };
        }
    }

    /**
     * Crea bins para histograma
     */
    createHistogramBins(data, numBins = 15) {
        if (!data || data.length === 0) {
            return { labels: ['Sin datos'], counts: [0] };
        }

        const min = Math.min(...data);
        const max = Math.max(...data);
        const binSize = (max - min) / numBins;
        
        const bins = Array(numBins).fill(0);
        const labels = [];
        
        for (let i = 0; i < numBins; i++) {
            const binStart = min + i * binSize;
            const binEnd = min + (i + 1) * binSize;
            labels.push(`${binStart.toFixed(1)}-${binEnd.toFixed(1)}`);
        }
        
        data.forEach(value => {
            const binIndex = Math.min(Math.floor((value - min) / binSize), numBins - 1);
            bins[binIndex]++;
        });
        
        return { labels, counts: bins };
    }

    /**
     * Renderiza error
     */
    renderError(message) {
        this.container.innerHTML = `
            <div class="charts-error">
                <h4>Error</h4>
                <p>${message}</p>
                <button onclick="this.parentElement.parentElement.querySelector('.btn-refresh').click()" 
                        class="btn-secondary">Reintentar</button>
            </div>
        `;
    }

    /**
     * Limpia todas las gráficas
     */
    clear() {
        // Destruir instancias de Chart.js
        this.chartInstances.forEach(chart => {
            try {
                chart.destroy();
            } catch (error) {
                console.warn('Error destruyendo gráfica:', error);
            }
        });
        this.chartInstances = [];
        
        if (this.container) {
            this.container.innerHTML = '';
        }
        
        this.filename = null;
        this.columnsInfo = null;
        this.chartCounter = 0;
    }
}

window.ChartViewer = ChartViewer;