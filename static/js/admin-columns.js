// static/js/admin-columns.js
// Gestión de columnas para el panel de administrador

let currentFileColumns = [];
let hasUnsavedChanges = false;
let currentFileName = '';

// Inicializar cuando la página carga
document.addEventListener('DOMContentLoaded', function() {
    loadAvailableFiles();
});

async function loadAvailableFiles() {
    try {
        // Cargar archivos disponibles para el selector
        const response = await fetch('/admin/metadata');
        const metadata = await response.json();
        
        const fileSelect = document.getElementById('fileSelectForColumns');
        fileSelect.innerHTML = '<option value="">Seleccionar archivo...</option>';
        
        metadata.forEach(file => {
            const option = document.createElement('option');
            option.value = file.filename;
            option.textContent = `${file.filename} (${file.title || 'Sin título'})`;
            fileSelect.appendChild(option);
        });
        
    } catch (error) {
        showNotification('Error cargando archivos: ' + error.message, 'error');
    }
}

async function loadFileColumns() {
    const filename = document.getElementById('fileSelectForColumns').value;
    if (!filename) {
        showNotification('Selecciona un archivo primero', 'warning');
        return;
    }

    currentFileName = filename;
    showLoadingSpinner();

    try {
        const response = await fetch(`/admin/files/${filename}/columns`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        currentFileColumns = data.columns;
        
        renderFileColumnsInfo(data);
        renderColumnsList();
        showColumnsInterface();
        
    } catch (error) {
        showNotification('Error cargando columnas: ' + error.message, 'error');
    } finally {
        hideLoadingSpinner();
    }
}

function renderFileColumnsInfo(data) {
    document.getElementById('currentFileName').textContent = data.filename;
    document.getElementById('totalColumnsCount').textContent = data.total_columns;
    
    const visibleCount = data.columns.filter(col => col.is_visible).length;
    const customizedCount = data.columns.filter(col => col.has_metadata).length;
    
    document.getElementById('visibleColumnsCount').textContent = visibleCount;
    document.getElementById('customizedColumnsCount').textContent = customizedCount;
    
    document.getElementById('fileColumnsInfo').classList.remove('hidden');
}

function renderColumnsList() {
    const container = document.getElementById('columnsContainer');
    container.innerHTML = '';

    if (currentFileColumns.length === 0) {
        container.innerHTML = '<div class="empty-state">No se encontraron columnas</div>';
        return;
    }

    currentFileColumns.forEach((column, index) => {
        const columnRow = createColumnRow(column, index);
        container.appendChild(columnRow);
    });
}

function createColumnRow(column, index) {
    const row = document.createElement('div');
    row.className = 'column-row';
    row.dataset.originalName = column.original_name;
    
    row.innerHTML = `
        <div class="col-order">
            <span class="order-handle" title="Arrastrar para reordenar">${index + 1}</span>
        </div>
        <div class="col-visible">
            <input type="checkbox" 
                   ${column.is_visible ? 'checked' : ''} 
                   onchange="markUnsavedChanges()"
                   title="Mostrar/ocultar columna">
        </div>
        <div class="col-original">
            <code class="original-name">${column.original_name}</code>
        </div>
        <div class="col-display">
            <input type="text" 
                   value="${column.display_name}" 
                   placeholder="Nombre para mostrar"
                   onchange="markUnsavedChanges()"
                   oninput="markUnsavedChanges()"
                   class="display-name-input">
        </div>
        <div class="col-description">
            <input type="text" 
                   value="${column.description || ''}" 
                   placeholder="Descripción opcional"
                   onchange="markUnsavedChanges()"
                   oninput="markUnsavedChanges()"
                   class="description-input">
        </div>
        <div class="col-type">
            <span class="type-badge">${column.data_type}</span>
        </div>
        <div class="col-actions">
            <button onclick="resetColumn('${column.original_name}')" 
                    class="btn-small btn-reset" 
                    title="Resetear a valores originales">
                Reset
            </button>
        </div>
    `;

    return row;
}

function showColumnsInterface() {
    document.getElementById('columnsToolbar').classList.remove('hidden');
    document.getElementById('columnsList').classList.remove('hidden');
}

function markUnsavedChanges() {
    hasUnsavedChanges = true;
    document.getElementById('unsavedChangesIndicator').classList.remove('hidden');
    document.getElementById('saveColumnsBtn').disabled = false;
}

async function saveAllColumnChanges() {
    if (!hasUnsavedChanges) return;

    const columnsUpdates = collectColumnChanges();
    showLoadingSpinner();

    try {
        const response = await fetch(`/admin/files/${currentFileName}/columns/bulk-update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(columnsUpdates)
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const result = await response.json();
        
        showNotification(
            `Cambios guardados: ${result.results.updated} actualizadas, ${result.results.created} creadas`, 
            'success'
        );
        
        // Recargar columnas
        await loadFileColumns();
        
        hasUnsavedChanges = false;
        document.getElementById('unsavedChangesIndicator').classList.add('hidden');
        document.getElementById('saveColumnsBtn').disabled = true;
        
    } catch (error) {
        showNotification('Error guardando cambios: ' + error.message, 'error');
    } finally {
        hideLoadingSpinner();
    }
}

function collectColumnChanges() {
    const updates = [];
    const rows = document.querySelectorAll('.column-row');
    
    rows.forEach((row, index) => {
        const originalName = row.dataset.originalName;
        const displayName = row.querySelector('.display-name-input').value.trim();
        const description = row.querySelector('.description-input').value.trim();
        const isVisible = row.querySelector('input[type="checkbox"]').checked;
        
        updates.push({
            original_column_name: originalName,
            display_name: displayName || originalName,
            description: description || null,
            is_visible: isVisible,
            sort_order: index
        });
    });
    
    return updates;
}

// Resto de funciones...
async function syncFileColumns() {
    if (!currentFileName) return;
    
    showLoadingSpinner();
    
    try {
        const response = await fetch(`/admin/files/${currentFileName}/columns/sync`, {
            method: 'POST'
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const result = await response.json();
        
        showNotification(
            `Sincronización completada: ${result.sync_results.created} nuevas, ${result.sync_results.hidden} ocultas`,
            'success'
        );
        
        await loadFileColumns();
        
    } catch (error) {
        showNotification('Error sincronizando: ' + error.message, 'error');
    } finally {
        hideLoadingSpinner();
    }
}

function showAllColumns() {
    document.querySelectorAll('.column-row input[type="checkbox"]').forEach(checkbox => {
        checkbox.checked = true;
    });
    markUnsavedChanges();
}

function hideAllColumns() {
    document.querySelectorAll('.column-row input[type="checkbox"]').forEach(checkbox => {
        checkbox.checked = false;
    });
    markUnsavedChanges();
}

function resetAllColumnNames() {
    if (!confirm('¿Resetear todos los nombres de columnas a sus valores originales?')) return;
    
    document.querySelectorAll('.column-row').forEach(row => {
        const originalName = row.querySelector('.original-name').textContent;
        row.querySelector('.display-name-input').value = originalName;
        row.querySelector('.description-input').value = '';
        row.querySelector('input[type="checkbox"]').checked = true;
    });
    
    markUnsavedChanges();
}

function resetColumn(originalName) {
    const row = document.querySelector(`[data-original-name="${originalName}"]`);
    if (!row) return;
    
    row.querySelector('.display-name-input').value = originalName;
    row.querySelector('.description-input').value = '';
    row.querySelector('input[type="checkbox"]').checked = true;
    
    markUnsavedChanges();
}

// Funciones de modal y utilidades
function showImportDialog() {
    document.getElementById('importConfigModal').style.display = 'block';
}

function closeImportModal() {
    document.getElementById('importConfigModal').style.display = 'none';
}

function closePreviewModal() {
    document.getElementById('previewModal').style.display = 'none';
}

// Funciones auxiliares que deberían estar en admin.js
function showLoadingSpinner() {
    document.getElementById('loadingSpinner').classList.remove('hidden');
}

function hideLoadingSpinner() {
    document.getElementById('loadingSpinner').classList.add('hidden');
}

function showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');
    const messageElement = document.getElementById('notificationMessage');
    
    messageElement.textContent = message;
    notification.className = `notification ${type}`;
    notification.classList.remove('hidden');
    
    setTimeout(() => {
        notification.classList.add('hidden');
    }, 5000);
}