// Power BI Module JavaScript
const API_BASE = window.location.origin;
let currentProjects = [];
let currentProject = null;
let relationshipDiagramData = null;

// Initialize module when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    initializePowerBIModule();
});

function initializePowerBIModule() {
    setupTabNavigation();
    setupFileUpload();
    setupFormHandlers();
    loadProjects();
}

// Tab Navigation
function setupTabNavigation() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabId = button.dataset.tab;
            
            // Remove active class from all tabs and contents
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            // Add active class to clicked tab and corresponding content
            button.classList.add('active');
            document.getElementById(`${tabId}-tab`).classList.add('active');
        });
    });
}

// File Upload Setup
function setupFileUpload() {
    const uploadArea = document.getElementById('fileUploadArea');
    const fileInput = document.getElementById('parquetFiles');
    const filesList = document.getElementById('filesList');
    const selectedFiles = document.getElementById('selectedFiles');
    
    // Click to select files
    uploadArea.addEventListener('click', () => {
        fileInput.click();
    });
    
    // Drag and drop functionality
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        const files = Array.from(e.dataTransfer.files).filter(file => 
            file.name.endsWith('.parquet')
        );
        
        if (files.length > 0) {
            fileInput.files = createFileList(files);
            updateFilesList(files);
        } else {
            showNotification('Solo se aceptan archivos .parquet', 'warning');
        }
    });
    
    // File input change
    fileInput.addEventListener('change', (e) => {
        const files = Array.from(e.target.files);
        updateFilesList(files);
    });
    
    function updateFilesList(files) {
        if (files.length > 0) {
            filesList.style.display = 'block';
            selectedFiles.innerHTML = '';
            
            files.forEach(file => {
                const li = document.createElement('li');
                li.innerHTML = `
                    <strong>${file.name}</strong> 
                    (${(file.size / (1024 * 1024)).toFixed(2)} MB)
                `;
                selectedFiles.appendChild(li);
            });
        } else {
            filesList.style.display = 'none';
        }
    }
}

// Helper function to create FileList
function createFileList(files) {
    const dt = new DataTransfer();
    files.forEach(file => dt.items.add(file));
    return dt.files;
}

// Form Handlers
function setupFormHandlers() {
    const createForm = document.getElementById('createProjectForm');
    const relationshipForm = document.getElementById('relationshipForm');
    
    createForm.addEventListener('submit', handleCreateProject);
    relationshipForm.addEventListener('submit', handleSaveRelationship);
}

// Load and display projects
async function loadProjects() {
    try {
        showLoading(true);
        const response = await fetch(`${API_BASE}/power-bi/projects`);
        
        if (!response.ok) {
            throw new Error('Error loading projects');
        }
        
        currentProjects = await response.json();
        displayProjects();
        
    } catch (error) {
        showNotification('Error loading projects: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function displayProjects() {
    const grid = document.getElementById('projectsGrid');
    
    if (currentProjects.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <h3>No hay proyectos Power BI</h3>
                <p>Crea tu primer proyecto subiendo archivos Parquet</p>
                <button class="btn btn-primary" onclick="showCreateProject()">
                    Crear Proyecto
                </button>
            </div>
        `;
        return;
    }
    
    grid.innerHTML = currentProjects.map(project => `
        <div class="project-card" onclick="openProject(${project.id})">
            <div class="project-header">
                <h3>${project.name}</h3>
                <span class="project-status ${project.status}">${getStatusText(project.status)}</span>
            </div>
            <p class="project-description">${project.description || 'Sin descripción'}</p>
            <div class="project-stats">
                <div class="stat">
                    <strong>${project.tables_count}</strong> Tablas
                </div>
                <div class="stat">
                    <strong>${project.relationships_count}</strong> Relaciones
                </div>
            </div>
            <div class="project-date">
                Creado: ${new Date(project.created_at).toLocaleDateString('es-ES')}
            </div>
        </div>
    `).join('');
}

function getStatusText(status) {
    const statusMap = {
        'draft': 'Borrador',
        'processing': 'Procesando',
        'ready': 'Listo',
        'error': 'Error'
    };
    return statusMap[status] || status;
}

// Create new project
function showCreateProject() {
    // Switch to create tab
    document.querySelector('[data-tab="create"]').click();
}

async function handleCreateProject(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const files = formData.getAll('files');
    
    if (files.length === 0) {
        showNotification('Selecciona al menos un archivo Parquet', 'warning');
        return;
    }
    
    try {
        showLoading(true, 'Creando proyecto...');
        
        const response = await fetch(`${API_BASE}/power-bi/projects`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error creating project');
        }
        
        const result = await response.json();
        showNotification(result.message, 'success');
        
        // Reset form and switch to projects tab
        resetCreateForm();
        document.querySelector('[data-tab="projects"]').click();
        
        // Reload projects
        loadProjects();
        
    } catch (error) {
        showNotification('Error creating project: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function resetCreateForm() {
    document.getElementById('createProjectForm').reset();
    document.getElementById('filesList').style.display = 'none';
}

// Open project details
async function openProject(projectId) {
    try {
        showLoading(true, 'Loading project...');
        
        const response = await fetch(`${API_BASE}/power-bi/projects/${projectId}`);
        if (!response.ok) throw new Error('Error loading project');
        
        currentProject = await response.json();
        displayProjectModal();
        
    } catch (error) {
        showNotification('Error loading project: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function displayProjectModal() {
    document.getElementById('projectModalTitle').textContent = currentProject.name;
    
    const content = document.getElementById('projectModalContent');
    content.innerHTML = `
        <div class="project-tabs">
            <div class="tabs-nav">
                <button class="tab-button active" data-tab="overview">Overview</button>
                <button class="tab-button" data-tab="tables">Tablas</button>
                <button class="tab-button" data-tab="relationships">Relaciones</button>
                <button class="tab-button" data-tab="diagram">Diagrama</button>
                <button class="tab-button" data-tab="export">Exportar</button>
            </div>
            
            <div class="tab-content active" id="overview-content">
                ${renderOverviewTab()}
            </div>
            
            <div class="tab-content" id="tables-content">
                ${renderTablesTab()}
            </div>
            
            <div class="tab-content" id="relationships-content">
                ${renderRelationshipsTab()}
            </div>
            
            <div class="tab-content" id="diagram-content">
                ${renderDiagramTab()}
            </div>
            
            <div class="tab-content" id="export-content">
                ${renderExportTab()}
            </div>
        </div>
    `;
    
    // Setup modal tab navigation
    setupModalTabNavigation();
    
    // Show modal
    document.getElementById('projectModal').style.display = 'block';
}

function renderOverviewTab() {
    return `
        <div class="overview-section">
            <div class="project-info">
                <h3>${currentProject.name}</h3>
                <p>${currentProject.description || 'Sin descripción'}</p>
                <p><strong>Estado:</strong> <span class="project-status ${currentProject.status}">${getStatusText(currentProject.status)}</span></p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <h4>Tablas</h4>
                    <div class="stat-number">${currentProject.tables.length}</div>
                </div>
                <div class="stat-card">
                    <h4>Relaciones</h4>
                    <div class="stat-number">${currentProject.relationships.length}</div>
                </div>
                <div class="stat-card">
                    <h4>Total Filas</h4>
                    <div class="stat-number">${currentProject.tables.reduce((sum, t) => sum + (t.row_count || 0), 0).toLocaleString()}</div>
                </div>
            </div>
            
            <div class="actions-section">
                <button class="btn btn-primary" onclick="validateProject()">Validar Modelo</button>
                <button class="btn btn-secondary" onclick="deleteProject(${currentProject.id})" 
                        style="background: var(--danger); color: white;">
                    Eliminar Proyecto
                </button>
            </div>
        </div>
    `;
}

function renderTablesTab() {
    return `
        <div class="tables-section">
            <h3>Tablas del Proyecto (${currentProject.tables.length})</h3>
            
            ${currentProject.tables.map(table => `
                <div class="table-card">
                    <div class="table-header">
                        <h4>${table.friendly_name || table.table_name}</h4>
                        <span class="table-info">${table.row_count?.toLocaleString() || '0'} filas</span>
                    </div>
                    
                    <div class="columns-list">
                        <h5>Columnas (${table.columns.length})</h5>
                        <div class="columns-grid">
                            ${table.columns.map(col => `
                                <div class="column-item">
                                    ${col.is_key ? '<span class="column-key">🔑</span>' : ''}
                                    <strong>${col.friendly_name || col.column_name}</strong>
                                    <span class="column-type">(${col.data_type})</span>
                                    ${col.description ? `<p class="column-desc">${col.description}</p>` : ''}
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function renderRelationshipsTab() {
    return `
        <div class="relationships-section">
            <div class="section-header">
                <h3>Relaciones (${currentProject.relationships.length})</h3>
                <button class="btn btn-primary" onclick="createNewRelationship()">Nueva Relación</button>
            </div>
            
            ${currentProject.relationships.length === 0 ? 
                '<p class="empty-state">No se encontraron relaciones. Puedes crear una manualmente.</p>' :
                `<div class="relationships-list">
                    ${currentProject.relationships.map(rel => `
                        <div class="relationship-card ${rel.is_active ? 'active' : 'inactive'}">
                            <div class="relationship-header">
                                <h4>${rel.parent_table} → ${rel.child_table}</h4>
                                <div class="relationship-actions">
                                    <button class="btn btn-small" onclick="editRelationship(${rel.id})">Editar</button>
                                    <button class="btn btn-small btn-danger" onclick="deleteRelationship(${rel.id})">Eliminar</button>
                                </div>
                            </div>
                            <div class="relationship-details">
                                <span><strong>Columnas:</strong> ${rel.parent_column} → ${rel.child_column}</span>
                                <span><strong>Cardinalidad:</strong> ${rel.cardinality}</span>
                                <span><strong>Filtrado:</strong> ${rel.cross_filter_direction}</span>
                                <span><strong>Estado:</strong> ${rel.status}</span>
                            </div>
                        </div>
                    `).join('')}
                </div>`
            }
        </div>
    `;
}

function renderDiagramTab() {
    return `
        <div class="diagram-section">
            <div class="diagram-controls">
                <button class="btn btn-secondary" onclick="loadRelationshipDiagram()">Cargar Diagrama</button>
                <button class="btn btn-secondary" onclick="resetDiagramLayout()">Resetear Layout</button>
            </div>
            <div id="relationshipDiagram" class="relationship-diagram">
                <p class="diagram-placeholder">Haz clic en "Cargar Diagrama" para ver las relaciones</p>
            </div>
        </div>
    `;
}

function renderExportTab() {
    return `
        <div class="export-section">
            <h3>Exportar a Power BI</h3>
            <p>Selecciona el formato de exportación para usar en Power BI Desktop:</p>
            
            <div class="export-options">
                <div class="export-card" onclick="exportProject('pbit')">
                    <div class="export-icon">📊</div>
                    <h4>Power BI Template (.pbit)</h4>
                    <p>Archivo de plantilla que se abre directamente en Power BI Desktop</p>
                    <span class="export-status">Recomendado</span>
                </div>
                
                <div class="export-card" onclick="exportProject('json')">
                    <div class="export-icon">📄</div>
                    <h4>BIM JSON</h4>
                    <p>Modelo en formato JSON para Tabular Editor</p>
                    <span class="export-status">Avanzado</span>
                </div>
                
                <div class="export-card" onclick="exportProject('xmla')">
                    <div class="export-icon">🔧</div>
                    <h4>XMLA Script</h4>
                    <p>Script para Analysis Services</p>
                    <span class="export-status">Servidor</span>
                </div>
            </div>
            
            <div id="exportHistory" class="export-history">
                <h4>Exportaciones Recientes</h4>
                <div id="exportsList">
                    <p>Cargando...</p>
                </div>
            </div>
        </div>
    `;
}

function setupModalTabNavigation() {
    const modalTabButtons = document.querySelectorAll('#projectModalContent .tab-button');
    const modalTabContents = document.querySelectorAll('#projectModalContent .tab-content');
    
    modalTabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabId = button.dataset.tab;
            
            modalTabButtons.forEach(btn => btn.classList.remove('active'));
            modalTabContents.forEach(content => content.classList.remove('active'));
            
            button.classList.add('active');
            document.getElementById(`${tabId}-content`).classList.add('active');
            
            // Load specific tab content
            if (tabId === 'export') {
                loadExportHistory();
            }
        });
    });
}

// Relationship Management
function createNewRelationship() {
    openRelationshipModal(null);
}

function editRelationship(relationshipId) {
    const relationship = currentProject.relationships.find(r => r.id === relationshipId);
    openRelationshipModal(relationship);
}

function openRelationshipModal(relationship) {
    const modal = document.getElementById('relationshipModal');
    const title = document.getElementById('relationshipModalTitle');
    
    if (relationship) {
        title.textContent = 'Editar Relación';
        populateRelationshipForm(relationship);
    } else {
        title.textContent = 'Nueva Relación';
        document.getElementById('relationshipForm').reset();
    }
    
    // Populate table options
    populateTableOptions();
    modal.style.display = 'block';
}

function populateTableOptions() {
    const parentSelect = document.getElementById('parentTable');
    const childSelect = document.getElementById('childTable');
    
    const options = currentProject.tables.map(table => 
        `<option value="${table.id}">${table.friendly_name || table.table_name}</option>`
    ).join('');
    
    parentSelect.innerHTML = '<option value="">Seleccionar tabla...</option>' + options;
    childSelect.innerHTML = '<option value="">Seleccionar tabla...</option>' + options;
    
    // Setup column population on table change
    parentSelect.addEventListener('change', () => updateColumnOptions('parent'));
    childSelect.addEventListener('change', () => updateColumnOptions('child'));
}

function updateColumnOptions(type) {
    const tableSelect = document.getElementById(`${type}Table`);
    const columnSelect = document.getElementById(`${type}Column`);
    
    if (!tableSelect.value) {
        columnSelect.innerHTML = '<option value="">Seleccionar columna...</option>';
        return;
    }
    
    const table = currentProject.tables.find(t => t.id == tableSelect.value);
    if (!table) return;
    
    const options = table.columns.map(col => 
        `<option value="${col.column_name}">${col.friendly_name || col.column_name} (${col.data_type})</option>`
    ).join('');
    
    columnSelect.innerHTML = '<option value="">Seleccionar columna...</option>' + options;
}

function populateRelationshipForm(relationship) {
    document.getElementById('parentTable').value = relationship.parent_table_id || '';
    document.getElementById('childTable').value = relationship.child_table_id || '';
    document.getElementById('cardinality').value = relationship.cardinality;
    document.getElementById('crossFilterDirection').value = relationship.cross_filter_direction;
    document.getElementById('isActive').checked = relationship.is_active;
    
    // Trigger column updates
    updateColumnOptions('parent');
    updateColumnOptions('child');
    
    // Set column values after a brief delay to ensure options are loaded
    setTimeout(() => {
        document.getElementById('parentColumn').value = relationship.parent_column;
        document.getElementById('childColumn').value = relationship.child_column;
    }, 100);
}

async function handleSaveRelationship(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const relationshipData = {
        parent_table_id: formData.get('parentTable'),
        child_table_id: formData.get('childTable'),
        parent_column: formData.get('parentColumn'),
        child_column: formData.get('childColumn'),
        cardinality: formData.get('cardinality'),
        cross_filter_direction: formData.get('crossFilterDirection'),
        is_active: formData.get('isActive') === 'on'
    };
    
    try {
        showLoading(true, 'Guardando relación...');
        
        const response = await fetch(`${API_BASE}/power-bi/projects/${currentProject.id}/relationships`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(relationshipData)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error saving relationship');
        }
        
        showNotification('Relación guardada exitosamente', 'success');
        closeRelationshipModal();
        
        // Reload project data
        await openProject(currentProject.id);
        
    } catch (error) {
        showNotification('Error saving relationship: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// Export Functions
async function exportProject(exportType) {
    try {
        showLoading(true, `Exportando como ${exportType.toUpperCase()}...`);
        
        const response = await fetch(`${API_BASE}/power-bi/projects/${currentProject.id}/export`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                export_type: exportType
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error exporting project');
        }
        
        const result = await response.json();
        showNotification(result.message, 'success');
        
        // Reload export history
        setTimeout(loadExportHistory, 1000);
        
    } catch (error) {
        showNotification('Error exporting project: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

async function loadExportHistory() {
    try {
        const response = await fetch(`${API_BASE}/power-bi/projects/${currentProject.id}/exports`);
        if (!response.ok) return;
        
        const exports = await response.json();
        const exportsList = document.getElementById('exportsList');
        
        if (exports.length === 0) {
            exportsList.innerHTML = '<p>No hay exportaciones disponibles</p>';
            return;
        }
        
        exportsList.innerHTML = exports.map(exp => `
            <div class="export-item ${exp.export_status}">
                <div class="export-info">
                    <strong>${exp.export_type.toUpperCase()}</strong>
                    <span class="export-date">${new Date(exp.created_at).toLocaleDateString('es-ES')}</span>
                </div>
                <div class="export-actions">
                    <span class="export-status ${exp.export_status}">${getExportStatusText(exp.export_status)}</span>
                    ${exp.has_file ? `<button class="btn btn-small" onclick="downloadExport(${exp.id})">Descargar</button>` : ''}
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading export history:', error);
    }
}

function getExportStatusText(status) {
    const statusMap = {
        'processing': 'Procesando',
        'success': 'Completado',
        'error': 'Error'
    };
    return statusMap[status] || status;
}

async function downloadExport(exportId) {
    try {
        const response = await fetch(`${API_BASE}/power-bi/exports/${exportId}/download`);
        if (!response.ok) throw new Error('Error downloading file');
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        
        // Get filename from response headers
        const contentDisposition = response.headers.get('content-disposition');
        const filename = contentDisposition ? 
            contentDisposition.split('filename=')[1].replace(/"/g, '') : 
            'export_file';
        
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        
    } catch (error) {
        showNotification('Error downloading file: ' + error.message, 'error');
    }
}

// Validation
async function validateProject() {
    try {
        showLoading(true, 'Validating project...');
        
        const response = await fetch(`${API_BASE}/power-bi/projects/${currentProject.id}/validate`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error('Error validating project');
        }
        
        const result = await response.json();
        displayValidationResults(result);
        
    } catch (error) {
        showNotification('Error validating project: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function displayValidationResults(result) {
    const validationHtml = `
        <div class="validation-results">
            <h3>Resultados de Validación</h3>
            <div class="validation-summary">
                <p><strong>Total de relaciones:</strong> ${result.total_relationships}</p>
                <p><strong>Válidas:</strong> ${result.valid_relationships}</p>
                <p><strong>Inválidas:</strong> ${result.invalid_relationships}</p>
            </div>
            
            ${result.validation_details.map(detail => `
                <div class="validation-result ${detail.is_valid ? 'valid' : 'invalid'}">
                    <h4>${detail.parent_table} → ${detail.child_table}</h4>
                    <p><strong>Columnas:</strong> ${detail.parent_column} → ${detail.child_column}</p>
                    ${detail.errors.length > 0 ? `
                        <div class="validation-errors">
                            <strong>Errores:</strong>
                            <ul>
                                ${detail.errors.map(error => `<li>${error}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                    ${detail.warnings.length > 0 ? `
                        <div class="validation-warnings">
                            <strong>Advertencias:</strong>
                            <ul>
                                ${detail.warnings.map(warning => `<li>${warning}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                </div>
            `).join('')}
        </div>
    `;
    
    // Create a temporary modal or update existing content
    showNotification(
        `Validación completada: ${result.valid_relationships}/${result.total_relationships} relaciones válidas`,
        result.invalid_relationships === 0 ? 'success' : 'warning'
    );
}

// Utility Functions
function showLoading(show, message = 'Cargando...') {
    const spinner = document.getElementById('loadingSpinner');
    if (spinner) {
        if (show) {
            spinner.querySelector('p').textContent = message;
            spinner.classList.remove('hidden');
        } else {
            spinner.classList.add('hidden');
        }
    }
}

function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    const messageElement = document.getElementById('notificationMessage');
    
    if (notification && messageElement) {
        messageElement.textContent = message;
        notification.className = `notification ${type}`;
        notification.classList.remove('hidden');
        
        setTimeout(() => {
            notification.classList.add('hidden');
        }, 5000);
    }
}

function closeNotification() {
    const notification = document.getElementById('notification');
    if (notification) {
        notification.classList.add('hidden');
    }
}

function closeProjectModal() {
    document.getElementById('projectModal').style.display = 'none';
    currentProject = null;
}

function closeRelationshipModal() {
    document.getElementById('relationshipModal').style.display = 'none';
}

async function deleteProject(projectId) {
    if (!confirm('¿Estás seguro de que quieres eliminar este proyecto? Esta acción no se puede deshacer.')) {
        return;
    }
    
    try {
        showLoading(true, 'Eliminando proyecto...');
        
        const response = await fetch(`${API_BASE}/power-bi/projects/${projectId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error deleting project');
        }
        
        showNotification('Proyecto eliminado exitosamente', 'success');
        closeProjectModal();
        loadProjects();
        
    } catch (error) {
        showNotification('Error deleting project: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

async function deleteRelationship(relationshipId) {
    if (!confirm('¿Estás seguro de que quieres eliminar esta relación?')) {
        return;
    }
    
    try {
        showLoading(true, 'Eliminando relación...');
        
        const response = await fetch(`${API_BASE}/power-bi/projects/${currentProject.id}/relationships/${relationshipId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error deleting relationship');
        }
        
        showNotification('Relación eliminada exitosamente', 'success');
        
        // Reload project data
        await openProject(currentProject.id);
        
    } catch (error) {
        showNotification('Error deleting relationship: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// Relationship Diagram Functions
async function loadRelationshipDiagram() {
    try {
        showLoading(true, 'Cargando diagrama...');
        
        const response = await fetch(`${API_BASE}/power-bi/projects/${currentProject.id}/relationships/diagram`);
        if (!response.ok) throw new Error('Error loading diagram data');
        
        relationshipDiagramData = await response.json();
        renderRelationshipDiagram();
        
    } catch (error) {
        showNotification('Error loading diagram: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function renderRelationshipDiagram() {
    if (!relationshipDiagramData) return;
    
    const diagram = document.getElementById('relationshipDiagram');
    diagram.innerHTML = '';
    
    const { nodes, edges } = relationshipDiagramData;
    
    // Simple automatic layout
    const layout = calculateLayout(nodes);
    
    // Create table nodes
    nodes.forEach((node, index) => {
        const position = layout[index];
        const tableNode = createTableNode(node, position);
        diagram.appendChild(tableNode);
    });
    
    // Create relationship lines
    edges.forEach(edge => {
        const sourceNode = nodes.find(n => n.id === edge.source);
        const targetNode = nodes.find(n => n.id === edge.target);
        
        if (sourceNode && targetNode) {
            const sourcePos = layout[nodes.indexOf(sourceNode)];
            const targetPos = layout[nodes.indexOf(targetNode)];
            
            const relationshipLine = createRelationshipLine(
                sourcePos, targetPos, edge
            );
            diagram.appendChild(relationshipLine);
        }
    });
}

function calculateLayout(nodes) {
    // Simple circular layout
    const centerX = 400;
    const centerY = 300;
    const radius = Math.min(centerX, centerY) - 150;
    
    return nodes.map((node, index) => {
        const angle = (2 * Math.PI * index) / nodes.length;
        return {
            x: centerX + radius * Math.cos(angle) - 100,
            y: centerY + radius * Math.sin(angle) - 100
        };
    });
}

function createTableNode(node, position) {
    const tableDiv = document.createElement('div');
    tableDiv.className = 'table-node';
    tableDiv.style.left = `${position.x}px`;
    tableDiv.style.top = `${position.y}px`;
    
    const keyColumns = node.columns.filter(col => col.is_key);
    const regularColumns = node.columns.filter(col => !col.is_key).slice(0, 5);
    
    tableDiv.innerHTML = `
        <div class="table-header">
            ${node.label}
            <small>(${node.row_count?.toLocaleString() || '0'} filas)</small>
        </div>
        <div class="table-columns">
            ${keyColumns.map(col => `
                <div class="column-item">
                    <span class="column-key">🔑</span>
                    <strong>${col.friendly_name || col.name}</strong>
                    <span class="column-type">${col.data_type}</span>
                </div>
            `).join('')}
            ${regularColumns.map(col => `
                <div class="column-item">
                    <span>${col.friendly_name || col.name}</span>
                    <span class="column-type">${col.data_type}</span>
                </div>
            `).join('')}
            ${node.columns.length > (keyColumns.length + regularColumns.length) ? 
                `<div class="column-item">... y ${node.columns.length - keyColumns.length - regularColumns.length} más</div>` : 
                ''
            }
        </div>
    `;
    
    // Make draggable
    makeNodeDraggable(tableDiv);
    
    return tableDiv;
}

function createRelationshipLine(sourcePos, targetPos, edge) {
    const line = document.createElement('div');
    line.className = 'relationship-line';
    
    const deltaX = targetPos.x - sourcePos.x;
    const deltaY = targetPos.y - sourcePos.y;
    const length = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
    const angle = Math.atan2(deltaY, deltaX) * (180 / Math.PI);
    
    line.style.width = `${length}px`;
    line.style.left = `${sourcePos.x + 100}px`;
    line.style.top = `${sourcePos.y + 50}px`;
    line.style.transform = `rotate(${angle}deg)`;
    line.style.transformOrigin = '0 50%';
    
    // Add arrow
    const arrow = document.createElement('div');
    arrow.className = 'relationship-arrow';
    line.appendChild(arrow);
    
    // Add tooltip
    line.title = `${edge.source_column} → ${edge.target_column} (${edge.cardinality})`;
    
    return line;
}

function makeNodeDraggable(element) {
    let isDragging = false;
    let startX, startY, initialX, initialY;
    
    element.addEventListener('mousedown', (e) => {
        isDragging = true;
        startX = e.clientX;
        startY = e.clientY;
        initialX = parseInt(element.style.left, 10);
        initialY = parseInt(element.style.top, 10);
        
        element.style.cursor = 'grabbing';
        e.preventDefault();
    });
    
    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        
        const deltaX = e.clientX - startX;
        const deltaY = e.clientY - startY;
        
        element.style.left = `${initialX + deltaX}px`;
        element.style.top = `${initialY + deltaY}px`;
    });
    
    document.addEventListener('mouseup', () => {
        if (isDragging) {
            isDragging = false;
            element.style.cursor = 'move';
        }
    });
    
    element.style.cursor = 'move';
}

function resetDiagramLayout() {
    if (relationshipDiagramData) {
        renderRelationshipDiagram();
        showNotification('Layout del diagrama reiniciado', 'success');
    }
}

// Modal window click handling
window.addEventListener('click', (event) => {
    const projectModal = document.getElementById('projectModal');
    const relationshipModal = document.getElementById('relationshipModal');
    
    if (event.target === projectModal) {
        closeProjectModal();
    }
    
    if (event.target === relationshipModal) {
        closeRelationshipModal();
    }
});

// Initialize tooltips and other interactive elements
document.addEventListener('DOMContentLoaded', () => {
    // Add keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Escape key closes modals
        if (e.key === 'Escape') {
            const projectModal = document.getElementById('projectModal');
            const relationshipModal = document.getElementById('relationshipModal');
            
            if (projectModal.style.display === 'block') {
                closeProjectModal();
            }
            
            if (relationshipModal.style.display === 'block') {
                closeRelationshipModal();
            }
        }
    });
});

// Auto-refresh project status for processing projects
function startStatusPolling() {
    const processingProjects = currentProjects.filter(p => p.status === 'processing');
    
    if (processingProjects.length > 0) {
        setTimeout(() => {
            loadProjects().then(() => {
                startStatusPolling();
            });
        }, 5000); // Check every 5 seconds
    }
}

// Start polling when projects are loaded
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(startStatusPolling, 1000);
});