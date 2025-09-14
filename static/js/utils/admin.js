const API_BASE = window.location.origin;
let currentEditingFile = null;
let filterOptions = {};

// Estado de la aplicación
const appState = {
    currentSection: 'dashboard',
    dashboardData: null,
    metadataList: [],
    filesWithoutMetadata: []
};

// Inicialización
document.addEventListener('DOMContentLoaded', function() {
    loadCurrentUser();
    showSection('dashboard');
    loadFilterOptions();
});

// Gestión de navegación
function showSection(sectionName) {
    // Ocultar todas las secciones
    document.querySelectorAll('.admin-section').forEach(section => {
        section.classList.add('hidden');
    });
    
    // Mostrar la sección seleccionada
    document.getElementById(sectionName + 'Section').classList.remove('hidden');
    
    // Actualizar navegación activa
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // Cargar datos específicos de la sección
    appState.currentSection = sectionName;
    loadSectionData(sectionName);
}

function loadSectionData(sectionName) {
    switch(sectionName) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'metadata':
            loadMetadataList();
            break;
        case 'files':
            loadFilesWithoutMetadata();
            break;
    }
}

// Autenticación
async function loadCurrentUser() {
    try {
        const response = await fetch(`${API_BASE}/admin/user-info`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const userInfo = await response.json();
            document.getElementById('adminUser').textContent = userInfo.username;
        }
    } catch (error) {
        console.error('Error cargando usuario:', error);
    }
}

function logout() {
    // Para HTTP Basic Auth, simplemente redirigir a una URL que fuerce re-autenticación
    window.location.href = '/admin/';
}

// Dashboard
async function loadDashboard() {
    showLoading(true);
    try {
        const response = await fetch(`${API_BASE}/admin/dashboard`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Error cargando dashboard');
        }
        
        const data = await response.json();
        appState.dashboardData = data;
        updateDashboardUI(data);
    } catch (error) {
        showNotification('Error cargando dashboard: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function updateDashboardUI(data) {
    document.getElementById('totalFiles').textContent = data.total_files;
    document.getElementById('filesWithMetadata').textContent = data.files_with_metadata;
    document.getElementById('filesWithoutMetadata').textContent = data.files_without_metadata;
    
    const lastUpdated = data.last_updated 
        ? new Date(data.last_updated).toLocaleDateString('es-ES')
        : 'Nunca';
    document.getElementById('lastUpdated').textContent = lastUpdated;
    
    // Actividad reciente
    const activityList = document.getElementById('recentActivity');
    if (data.recent_activity && data.recent_activity.length > 0) {
        activityList.innerHTML = data.recent_activity.map(activity => `
            <div class="activity-item">
                <strong>${activity.changed_by}</strong> modificó 
                <em>${activity.field_changed}</em> 
                - ${new Date(activity.changed_at).toLocaleString('es-ES')}
            </div>
        `).join('');
    } else {
        activityList.innerHTML = '<div class="activity-item">No hay actividad reciente</div>';
    }
}

// Gestión de metadatos
async function loadMetadataList() {
    showLoading(true);
    try {
        const searchTerm = document.getElementById('searchMetadata')?.value || '';
        const responsible = document.getElementById('filterByResponsible')?.value || '';
        const permissions = document.getElementById('filterByPermission')?.value || '';
        
        const params = new URLSearchParams();
        if (searchTerm) params.append('search', searchTerm);
        if (responsible) params.append('responsible', responsible);
        if (permissions) params.append('permissions', permissions);
        
        const response = await fetch(`${API_BASE}/admin/metadata?${params}`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Error cargando metadatos');
        }
        
        const data = await response.json();
        appState.metadataList = data;
        updateMetadataTable(data);
    } catch (error) {
        showNotification('Error cargando metadatos: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function updateMetadataTable(metadataList) {
    const tbody = document.getElementById('metadataTableBody');
    
    if (metadataList.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6">No se encontraron metadatos</td></tr>';
        return;
    }
    
    tbody.innerHTML = metadataList.map(metadata => `
        <tr>
            <td><code>${metadata.filename}</code></td>
            <td>${metadata.title}</td>
            <td>${metadata.responsible || '-'}</td>
            <td><span class="permission-badge ${metadata.permissions}">${metadata.permissions}</span></td>
            <td>${new Date(metadata.updated_at).toLocaleDateString('es-ES')}</td>
            <td>
                <button onclick="editMetadata('${metadata.filename}')" class="btn-primary btn-sm">Editar</button>
                <button onclick="deleteMetadata('${metadata.filename}')" class="btn-danger btn-sm">Eliminar</button>
            </td>
        </tr>
    `).join('');
}

async function loadFilterOptions() {
    try {
        const response = await fetch(`${API_BASE}/admin/filter-options`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            filterOptions = await response.json();
            updateFilterSelects();
        }
    } catch (error) {
        console.error('Error cargando opciones de filtro:', error);
    }
}

function updateFilterSelects() {
    const responsibleSelect = document.getElementById('filterByResponsible');
    const permissionSelect = document.getElementById('filterByPermission');
    
    if (responsibleSelect && filterOptions.responsibles) {
        responsibleSelect.innerHTML = '<option value="">Todos los responsables</option>' +
            filterOptions.responsibles.map(r => `<option value="${r}">${r}</option>`).join('');
    }
    
    if (permissionSelect && filterOptions.permissions) {
        permissionSelect.innerHTML = '<option value="">Todos los permisos</option>' +
            filterOptions.permissions.map(p => `<option value="${p}">${p}</option>`).join('');
    }
}

function applyFilters() {
    loadMetadataList();
}

// Archivos sin metadatos
async function loadFilesWithoutMetadata() {
    showLoading(true);
    try {
        const response = await fetch(`${API_BASE}/admin/files-without-metadata`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Error cargando archivos sin metadatos');
        }
        
        const data = await response.json();
        appState.filesWithoutMetadata = data;
        updateFilesWithoutMetadataUI(data);
    } catch (error) {
        showNotification('Error cargando archivos: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function updateFilesWithoutMetadataUI(files) {
    const container = document.getElementById('filesWithoutMetadataList');
    
    if (files.length === 0) {
        container.innerHTML = '<p>Todos los archivos tienen metadatos.</p>';
        return;
    }
    
    container.innerHTML = files.map(file => `
        <div class="file-card">
            <h4>${file.filename}</h4>
            <p>Tamaño: ${file.size_mb} MB</p>
            <p>Modificado: ${new Date(file.modified).toLocaleDateString('es-ES')}</p>
            <button onclick="createMetadataForFile('${file.filename}')" class="btn-primary btn-sm">
                Crear Metadatos
            </button>
        </div>
    `).join('');
}

// Modal de metadatos
function showCreateForm() {
    currentEditingFile = null;
    document.getElementById('modalTitle').textContent = 'Crear Metadatos';
    document.getElementById('submitBtn').textContent = 'Crear Metadatos';
    resetMetadataForm();
    loadFilesForSelect();
    showModal();
}

function createMetadataForFile(filename) {
    currentEditingFile = null;
    document.getElementById('modalTitle').textContent = 'Crear Metadatos';
    document.getElementById('submitBtn').textContent = 'Crear Metadatos';
    resetMetadataForm();
    
    // Pre-seleccionar el archivo
    const filenameSelect = document.getElementById('filename');
    filenameSelect.innerHTML = `<option value="${filename}" selected>${filename}</option>`;
    filenameSelect.disabled = true;
    
    showModal();
}

async function editMetadata(filename) {
    showLoading(true);
    try {
        const response = await fetch(`${API_BASE}/admin/metadata/${filename}`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Error cargando metadatos');
        }
        
        const data = await response.json();
        
        currentEditingFile = filename;
        document.getElementById('modalTitle').textContent = 'Editar Metadatos';
        document.getElementById('submitBtn').textContent = 'Actualizar Metadatos';
        
        // Llenar formulario con datos existentes
        fillMetadataForm(data);
        showModal();
    } catch (error) {
        showNotification('Error cargando metadatos: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function fillMetadataForm(data) {
    document.getElementById('filename').innerHTML = `<option value="${data.filename}" selected>${data.filename}</option>`;
    document.getElementById('filename').disabled = true;
    document.getElementById('title').value = data.title || '';
    document.getElementById('description').value = data.description || '';
    document.getElementById('responsible').value = data.responsible || '';
    document.getElementById('frequency').value = data.frequency || '';
    document.getElementById('permissions').value = data.permissions || 'public';
    document.getElementById('tags').value = (data.tags || []).join(', ');
}

function resetMetadataForm() {
    document.getElementById('metadataForm').reset();
    document.getElementById('filename').disabled = false;
    document.getElementById('permissions').value = 'public';
}

async function loadFilesForSelect() {
    try {
        const files = appState.filesWithoutMetadata;
        const filenameSelect = document.getElementById('filename');
        
        filenameSelect.innerHTML = '<option value="">Seleccionar archivo...</option>' +
            files.map(file => `<option value="${file.filename}">${file.filename}</option>`).join('');
    } catch (error) {
        console.error('Error cargando archivos para select:', error);
    }
}

// Envío de formulario
document.getElementById('metadataForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = {
        filename: document.getElementById('filename').value,
        title: document.getElementById('title').value,
        description: document.getElementById('description').value || null,
        responsible: document.getElementById('responsible').value || null,
        frequency: document.getElementById('frequency').value || null,
        permissions: document.getElementById('permissions').value,
        tags: document.getElementById('tags').value.split(',').map(tag => tag.trim()).filter(tag => tag)
    };
    
    showLoading(true);
    try {
        const isEditing = currentEditingFile !== null;
        const url = isEditing 
            ? `${API_BASE}/admin/metadata/${currentEditingFile}`
            : `${API_BASE}/admin/metadata`;
        const method = isEditing ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify(formData)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error procesando solicitud');
        }
        
        showNotification(
            isEditing ? 'Metadatos actualizados correctamente' : 'Metadatos creados correctamente', 
            'success'
        );
        
        closeModal();
        
        // Recargar datos según la sección actual
        if (appState.currentSection === 'metadata') {
            loadMetadataList();
        } else if (appState.currentSection === 'files') {
            loadFilesWithoutMetadata();
        }
        loadDashboard(); // Actualizar estadísticas
        
    } catch (error) {
        showNotification('Error: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
});

async function deleteMetadata(filename) {
    if (!confirm(`¿Estás seguro de que quieres eliminar los metadatos de "${filename}"?`)) {
        return;
    }
    
    showLoading(true);
    try {
        const response = await fetch(`${API_BASE}/admin/metadata/${filename}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error eliminando metadatos');
        }
        
        showNotification('Metadatos eliminados correctamente', 'success');
        loadMetadataList();
        loadDashboard(); // Actualizar estadísticas
        
    } catch (error) {
        showNotification('Error eliminando metadatos: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// Utilidades UI
function showModal() {
    document.getElementById('metadataModal').style.display = 'block';
}

function closeModal() {
    document.getElementById('metadataModal').style.display = 'none';
    resetMetadataForm();
    currentEditingFile = null;
}

function showLoading(show) {
    const spinner = document.getElementById('loadingSpinner');
    if (show) {
        spinner.classList.remove('hidden');
    } else {
        spinner.classList.add('hidden');
    }
}

function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    const messageElement = document.getElementById('notificationMessage');
    
    messageElement.textContent = message;
    notification.className = `notification ${type}`;
    notification.classList.remove('hidden');
    
    // Auto-ocultar después de 5 segundos
    setTimeout(() => {
        closeNotification();
    }, 5000);
}

function closeNotification() {
    document.getElementById('notification').classList.add('hidden');
}

// Event listeners para cerrar modal
window.onclick = function(event) {
    const modal = document.getElementById('metadataModal');
    if (event.target === modal) {
        closeModal();
    }
}

// Event listeners para filtros
document.getElementById('searchMetadata')?.addEventListener('input', function() {
    // Debounce search
    clearTimeout(this.searchTimeout);
    this.searchTimeout = setTimeout(applyFilters, 300);
});