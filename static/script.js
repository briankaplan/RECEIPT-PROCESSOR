// Receipt Processor Pro - Enhanced Interactive Frontend

// Global state management
const AppState = {
    processing: false,
    connected: false,
    services: {
        mongodb: 'offline',
        gmail: 'offline', 
        teller: 'offline',
        r2: 'offline',
        huggingface: 'offline',
        sheets: 'offline'
    },
    stats: {
        receipts: 0,
        processed: 0,
        matched: 0,
        unmatched: 0
    },
    settings: {}
};

// Enhanced animation utilities
const AnimationUtils = {
    slideIn: (element, direction = 'up', duration = 0.5) => {
        if (!element) return;
        element.style.opacity = '0';
        element.style.transform = direction === 'up' ? 'translateY(30px)' : 
                                 direction === 'down' ? 'translateY(-30px)' :
                                 direction === 'left' ? 'translateX(30px)' : 'translateX(-30px)';
        element.style.transition = `all ${duration}s cubic-bezier(0.4, 0, 0.2, 1)`;
        
        setTimeout(() => {
            element.style.opacity = '1';
            element.style.transform = 'translate(0, 0)';
        }, 50);
    },

    bounce: (element, scale = 1.1, duration = 0.3) => {
        if (!element) return;
        element.style.transition = `transform ${duration}s cubic-bezier(0.68, -0.55, 0.265, 1.55)`;
        element.style.transform = `scale(${scale})`;
        
        setTimeout(() => {
            element.style.transform = 'scale(1)';
        }, duration * 1000);
    },

    pulse: (element, iterations = 3) => {
        if (!element) return;
        element.style.animation = `pulse 0.5s ease-in-out ${iterations}`;
        setTimeout(() => {
            element.style.animation = '';
        }, iterations * 500);
    },

    shake: (element) => {
        if (!element) return;
        element.style.animation = 'shake 0.5s ease-in-out';
        setTimeout(() => {
            element.style.animation = '';
        }, 500);
    },

    glow: (element, color = 'primary') => {
        if (!element) return;
        element.classList.add(`shadow-glow-${color}`);
        setTimeout(() => {
            element.classList.remove(`shadow-glow-${color}`);
        }, 2000);
    }
};

// Enhanced notification system
class NotificationManager {
    constructor() {
        this.container = this.createContainer();
        this.queue = [];
        this.active = [];
    }

    createContainer() {
        const container = document.createElement('div');
        container.id = 'notification-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            pointer-events: none;
        `;
        document.body.appendChild(container);
        return container;
    }

    show(type, message, options = {}) {
        const notification = this.create(type, message, options);
        this.queue.push(notification);
        this.processQueue();
        return notification;
    }

    create(type, message, options) {
        const {
            duration = 5000,
            title = '',
            actions = [],
            persistent = false,
            icon = ''
        } = options;

        const id = `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const iconClass = icon || this.getDefaultIcon(type);
        
        const notification = document.createElement('div');
        notification.id = id;
        notification.className = `alert alert-${type} notification shadow-lg`;
        notification.style.cssText = `
            margin-bottom: 1rem;
            min-width: 350px;
            max-width: 500px;
            opacity: 0;
            transform: translateX(100%);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            pointer-events: auto;
            position: relative;
            overflow: hidden;
        `;

        notification.innerHTML = `
            <div class="d-flex align-items-start">
                <i class="${iconClass} me-3 mt-1" style="font-size: 1.2rem;"></i>
                <div class="flex-grow-1">
                    ${title ? `<div class="fw-bold mb-1">${title}</div>` : ''}
                    <div>${message}</div>
                    ${actions.length ? `
                        <div class="mt-2">
                            ${actions.map(action => `
                                <button class="btn btn-sm btn-outline-${type === 'danger' ? 'light' : 'primary'} me-2" 
                                        onclick="${action.onClick}">${action.label}</button>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
                ${!persistent ? `
                    <button type="button" class="btn-close ms-2" onclick="notifications.remove('${id}')"></button>
                ` : ''}
            </div>
            <div class="notification-progress"></div>
        `;

        // Auto-remove if not persistent
        if (!persistent && duration > 0) {
            setTimeout(() => this.remove(id), duration);
        }

        return { element: notification, id, duration, persistent };
    }

    getDefaultIcon(type) {
        const icons = {
            success: 'fas fa-check-circle',
            warning: 'fas fa-exclamation-triangle', 
            danger: 'fas fa-times-circle',
            info: 'fas fa-info-circle',
            primary: 'fas fa-bell'
        };
        return icons[type] || icons.info;
    }

    processQueue() {
        if (this.queue.length === 0) return;
        
        const notification = this.queue.shift();
        this.active.push(notification);
        this.container.appendChild(notification.element);
        
        // Animate in
        setTimeout(() => {
            notification.element.style.opacity = '1';
            notification.element.style.transform = 'translateX(0)';
        }, 50);
        
        // Add progress bar animation
        if (!notification.persistent && notification.duration > 0) {
            const progressBar = notification.element.querySelector('.notification-progress');
            if (progressBar) {
                progressBar.style.cssText = `
                    position: absolute;
                    bottom: 0;
                    left: 0;
                    height: 3px;
                    background: currentColor;
                    opacity: 0.3;
                    width: 100%;
                    transform-origin: left;
                    animation: notificationProgress ${notification.duration}ms linear;
                `;
            }
        }
    }

    remove(id) {
        const notification = this.active.find(n => n.id === id);
        if (!notification) return;
        
        // Animate out
        notification.element.style.opacity = '0';
        notification.element.style.transform = 'translateX(100%)';
        
        setTimeout(() => {
            if (notification.element.parentNode) {
                notification.element.parentNode.removeChild(notification.element);
            }
            this.active = this.active.filter(n => n.id !== id);
        }, 300);
    }

    clear() {
        this.active.forEach(notification => this.remove(notification.id));
        this.queue = [];
    }
}

// Global action handlers
window.actions = {
    async connectBanks() {
        try {
            notifications.show('info', 'Connecting to banks...', { icon: 'fas fa-bank' });
            const response = await fetch('/teller/connect', { method: 'POST' });
            const data = await response.json();
            
            if (data.success && data.redirect_url) {
                notifications.show('success', 'Redirecting to secure bank connection...');
                setTimeout(() => window.location.href = data.redirect_url, 1000);
            }
        } catch (error) {
            notifications.show('danger', 'Failed to connect banks: ' + error.message);
        }
    },

    async syncBankData() {
        try {
            notifications.show('info', 'Syncing bank data...', { icon: 'fas fa-sync' });
            const response = await fetch('/api/sync-bank-transactions', { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            
            if (data.success) {
                notifications.show('success', `Synced ${data.count || 0} transactions!`);
                this.refreshData();
            }
        } catch (error) {
            notifications.show('danger', 'Failed to sync: ' + error.message);
        }
    },

    async processReceipts() {
        try {
            notifications.show('info', 'Processing receipts...', { icon: 'fas fa-receipt' });
            const response = await fetch('/api/process-receipts', { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ days_back: 30 })
            });
            const data = await response.json();
            
            if (data.success) {
                notifications.show('success', `Processed ${data.receipts_found || 0} receipts!`);
                this.refreshData();
            }
        } catch (error) {
            notifications.show('danger', 'Failed to process: ' + error.message);
        }
    },

    async exportToSheets() {
        try {
            notifications.show('info', 'Exporting to Google Sheets...', { icon: 'fas fa-file-export' });
            const response = await fetch('/api/export-sheets', { method: 'POST' });
            const data = await response.json();
            
            if (data.success) {
                notifications.show('success', 'Exported successfully!', {
                    actions: data.sheet_url ? [{
                        label: 'View Sheet',
                        onClick: `window.open('${data.sheet_url}', '_blank')`
                    }] : []
                });
            }
        } catch (error) {
            notifications.show('danger', 'Export failed: ' + error.message);
        }
    },

    async clearTestData() {
        try {
            notifications.show('info', 'Clearing test data...', { icon: 'fas fa-trash' });
            const response = await fetch('/api/clear-test-data', { method: 'POST' });
            const data = await response.json();
            
            if (data.success) {
                notifications.show('success', `Cleared ${data.removed || 0} test entries!`);
                this.refreshData();
            }
        } catch (error) {
            notifications.show('danger', 'Failed to clear: ' + error.message);
        }
    },

    async refreshData() {
        notifications.show('info', 'Refreshing data...', { icon: 'fas fa-refresh' });
        // Refresh status
        checkStatus();
        // Trigger page refresh for tables
        setTimeout(() => location.reload(), 1000);
    }
};

// Status checking
function checkStatus() {
    fetch('/api/status/real')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateServiceStatuses(data.services);
                updateStats(data.stats);
            }
        })
        .catch(error => console.error('Status check failed:', error));
}

function updateServiceStatuses(services) {
    Object.entries(services).forEach(([service, info]) => {
        const indicator = document.getElementById(`${service}-status`);
        if (indicator) {
            indicator.classList.remove('online', 'offline', 'processing');
            const status = info.status === 'connected' ? 'online' : 
                          info.status === 'configured' ? 'processing' : 'offline';
            indicator.classList.add(status);
        }
    });
}

function updateStats(stats) {
    if (!stats) return;
    Object.entries(stats).forEach(([key, value]) => {
        const element = document.getElementById(`${key}-count`);
        if (element) {
            element.textContent = value;
        }
    });
}

// Initialize managers
const notifications = new NotificationManager();

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    // Add CSS animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes notificationProgress {
            from { transform: scaleX(1); }
            to { transform: scaleX(0); }
        }
        
        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-5px); }
            75% { transform: translateX(5px); }
        }
        
        .btn:not(:disabled):hover {
            transform: translateY(-2px) scale(1.05);
            transition: all 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-4px) scale(1.01);
            transition: all 0.3s ease;
        }
        
        .table tbody tr:hover {
            background-color: rgba(13, 110, 253, 0.1);
            transform: scale(1.005);
            transition: all 0.2s ease;
        }
        
        .status-dot.online {
            background: #10b981;
            box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.3);
            animation: pulse-online 2s infinite;
        }
        
        .status-dot.offline {
            background: #ef4444;
            animation: pulse-offline 1s infinite;
        }
        
        .status-dot.processing {
            background: #f59e0b;
            animation: pulse-processing 0.8s infinite;
        }
        
        @keyframes pulse-online {
            0%, 100% { 
                box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.3);
                transform: scale(1);
            }
            50% { 
                box-shadow: 0 0 0 8px rgba(16, 185, 129, 0.1);
                transform: scale(1.1);
            }
        }
        
        @keyframes pulse-offline {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        @keyframes pulse-processing {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.3); }
        }
    `;
    document.head.appendChild(style);

    // Enhance all buttons
    document.querySelectorAll('button, .btn').forEach(button => {
        button.addEventListener('click', () => {
            if (!button.disabled) {
                AnimationUtils.bounce(button, 1.1, 0.2);
            }
        });
    });

    // Initial status check
    checkStatus();
    
    // Regular status updates
    setInterval(checkStatus, 30000);

    // Show welcome message
    setTimeout(() => {
        notifications.show('info', 'Receipt Processor Pro is ready!', {
            title: 'Welcome',
            icon: 'fas fa-rocket',
            duration: 3000
        });
    }, 1000);

    console.log('Receipt Processor Pro initialized! 🚀');
});

// Additional interactive functions
window.filterTransactions = function(type) {
    notifications.show('info', `Filtering transactions: ${type}`, { duration: 2000 });
    // Add actual filtering logic here
};

window.viewReceiptDetails = function(receiptId) {
    actions.openModal('receiptDetailsModal', `/api/receipts/${receiptId}`);
};

window.viewOCRText = function(receiptId) {
    actions.openModal('ocrTextModal', `/api/receipts/${receiptId}/ocr`);
};

window.copyOCRText = function(receiptId) {
    fetch(`/api/receipts/${receiptId}/ocr`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.ocr_text) {
                navigator.clipboard.writeText(data.ocr_text);
                notifications.show('success', 'OCR text copied to clipboard!');
            }
        })
        .catch(error => notifications.show('danger', 'Failed to copy OCR text'));
};

window.exportLog = function() {
    notifications.show('info', 'Exporting logs...', { icon: 'fas fa-file-export' });
    // Add export logic
};

window.clearLog = function() {
    notifications.show('warning', 'Clearing logs...', { icon: 'fas fa-trash' });
    // Add clear logic
};

window.openScanner = function() {
    window.location.href = '/receipt-scanner';
};

window.toggleTheme = function() {
    const body = document.body;
    const isDark = body.classList.contains('dark-theme');
    
    if (isDark) {
        body.classList.remove('dark-theme');
        localStorage.setItem('theme', 'light');
        notifications.show('info', 'Switched to light theme', { duration: 2000 });
    } else {
        body.classList.add('dark-theme');
        localStorage.setItem('theme', 'dark');
        notifications.show('info', 'Switched to dark theme', { duration: 2000 });
    }
};

// Enhanced keyboard shortcuts
window.addEventListener('keydown', function(e) {
    // Ctrl+S for scanner
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        openScanner();
    }
    
    // Ctrl+B for connect banks
    if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
        e.preventDefault();
        actions.connectBanks();
    }
    
    // Ctrl+P for process receipts
    if ((e.ctrlKey || e.metaKey) && e.key === 'p') {
        e.preventDefault();
        actions.processReceipts();
    }
    
    // Ctrl+E for export
    if ((e.ctrlKey || e.metaKey) && e.key === 'e') {
        e.preventDefault();
        actions.exportToSheets();
    }
});

// Legacy compatibility
let processingInProgress = false;

function showAlert(type, message, duration = 5000) {
    notifications.show(type, message, { duration });
}
