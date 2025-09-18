const API_BASE = window.location.origin;
let currentEditingFile = null;

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM cargado, inicializando admin...');
    loadCurrentUser();
    showSection('dashboard');
    setupForm();
});

// --- Formulario ---
function setupForm() {
    const form = document.getElementById('metadataForm');
    if (form) form.addEventListener('submit', handleFormSubmit);
}

// --- Navegación ---
function showSection(sectionName) {
    const sections = document.querySelectorAll('.admin-section');
    sections.forEach(sec => sec.classList.add('hidden'));

    const targetSection = document.getElementById(sectionName + 'Section');
    if (targetSection) targetSection.classList.remove('hidden');

    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    const btn = document.querySelector(`.nav-btn[data-section="${sectionName}"]`);
    if (btn) btn.classList.add('active');

    switch(sectionName) {
        case 'dashboard': loadDashboard(); break;
        case 'metadata': loadMetadataList(); break;
        case 'files': loadFilesWithoutMetadata(); break;
    }
}

// --- Usuario ---
async function loadCurrentUser() {
    try {
        const res = await fetch(`${API_BASE}/admin/user-info`, { credentials: 'include' });
        if (!res.ok) throw new Error(res.statusText);
        const user = await res.json();
        document.getElementById('adminUser').textContent = user.username;
    } catch (e) {
        console.error('Error cargando usuario:', e);
    }
}

// --- Dashboard ---
async function loadDashboard() {
    showLoading(true);
    try {
        const res = await fetch(`${API_BASE}/admin/dashboard`, { credentials: 'include' });
        if (!res.ok) throw new Error(res.statusText);
        const data = await res.json();
        updateDashboardUI(data);
    } catch (e) {
        showNotification('Error cargando dashboard: ' + e.message, 'error');
    } finally { showLoading(false); }
}

function updateDashboardUI(data) {
    document.getElementById('totalFiles').textContent = data.total_files || '0';
    document.getElementById('filesWithMetadata').textContent = data.files_with_metadata || '0';
    document.getElementById('filesWithoutMetadata').textContent = data.files_without_metadata || '0';
    document.getElementById('lastUpdated').textContent = data.last_updated 
        ? new Date(data.last_updated).toLocaleDateString('es-ES') : 'Nunca';

    const activityList = document.getElementById('recentActivity');
    if (activityList) {
        activityList.innerHTML = (data.recent_activity || []).length > 0 
            ? data.recent_activity.map(a => `
                <div class="activity-item">
                    <strong>${a.changed_by}</strong> modificó <em>${a.field_changed}</em>
                    - ${new Date(a.changed_at).toLocaleString('es-ES')}
                </div>`).join('')
            : '<div class="activity-item">No hay actividad reciente</div>';
    }
}

// --- Archivos sin metadatos ---
async function loadFilesWithoutMetadata() {
    showLoading(true);
    try {
        const res = await fetch(`${API_BASE}/admin/files-without-metadata`, { credentials: 'include' });
        if (!res.ok) throw new Error(res.statusText);
        const files = await res.json();
        updateFilesWithoutMetadataUI(files);
    } catch (e) {
        showNotification('Error cargando archivos: ' + e.message, 'error');
    } finally { showLoading(false); }
}

function updateFilesWithoutMetadataUI(files) {
    const container = document.getElementById('filesWithoutMetadataList');
    if (!container) return;
    if (files.length === 0) {
        container.innerHTML = '<p class="info-text">Todos los archivos tienen metadatos.</p>';
        return;
    }

    container.innerHTML = files.map(f => `
        <div class="file-card">
            <h4>${f.filename}</h4>
            <p>Tamaño: ${f.size_mb} MB</p>
            <p>Modificado: ${new Date(f.modified).toLocaleDateString('es-ES')}</p>
            <button onclick="createMetadataForFile('${f.filename}')" class="btn btn-primary">Crear Metadatos</button>
        </div>
    `).join('');
}

// --- Lista de metadatos ---
async function loadMetadataList() {
    showLoading(true);
    try {
        const res = await fetch(`${API_BASE}/admin/metadata`, { credentials: 'include' });
        if (!res.ok) throw new Error(res.statusText);
        const data = await res.json();
        updateMetadataTable(data);
    } catch (e) {
        showNotification('Error cargando metadatos: ' + e.message, 'error');
    } finally { showLoading(false); }
}

function updateMetadataTable(list) {
    const tbody = document.getElementById('metadataTableBody');
    if (!tbody) return;
    if (list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7">No hay metadatos</td></tr>';
        return;
    }

    tbody.innerHTML = list.map(m => `
        <tr>
            <td><code>${m.filename}</code></td>
            <td>${m.title}</td>
            <td>${m.responsible || '-'}</td>
            <td>${translatePermission(m.permissions)}</td>
            <td>${translateFrequency(m.frequency || '-')}</td>
            <td>${new Date(m.updated_at).toLocaleDateString('es-ES')}</td>
            <td>
                <button onclick="editMetadata('${m.filename}')" class="btn btn-primary btn-sm">Editar</button>
                <button onclick="deleteMetadata('${m.filename}')" class="btn btn-danger btn-sm">Eliminar</button>
            </td>
        </tr>
    `).join('');
}

// --- Utils ---
function showLoading(show) {
    const spinner = document.getElementById('loadingSpinner');
    if (spinner) spinner.classList.toggle('hidden', !show);
}

function showNotification(message, type='success') {
    const notification = document.getElementById('notification');
    const msg = document.getElementById('notificationMessage');
    if (notification && msg) {
        // Limpiar clases anteriores
        notification.className = `notification ${type}`;
        notification.classList.remove('hiding');
        
        msg.textContent = message;
        notification.classList.remove('hidden');
        
        // Auto-ocultar con animación
        setTimeout(() => {
            notification.classList.add('hiding');
            setTimeout(() => {
                notification.classList.add('hidden');
                notification.classList.remove('hiding');
            }, 300);
        }, 4000);
    }
}

function translateFrequency(f) {
    return {
        'daily':'Diaria','weekly':'Semanal','monthly':'Mensual',
        'quarterly':'Trimestral','yearly':'Anual','on-demand':'Bajo demanda'
    }[f] || f;
}

function translatePermission(p) {
    return { 'public':'Público','internal':'Interno','confidential':'Confidencial' }[p] || p;
}

// Función para crear metadatos de un archivo específico
function createMetadataForFile(filename) {
    currentEditingFile = null;
    document.getElementById('modalTitle').textContent = 'Crear Metadatos';
    document.getElementById('submitBtn').textContent = 'Crear Metadatos';
    resetMetadataForm();
    
    // Pre-seleccionar el archivo
    const filenameSelect = document.getElementById('filename');
    if (filenameSelect) {
        filenameSelect.innerHTML = `<option value="${filename}" selected>${filename}</option>`;
        filenameSelect.disabled = true;
    }
    
    showModal();
}

// Función para mostrar el formulario de creación general
function showCreateForm() {
    currentEditingFile = null;
    document.getElementById('modalTitle').textContent = 'Crear Metadatos';
    document.getElementById('submitBtn').textContent = 'Crear Metadatos';
    resetMetadataForm();
    loadFilesForSelect();
    showModal();
}

// Función para editar metadatos existentes
async function editMetadata(filename) {
    showLoading(true);
    try {
        const res = await fetch(`${API_BASE}/admin/metadata/${filename}`, {
            credentials: 'include'
        });
        
        if (!res.ok) throw new Error('Error cargando metadatos');
        
        const data = await res.json();
        
        currentEditingFile = filename;
        document.getElementById('modalTitle').textContent = 'Editar Metadatos';
        document.getElementById('submitBtn').textContent = 'Actualizar Metadatos';
        
        // Llenar el formulario con los datos existentes
        populateForm(data);
        showModal();
        
    } catch (error) {
        showNotification('Error cargando metadatos: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// Función para eliminar metadatos
async function deleteMetadata(filename) {
    if (!confirm(`¿Estás seguro de que quieres eliminar los metadatos de "${filename}"?`)) {
        return;
    }
    
    showLoading(true);
    try {
        const res = await fetch(`${API_BASE}/admin/metadata/${filename}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (!res.ok) throw new Error('Error eliminando metadatos');
        
        showNotification('Metadatos eliminados correctamente');
        loadMetadataList(); // Recargar la lista
        
    } catch (error) {
        showNotification('Error eliminando metadatos: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// === FUNCIONES DE MODAL ===

function showModal() {
    const modal = document.getElementById('metadataModal');
    const modalContent = modal?.querySelector('.modal-content');
    
    if (modal && modalContent) {
        modal.style.display = 'block';
        modal.classList.add('showing');
        modalContent.classList.add('showing');
        
        // Limpiar clases después de la animación
        setTimeout(() => {
            modal.classList.remove('showing');
            modalContent.classList.remove('showing');
        }, 300);
    }
}

function closeModal() {
    const modal = document.getElementById('metadataModal');
    if (modal) {
        modal.style.display = 'none';
    }
    resetMetadataForm();
}

function resetMetadataForm() {
    const form = document.getElementById('metadataForm');
    if (form) {
        form.reset();
    }
    
    // Rehabilitar el selector de archivo
    const filenameSelect = document.getElementById('filename');
    if (filenameSelect) {
        filenameSelect.disabled = false;
        filenameSelect.innerHTML = '<option value="">Seleccionar archivo...</option>';
    }
    
    currentEditingFile = null;
}

function populateForm(data) {
    // Llenar el formulario con los datos para editar
    document.getElementById('filename').innerHTML = `<option value="${data.filename}" selected>${data.filename}</option>`;
    document.getElementById('filename').disabled = true;
    document.getElementById('title').value = data.title || '';
    document.getElementById('description').value = data.description || '';
    document.getElementById('responsible').value = data.responsible || '';
    document.getElementById('frequency').value = data.frequency || '';
    document.getElementById('permissions').value = data.permissions || 'public';
    document.getElementById('tags').value = data.tags ? data.tags.join(', ') : '';
}

async function loadFilesForSelect() {
    try {
        const res = await fetch(`${API_BASE}/admin/files-without-metadata`, {
            credentials: 'include'
        });
        
        if (res.ok) {
            const files = await res.json();
            const select = document.getElementById('filename');
            if (select) {
                select.innerHTML = '<option value="">Seleccionar archivo...</option>' +
                    files.map(file => `<option value="${file.filename}">${file.filename}</option>`).join('');
                select.disabled = false;
            }
        }
    } catch (error) {
        console.error('Error loading files:', error);
    }
}

async function handleFormSubmit(e) {
    e.preventDefault();
    
    const submitBtn = document.getElementById('submitBtn');
    const originalText = submitBtn.textContent;
    
    // Aplicar estado de carga
    submitBtn.classList.add('btn-loading');
    submitBtn.textContent = 'Procesando...';
    submitBtn.disabled = true;
    
    // Obtener valores directamente por ID
    const data = {
        filename: document.getElementById('filename').value,
        title: document.getElementById('title').value,
        description: document.getElementById('description').value,
        responsible: document.getElementById('responsible').value,
        frequency: document.getElementById('frequency').value,
        permissions: document.getElementById('permissions').value,
        tags: document.getElementById('tags').value ? 
            document.getElementById('tags').value.split(',').map(t => t.trim()).filter(t => t) : []
    };
    
    if (!data.filename || !data.title) {
        showNotification('Por favor completa los campos obligatorios (Archivo y Título)', 'error');
        resetSubmitButton(submitBtn, originalText);
        return;
    }
    
    try {
        const url = currentEditingFile 
            ? `${API_BASE}/admin/metadata/${currentEditingFile}`
            : `${API_BASE}/admin/metadata`;
            
        const method = currentEditingFile ? 'PUT' : 'POST';
        
        const res = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify(data)
        });
        
        if (!res.ok) {
            const errorData = await res.json();
            throw new Error(errorData.detail || 'Error guardando metadatos');
        }
        
        // Animación de éxito
        submitBtn.classList.remove('btn-loading');
        submitBtn.classList.add('btn-success');
        submitBtn.textContent = '¡Guardado!';
        
        showNotification(
            currentEditingFile ? 'Metadatos actualizados correctamente' : 'Metadatos creados correctamente',
            'success'
        );
        
        setTimeout(() => {
            closeModal();
            loadMetadataList();
            if (!currentEditingFile) {
                loadFilesWithoutMetadata();
            }
        }, 1000);
        
    } catch (error) {
        showNotification('Error: ' + error.message, 'error');
        resetSubmitButton(submitBtn, originalText);
    }
}

function resetSubmitButton(submitBtn, originalText) {
    submitBtn.classList.remove('btn-loading', 'btn-success');
    submitBtn.textContent = originalText;
    submitBtn.disabled = false;
}

// === FUNCIONES ADICIONALES ===

// Reemplaza la función applyFilters actual
async function applyFilters() {
    const searchTerm = document.getElementById('searchMetadata').value.toLowerCase();
    const responsibleFilter = document.getElementById('filterByResponsible').value;
    const permissionFilter = document.getElementById('filterByPermission').value;
    
    showLoading(true);
    try {
        const res = await fetch(`${API_BASE}/admin/metadata`, { credentials: 'include' });
        if (!res.ok) throw new Error(res.statusText);
        let data = await res.json();
        
        // Aplicar filtros
        if (searchTerm) {
            data = data.filter(item => 
                item.filename.toLowerCase().includes(searchTerm) ||
                item.title.toLowerCase().includes(searchTerm) ||
                (item.description && item.description.toLowerCase().includes(searchTerm))
            );
        }
        
        if (responsibleFilter) {
            data = data.filter(item => item.responsible === responsibleFilter);
        }
        
        if (permissionFilter) {
            data = data.filter(item => item.permissions === permissionFilter);
        }
        
        updateMetadataTable(data);
        
        // Actualizar opciones de filtros
        updateFilterOptions(data);
        
    } catch (e) {
        showNotification('Error aplicando filtros: ' + e.message, 'error');
    } finally { 
        showLoading(false); 
    }
}

function updateFilterOptions(allData) {
    // Actualizar responsables
    const responsibles = [...new Set(allData.map(item => item.responsible).filter(Boolean))];
    const responsibleSelect = document.getElementById('filterByResponsible');
    if (responsibleSelect) {
        const currentValue = responsibleSelect.value;
        responsibleSelect.innerHTML = '<option value="">Todos los responsables</option>' +
            responsibles.map(r => `<option value="${r}" ${r === currentValue ? 'selected' : ''}>${r}</option>`).join('');
    }
    
    // Actualizar permisos
    const permissions = [...new Set(allData.map(item => item.permissions).filter(Boolean))];
    const permissionSelect = document.getElementById('filterByPermission');
    if (permissionSelect) {
        const currentValue = permissionSelect.value;
        permissionSelect.innerHTML = '<option value="">Todos los permisos</option>' +
            permissions.map(p => `<option value="${p}" ${p === currentValue ? 'selected' : ''}>${translatePermission(p)}</option>`).join('');
    }
}

// Agregar búsqueda en tiempo real
document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchMetadata');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(applyFilters, 500);
        });
    }
});

function closeNotification() {
    const notification = document.getElementById('notification');
    if (notification) {
        notification.classList.add('hidden');
    }
}

function logout() {
    if (confirm('¿Estás seguro de que quieres cerrar sesión?')) {
        window.location.href = '/admin/logout';
    }
}

// Cerrar modal al hacer clic fuera de él
window.onclick = function(event) {
    const modal = document.getElementById('metadataModal');
    if (event.target === modal) {
        closeModal();
    }
}