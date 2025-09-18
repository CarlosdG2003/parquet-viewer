let currentFileColumns = [];
let hasUnsavedChanges = false;
let currentFileName = '';

document.addEventListener('DOMContentLoaded', () => {
    initColumnsAdmin();
});

function initColumnsAdmin() {
    loadAvailableFiles();
    setupGlobalListeners();
}

function setupGlobalListeners() {
    document.getElementById('fileSelectForColumns')?.addEventListener('change', loadFileColumns);
    document.getElementById('saveColumnsBtn')?.addEventListener('click', saveAllColumnChanges);
    document.getElementById('showAllColumnsBtn')?.addEventListener('click', showAllColumns);
    document.getElementById('hideAllColumnsBtn')?.addEventListener('click', hideAllColumns);
    document.getElementById('resetAllColumnsBtn')?.addEventListener('click', resetAllColumnNames);
}

// --- Cargar archivos disponibles ---
async function loadAvailableFiles() {
    try {
        const response = await fetch('/admin/metadata');
        const metadata = await response.json();

        const select = document.getElementById('fileSelectForColumns');
        if (!select) return;

        select.innerHTML = '<option value="">Seleccionar archivo...</option>';
        metadata.forEach(file => {
            const option = document.createElement('option');
            option.value = file.filename;
            option.textContent = `${file.filename} (${file.title || 'Sin título'})`;
            select.appendChild(option);
        });

    } catch (e) {
        showNotification('Error cargando archivos: ' + e.message, 'error');
    }
}

// --- Cargar columnas del archivo seleccionado ---
async function loadFileColumns() {
    const filename = document.getElementById('fileSelectForColumns')?.value;
    if (!filename) return showNotification('Selecciona un archivo primero', 'warning');

    currentFileName = filename;
    showLoadingSpinner();

    try {
        const res = await fetch(`/admin/files/${filename}/columns`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        currentFileColumns = data.columns;
        renderFileColumnsInfo(data);
        renderColumnsList();
        showColumnsInterface();

    } catch (e) {
        showNotification('Error cargando columnas: ' + e.message, 'error');
    } finally {
        hideLoadingSpinner();
    }
}

// --- Renderizar info del archivo ---
function renderFileColumnsInfo(data) {
    document.getElementById('currentFileName').textContent = data.filename;
    document.getElementById('totalColumnsCount').textContent = data.total_columns;

    const visibleCount = data.columns.filter(c => c.is_visible).length;
    const customizedCount = data.columns.filter(c => c.has_metadata).length;

    document.getElementById('visibleColumnsCount').textContent = visibleCount;
    document.getElementById('customizedColumnsCount').textContent = customizedCount;

    document.getElementById('fileColumnsInfo')?.classList.remove('hidden');
}

// --- Renderizar lista de columnas ---
function renderColumnsList() {
    const container = document.getElementById('columnsContainer');
    if (!container) return;

    container.innerHTML = '';
    if (currentFileColumns.length === 0) {
        container.innerHTML = '<div class="empty-state">No se encontraron columnas</div>';
        return;
    }

    currentFileColumns.forEach((col, idx) => container.appendChild(createColumnRow(col, idx)));
}

function createColumnRow(column, index) {
    const row = document.createElement('div');
    row.className = 'column-row';
    row.dataset.originalName = column.original_name;

    row.innerHTML = `
        <div class="col-order"><span class="order-handle" title="Arrastrar para reordenar">${index + 1}</span></div>
        <div class="col-visible"><input type="checkbox" ${column.is_visible ? 'checked' : ''}></div>
        <div class="col-original"><code class="original-name">${column.original_name}</code></div>
        <div class="col-display"><input type="text" value="${column.display_name}" placeholder="Nombre para mostrar" class="display-name-input"></div>
        <div class="col-description"><input type="text" value="${column.description || ''}" placeholder="Descripción opcional" class="description-input"></div>
        <div class="col-type"><span class="type-badge">${column.data_type}</span></div>
        <div class="col-actions"><button class="btn-small btn-reset" title="Resetear">Reset</button></div>
    `;

    // Listeners internos
    row.querySelectorAll('input').forEach(input => {
        input.addEventListener('input', markUnsavedChanges);
        input.addEventListener('change', markUnsavedChanges);
    });

    row.querySelector('.btn-reset')?.addEventListener('click', () => resetColumn(column.original_name));
    return row;
}

// --- Guardar cambios ---
function markUnsavedChanges() {
    hasUnsavedChanges = true;
    document.getElementById('unsavedChangesIndicator')?.classList.remove('hidden');
    document.getElementById('saveColumnsBtn')?.removeAttribute('disabled');
}

async function saveAllColumnChanges() {
    if (!hasUnsavedChanges) return;
    
    const saveBtn = document.getElementById('saveColumnsBtn');
    const originalText = saveBtn.textContent;
    
    // Estado de carga
    saveBtn.classList.add('btn-loading');
    saveBtn.textContent = 'Guardando...';
    saveBtn.disabled = true;
    
    const updates = collectColumnChanges();

    try {
        const res = await fetch(`/admin/files/${currentFileName}/columns/bulk-update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates)
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const result = await res.json();
        
        // Animación de éxito
        saveBtn.classList.remove('btn-loading');
        saveBtn.classList.add('btn-success');
        saveBtn.textContent = '¡Guardado!';
        
        // Animar filas actualizadas
        document.querySelectorAll('.column-row').forEach(row => {
            row.classList.add('updated');
            setTimeout(() => row.classList.remove('updated'), 800);
        });
        
        showNotification(`Cambios guardados: ${result.results.updated} actualizadas, ${result.results.created} creadas`, 'success');

        await loadFileColumns();
        hasUnsavedChanges = false;
        document.getElementById('unsavedChangesIndicator')?.classList.add('hidden');
        
        setTimeout(() => {
            saveBtn.classList.remove('btn-success');
            saveBtn.textContent = originalText;
            saveBtn.disabled = true;
        }, 2000);

    } catch (e) {
        showNotification('Error guardando cambios: ' + e.message, 'error');
        saveBtn.classList.remove('btn-loading');
        saveBtn.textContent = originalText;
        saveBtn.disabled = false;
    }
}

function collectColumnChanges() {
    return Array.from(document.querySelectorAll('.column-row')).map((row, idx) => {
        return {
            original_column_name: row.dataset.originalName,
            display_name: row.querySelector('.display-name-input').value.trim() || row.dataset.originalName,
            description: row.querySelector('.description-input').value.trim() || null,
            is_visible: row.querySelector('input[type="checkbox"]').checked,
            sort_order: idx
        };
    });
}

// --- Acciones rápidas ---
function showColumnsInterface() {
    document.getElementById('columnsToolbar')?.classList.remove('hidden');
    document.getElementById('columnsList')?.classList.remove('hidden');
}

function showAllColumns() { document.querySelectorAll('.column-row input[type="checkbox"]').forEach(cb => cb.checked = true); markUnsavedChanges(); }
function hideAllColumns() { document.querySelectorAll('.column-row input[type="checkbox"]').forEach(cb => cb.checked = false); markUnsavedChanges(); }
function resetAllColumnNames() {
    if (!confirm('¿Resetear todos los nombres de columnas a sus valores originales?')) return;
    document.querySelectorAll('.column-row').forEach(row => {
        const original = row.querySelector('.original-name').textContent;
        row.querySelector('.display-name-input').value = original;
        row.querySelector('.description-input').value = '';
        row.querySelector('input[type="checkbox"]').checked = true;
    });
    markUnsavedChanges();
}
function resetColumn(originalName) {
    const row = document.querySelector(`[data-original-name="${originalName}"]`);
    if (!row) return;
    const original = row.querySelector('.original-name').textContent;
    row.querySelector('.display-name-input').value = original;
    row.querySelector('.description-input').value = '';
    row.querySelector('input[type="checkbox"]').checked = true;
    markUnsavedChanges();
}

// --- Sincronización de columnas ---
async function syncFileColumns() {
    if (!currentFileName) return;
    showLoadingSpinner();
    try {
        const res = await fetch(`/admin/files/${currentFileName}/columns/sync`, { method: 'POST' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const result = await res.json();
        showNotification(`Sincronización completada: ${result.sync_results.created} nuevas, ${result.sync_results.hidden} ocultas`, 'success');
        await loadFileColumns();
    } catch (e) { showNotification('Error sincronizando: ' + e.message, 'error'); }
    finally { hideLoadingSpinner(); }
}

// --- Modales ---
function showImportDialog() { document.getElementById('importConfigModal')?.classList.add('visible'); }
function closeImportModal() { document.getElementById('importConfigModal')?.classList.remove('visible'); }
function closePreviewModal() { document.getElementById('previewModal')?.classList.remove('visible'); }

// --- Utils compartidos (se pueden mover a admin.js) ---
function showLoadingSpinner() { document.getElementById('loadingSpinner')?.classList.remove('hidden'); }
function hideLoadingSpinner() { document.getElementById('loadingSpinner')?.classList.add('hidden'); }
function showNotification(message, type = 'info') {
    const notif = document.getElementById('notification');
    const msgEl = document.getElementById('notificationMessage');
    if (!notif || !msgEl) return;
    msgEl.textContent = message;
    notif.className = `notification ${type}`;
    notif.classList.remove('hidden');
    setTimeout(() => notif.classList.add('hidden'), 5000);
}

function toggleAdvancedOptions() {
    const menu = document.getElementById('advancedOptionsMenu');
    if (menu) {
        menu.classList.toggle('hidden');
    }
}

// Cerrar dropdown al hacer clic fuera
document.addEventListener('click', (event) => {
    const dropdown = document.querySelector('.dropdown');
    const menu = document.getElementById('advancedOptionsMenu');
    
    if (dropdown && menu && !dropdown.contains(event.target)) {
        menu.classList.add('hidden');
    }
});

// Funciones placeholder para las opciones del menú
function validateColumnConfig() {
    alert('Función de validación en desarrollo');
}

function backupCurrentConfig() {
    alert('Función de backup en desarrollo');
}

// Vincular el evento después de que se cargue el DOM
document.addEventListener('DOMContentLoaded', () => {
    const advancedBtn = document.getElementById('advancedOptionsBtn');
    if (advancedBtn) {
        advancedBtn.addEventListener('click', toggleAdvancedOptions);
    }
});