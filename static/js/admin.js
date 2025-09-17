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
        msg.textContent = message;
        notification.className = `notification ${type}`;
        notification.classList.remove('hidden');
        setTimeout(() => notification.classList.add('hidden'), 5000);
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
