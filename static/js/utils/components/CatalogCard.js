/**
 * CatalogCard Component - Maneja la renderización y eventos de las tarjetas de catálogo
 */
class CatalogCard {
    constructor(catalog, onClick) {
        this.catalog = catalog;
        this.onClick = onClick;
    }

    /**
     * Renderiza la tarjeta de catálogo
     */
    render() {
        const permissions = this.catalog.permissions || 'public';
        const tags = this.catalog.tags || [];
        const lastUpdated = DOM.formatDate(this.catalog.modified);

        const cardElement = DOM.createElement('div', {
            className: 'catalog-card',
            dataset: { filename: this.catalog.name }
        });

        cardElement.innerHTML = this._getCardHTML(permissions, tags, lastUpdated);
        
        // Añadir evento de click
        cardElement.addEventListener('click', () => {
            if (this.onClick) {
                this.onClick(this.catalog);
            }
        });

        return cardElement;
    }

    /**
     * Genera el HTML interno de la tarjeta
     */
    _getCardHTML(permissions, tags, lastUpdated) {
        return `
            <div class="catalog-card-header">
                <h3 class="catalog-name">${DOM.escapeHtml(this.catalog.title || this.catalog.name)}</h3>
                <span class="permission-badge ${permissions}">${permissions}</span>
            </div>
            
            <p class="catalog-description">
                ${DOM.escapeHtml(this.catalog.description || 'Sin descripción disponible')}
            </p>
            
            <div class="catalog-meta">
                <div class="meta-item">
                    <span class="meta-label">Responsable</span>
                    <span class="meta-value">${DOM.escapeHtml(this.catalog.responsible || 'N/A')}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Actualización</span>
                    <span class="meta-value">${DOM.escapeHtml(this.catalog.frequency || 'N/A')}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Registros</span>
                    <span class="meta-value">${DOM.formatNumber(this.catalog.row_count)}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Formato</span>
                    <span class="meta-value">PARQUET</span>
                </div>
            </div>
            
            ${this._renderTags(tags)}
            
            <div class="catalog-footer">
                <span>Actualizado: ${lastUpdated}</span>
            </div>
        `;
    }

    /**
     * Renderiza los tags si existen
     */
    _renderTags(tags) {
        if (!tags || tags.length === 0) {
            return '';
        }

        const tagsHTML = tags.map(tag => 
            `<span class="tag">${DOM.escapeHtml(tag)}</span>`
        ).join('');

        return `<div class="catalog-tags">${tagsHTML}</div>`;
    }

    /**
     * Actualiza los datos del catálogo
     */
    updateData(newCatalog) {
        this.catalog = { ...this.catalog, ...newCatalog };
    }
}

window.CatalogCard = CatalogCard;