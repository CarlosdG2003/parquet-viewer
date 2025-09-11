/**
 * DOM Utilities - Helpers para manipulación del DOM
 */
class DomUtils {
    /**
     * Selecciona un elemento del DOM
     */
    static $(selector) {
        return document.querySelector(selector);
    }

    /**
     * Selecciona múltiples elementos del DOM
     */
    static $$(selector) {
        return document.querySelectorAll(selector);
    }

    /**
     * Crea un elemento con atributos y contenido
     */
    static createElement(tag, attributes = {}, content = '') {
        const element = document.createElement(tag);
        
        Object.entries(attributes).forEach(([key, value]) => {
            if (key === 'className') {
                element.className = value;
            } else if (key === 'dataset') {
                Object.entries(value).forEach(([dataKey, dataValue]) => {
                    element.dataset[dataKey] = dataValue;
                });
            } else {
                element.setAttribute(key, value);
            }
        });

        if (content) {
            element.innerHTML = content;
        }

        return element;
    }

    /**
     * Muestra/oculta elementos
     */
    static show(selector) {
        const element = typeof selector === 'string' ? this.$(selector) : selector;
        if (element) element.classList.remove('hidden');
    }

    static hide(selector) {
        const element = typeof selector === 'string' ? this.$(selector) : selector;
        if (element) element.classList.add('hidden');
    }

    static toggle(selector) {
        const element = typeof selector === 'string' ? this.$(selector) : selector;
        if (element) element.classList.toggle('hidden');
    }

    /**
     * Añade/quita clases CSS
     */
    static addClass(selector, className) {
        const element = typeof selector === 'string' ? this.$(selector) : selector;
        if (element) element.classList.add(className);
    }

    static removeClass(selector, className) {
        const element = typeof selector === 'string' ? this.$(selector) : selector;
        if (element) element.classList.remove(className);
    }

    /**
     * Estados de carga
     */
    static showLoading(containerId, message = 'Cargando...') {
        const container = this.$(containerId);
        if (container) {
            container.innerHTML = `<div class="loading-state">${message}</div>`;
        }
    }

    static showError(containerId, message) {
        const container = this.$(containerId);
        if (container) {
            container.innerHTML = `<div class="error-state">${message}</div>`;
        }
    }

    /**
     * Limpia el contenido de un contenedor
     */
    static clearContainer(selector) {
        const container = typeof selector === 'string' ? this.$(selector) : selector;
        if (container) {
            container.innerHTML = '';
        }
    }

    /**
     * Debounce para eventos
     */
    static debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Formatea números con separadores de miles
     */
    static formatNumber(number) {
        if (number === null || number === undefined) return 'N/A';
        return number.toLocaleString();
    }

    /**
     * Formatea fechas
     */
    static formatDate(dateString) {
        if (!dateString) return 'N/A';
        return new Date(dateString).toLocaleDateString();
    }

    /**
     * Escapa HTML para evitar XSS
     */
    static escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Manejo de eventos con delegación
     */
    static on(selector, event, handler, useCapture = false) {
        const element = typeof selector === 'string' ? this.$(selector) : selector;
        if (element) {
            element.addEventListener(event, handler, useCapture);
        }
    }

    static off(selector, event, handler) {
        const element = typeof selector === 'string' ? this.$(selector) : selector;
        if (element) {
            element.removeEventListener(event, handler);
        }
    }
}

// Crear alias global para fácil acceso
window.DOM = DomUtils;