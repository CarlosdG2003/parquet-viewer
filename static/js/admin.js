const API_BASE = window.location.origin;
let currentEditingFile = null;

// Inicialización cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM cargado, inicializando admin...');
    
    // Cargar usuario actual
    loadCurrentUser();
    
    // Mostrar dashboard por defecto
    showSectionDirect('dashboard');
    
    // Configurar formulario
    setupForm();
});

function setupForm() {
    const form = document.getElementById('metadataForm');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }
}

function showSectionDirect(sectionName) {
    console.log('Mostrando sección:', sectionName);
    
    // Ocultar todas las secciones
    const sections = document.querySelectorAll('.admin-section');
    sections.forEach(section => section.classList.add('hidden'));
    
    // Mostrar la sección seleccionada
    const targetSection = document.getElementById(sectionName + 'Section');
    if (targetSection) {
        targetSection.classList.remove('hidden');
    }
    
    // Cargar datos según la sección
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

// Función global para los botones onclick del HTML
function showSection(sectionName) {
    showSectionDirect(sectionName);
    
    // Actualizar botones activos
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    if (event && event.target) {
        event.target.classList.add('active');
    }
}

async function loadCurrentUser() {
    try {
        const response = await fetch(`${API_BASE}/admin/user-info`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const userInfo = await response.json();
            const userElement = document.getElementById('adminUser');
            if (userElement) {
                userElement.textContent = userInfo.username;
            }
        }
    } catch (error) {
        console.error('Error cargando usuario:', error);
    }
}

async function loadDashboard() {
    console.log('Cargando dashboard...');
    showLoading(true);
    
    try {
        const response = await fetch(`${API_BASE}/admin/dashboard`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error(`Error ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Dashboard data:', data);
        updateDashboardUI(data);
    } catch (error) {
        console.error('Error en dashboard:', error);
        showNotification('Error cargando dashboard: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function updateDashboardUI(data) {
    const totalFiles = document.getElementById('totalFiles');
    const filesWithMetadata = document.getElementById('filesWithMetadata');
    const filesWithoutMetadata = document.getElementById('filesWithoutMetadata');
    const lastUpdated = document.getElementById('lastUpdated');
    
    if (totalFiles) totalFiles.textContent = data.total_files || '0';
    if (filesWithMetadata) filesWithMetadata.textContent = data.files_with_metadata || '0';
    if (filesWithoutMetadata) filesWithoutMetadata.textContent = data.files_without_metadata || '0';
    
    if (lastUpdated) {
        const lastUpdatedText = data.last_updated 
            ? new Date(data.last_updated).toLocaleDateString('es-ES')
            : 'Nunca';
        lastUpdated.textContent = lastUpdatedText;
    }
    
    const activityList = document.getElementById('recentActivity');
    if (activityList) {
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
}

async function loadFilesWithoutMetadata() {
    console.log('Cargando archivos sin metadatos...');
    showLoading(true);
    
    try {
        const response = await fetch(`${API_BASE}/admin/files-without-metadata`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error(`Error ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Files without metadata:', data);
        updateFilesWithoutMetadataUI(data);
    } catch (error) {
        console.error('Error cargando archivos:', error);
        showNotification('Error cargando archivos: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function updateFilesWithoutMetadataUI(files) {
    const container = document.getElementById('filesWithoutMetadataList');
    if (!container) {
        console.error('Container not found');
        return;
    }
    
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

async function loadMetadataList() {
    console.log('Cargando metadatos...');
    showLoading(true);
    
    try {
        const response = await fetch(`${API_BASE}/admin/metadata`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error(`Error ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Metadata list:', data);
        updateMetadataTable(data);
    } catch (error) {
        console.error('Error cargando metadatos:', error);
        showNotification('Error cargando metadatos: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function updateMetadataTable(metadataList) {
    const tbody = document.getElementById('metadataTableBody');
    if (!tbody) return;
    
    if (metadataList.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6">No hay metadatos</td></tr>';
        return;
    }
    
    tbody.innerHTML = metadataList.map(metadata => `
        <tr>
            <td><code>${metadata.filename}</code></td>
            <td>${metadata.title}</td>
            <td>${metadata.responsible || '-'}</td>
            <td>${translatePermission(metadata.permissions)}</td>
            <td>${translateFrequency(metadata.frequency || '-')}</td>
            <td>${new Date(metadata.updated_at).toLocaleDateString('es-ES')}</td>
            <td>
                <button onclick="editMetadata('${metadata.filename}')" class="btn-primary btn-sm">Editar</button>
                <button onclick="deleteMetadata('${metadata.filename}')" class="btn-danger btn-sm">Eliminar</button>
            </td>
        </tr>
    `).join('');
}

// Funciones de utilidad
function showLoading(show) {
    const spinner = document.getElementById('loadingSpinner');
    if (spinner) {
        if (show) {
            spinner.classList.remove('hidden');
        } else {
            spinner.classList.add('hidden');
        }
    }
}

function showNotification(message, type = 'success') {
    console.log('Notification:', message);
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

// Funciones de modal

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

function showCreateForm() {
    currentEditingFile = null;
    document.getElementById('modalTitle').textContent = 'Crear Metadatos';
    document.getElementById('submitBtn').textContent = 'Crear Metadatos';
    resetMetadataForm();
    loadFilesForSelect();
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
        
        fillMetadataForm(data);
        showModal();
    } catch (error) {
        showNotification('Error cargando metadatos: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

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
        loadDashboard();
        
    } catch (error) {
        showNotification('Error eliminando metadatos: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function fillMetadataForm(data) {
    const filenameSelect = document.getElementById('filename');
    const titleInput = document.getElementById('title');
    const descriptionInput = document.getElementById('description');
    const responsibleInput = document.getElementById('responsible');
    const frequencySelect = document.getElementById('frequency');
    const permissionsSelect = document.getElementById('permissions');
    const tagsInput = document.getElementById('tags');
    
    if (filenameSelect) {
        filenameSelect.innerHTML = `<option value="${data.filename}" selected>${data.filename}</option>`;
        filenameSelect.disabled = true;
    }
    if (titleInput) titleInput.value = data.title || '';
    if (descriptionInput) descriptionInput.value = data.description || '';
    if (responsibleInput) responsibleInput.value = data.responsible || '';
    if (frequencySelect) frequencySelect.value = data.frequency || '';
    if (permissionsSelect) permissionsSelect.value = data.permissions || 'public';
    if (tagsInput) tagsInput.value = (data.tags || []).join(', ');
}

function resetMetadataForm() {
    const form = document.getElementById('metadataForm');
    if (form) {
        form.reset();
        const filenameSelect = document.getElementById('filename');
        const permissionsSelect = document.getElementById('permissions');
        
        if (filenameSelect) filenameSelect.disabled = false;
        if (permissionsSelect) permissionsSelect.value = 'public';
    }
}

async function loadFilesForSelect() {
    try {
        const response = await fetch(`${API_BASE}/admin/files-without-metadata`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const files = await response.json();
            const filenameSelect = document.getElementById('filename');
            
            if (filenameSelect) {
                filenameSelect.innerHTML = '<option value="">Seleccionar archivo...</option>' +
                    files.map(file => `<option value="${file.filename}">${file.filename}</option>`).join('');
            }
        }
    } catch (error) {
        console.error('Error cargando archivos:', error);
    }
}

function showModal() {
    const modal = document.getElementById('metadataModal');
    if (modal) {
        modal.style.display = 'block';
    }
}

function closeModal() {
    const modal = document.getElementById('metadataModal');
    if (modal) {
        modal.style.display = 'none';
    }
    resetMetadataForm();
    currentEditingFile = null;
}

async function handleFormSubmit(e) {
    e.preventDefault();
    
    const filenameInput = document.getElementById('filename');
    const titleInput = document.getElementById('title');
    const descriptionInput = document.getElementById('description');
    const responsibleInput = document.getElementById('responsible');
    const frequencySelect = document.getElementById('frequency');
    const permissionsSelect = document.getElementById('permissions');
    const tagsInput = document.getElementById('tags');
    
    const formData = {
        filename: filenameInput.value,
        title: titleInput.value,
        description: descriptionInput.value || null,
        responsible: responsibleInput.value || null,
        frequency: frequencySelect.value || null,
        permissions: permissionsSelect.value,
        tags: tagsInput.value.split(',').map(tag => tag.trim()).filter(tag => tag)
    };
    
    const isEditing = currentEditingFile !== null;
    
    showLoading(true);
    try {
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
        const currentSection = document.querySelector('.admin-section:not(.hidden)');
        if (currentSection) {
            if (currentSection.id === 'metadataSection') {
                loadMetadataList();
            } else if (currentSection.id === 'filesSection') {
                loadFilesWithoutMetadata();
            }
        }
        loadDashboard();
        
    } catch (error) {
        showNotification('Error: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}


// Event listeners para el modal
window.addEventListener('click', function(event) {
    const modal = document.getElementById('metadataModal');
    if (event.target === modal) {
        closeModal();
    }
});

function translateFrequency(frequency) {
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

function translatePermission(permission) {
    const translations = {
        'public': 'Público',
        'internal': 'Interno',
        'confidential': 'Confidencial'
    };
    return translations[permission] || permission;
}