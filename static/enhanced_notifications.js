// Enhanced Receipt Discovery Notification System
// This file provides real-time notifications and animations for receipt discovery

// Global state for receipt discovery
const ReceiptDiscoveryState = {
    active: false,
    totalFound: 0,
    totalProcessed: 0,
    discoveries: [],
    startTime: null,
    overlay: null
};

// Enhanced notification system with real-time receipt discovery
class EnhancedNotificationManager {
    constructor() {
        this.container = this.createContainer();
        this.queue = [];
        this.active = [];
        this.receiptDiscoveryOverlay = null;
        this.discoveryCounter = 0;
    }

    createContainer() {
        const container = document.createElement('div');
        container.id = 'enhanced-notification-container';
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
            icon = '',
            receiptData = null
        } = options;

        const id = `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const iconClass = icon || this.getDefaultIcon(type);
        
        const notification = document.createElement('div');
        notification.id = id;
        notification.className = `alert alert-${type} enhanced-notification shadow-lg`;
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

        // Enhanced content for receipt discoveries
        let content = '';
        if (receiptData) {
            content = this.createReceiptDiscoveryContent(receiptData);
        } else {
            content = `
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
                        <button type="button" class="btn-close ms-2" onclick="enhancedNotifications.remove('${id}')"></button>
                    ` : ''}
                </div>
            `;
        }

        notification.innerHTML = content + `<div class="notification-progress"></div>`;

        // Auto-remove if not persistent
        if (!persistent && duration > 0) {
            setTimeout(() => this.remove(id), duration);
        }

        return { element: notification, id, duration, persistent };
    }

    createReceiptDiscoveryContent(receiptData) {
        const { merchant, amount, date, confidence, receiptNumber, matchType } = receiptData;
        const confidenceColor = confidence >= 0.9 ? '#10b981' : confidence >= 0.7 ? '#f59e0b' : '#ef4444';
        const confidenceText = confidence >= 0.9 ? 'Perfect Match' : confidence >= 0.7 ? 'Good Match' : 'Low Confidence';
        
        return `
            <div class="receipt-discovery-notification">
                <div class="discovery-header">
                    <div class="discovery-icon">
                        <i class="fas fa-receipt"></i>
                        <span class="receipt-number">#${receiptNumber}</span>
                    </div>
                    <div class="discovery-status">
                        <span class="status-badge ${matchType || 'found'}">${matchType || 'Found'}</span>
                    </div>
                </div>
                
                <div class="discovery-content">
                    <div class="merchant-info">
                        <h4 class="merchant-name">${merchant || 'Unknown Merchant'}</h4>
                        <div class="receipt-details">
                            <span class="amount">$${(amount || 0).toFixed(2)}</span>
                            <span class="date">${date || 'No date'}</span>
                        </div>
                    </div>
                    
                    <div class="confidence-info">
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: ${(confidence || 0) * 100}%; background: ${confidenceColor};"></div>
                        </div>
                        <span class="confidence-text" style="color: ${confidenceColor};">${confidenceText} (${Math.round((confidence || 0) * 100)}%)</span>
                    </div>
                </div>
                
                <div class="discovery-footer">
                    <div class="discovery-stats">
                        <span class="stat-item">
                            <i class="fas fa-clock"></i>
                            <span>${this.formatTime(receiptData.processingTime || 0)}</span>
                        </span>
                        <span class="stat-item">
                            <i class="fas fa-search"></i>
                            <span>${receiptData.searchMethod || 'AI Scan'}</span>
                        </span>
                    </div>
                </div>
            </div>
        `;
    }

    formatTime(ms) {
        if (ms < 1000) return `${ms}ms`;
        return `${(ms / 1000).toFixed(1)}s`;
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
        this.active.forEach(notification => {
            this.remove(notification.id);
        });
    }

    // Real-time receipt discovery system
    startReceiptDiscovery() {
        ReceiptDiscoveryState.active = true;
        ReceiptDiscoveryState.startTime = Date.now();
        ReceiptDiscoveryState.totalFound = 0;
        ReceiptDiscoveryState.totalProcessed = 0;
        ReceiptDiscoveryState.discoveries = [];
        
        this.showDiscoveryOverlay();
        this.show('info', '🔍 Starting receipt discovery...', {
            title: 'Receipt Scanner Active',
            icon: 'fas fa-search',
            persistent: true
        });
    }

    showDiscoveryOverlay() {
        if (this.receiptDiscoveryOverlay) return;
        
        this.receiptDiscoveryOverlay = document.createElement('div');
        this.receiptDiscoveryOverlay.id = 'receipt-discovery-overlay';
        this.receiptDiscoveryOverlay.innerHTML = `
            <div class="discovery-panel">
                <div class="discovery-header">
                    <h3>🔍 Receipt Discovery in Progress</h3>
                    <div class="discovery-stats">
                        <div class="stat-item">
                            <i class="fas fa-receipt"></i>
                            <span id="discovery-found">0</span> Found
                        </div>
                        <div class="stat-item">
                            <i class="fas fa-check-circle"></i>
                            <span id="discovery-processed">0</span> Processed
                        </div>
                        <div class="stat-item">
                            <i class="fas fa-clock"></i>
                            <span id="discovery-time">0s</span>
                        </div>
                    </div>
                </div>
                
                <div class="discovery-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" id="discovery-progress-fill"></div>
                    </div>
                </div>
                
                <div class="discovery-live-feed" id="discovery-live-feed">
                    <div class="feed-header">
                        <h4>Live Discovery Feed</h4>
                        <button class="clear-feed-btn" onclick="enhancedNotifications.clearDiscoveryFeed()">
                            <i class="fas fa-trash"></i> Clear
                        </button>
                    </div>
                    <div class="feed-content" id="discovery-feed-content"></div>
                </div>
                
                <div class="discovery-actions">
                    <button class="btn btn-primary" onclick="enhancedNotifications.stopReceiptDiscovery()">
                        <i class="fas fa-stop"></i> Stop Discovery
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(this.receiptDiscoveryOverlay);
        
        // Add CSS for the overlay
        this.addDiscoveryStyles();
        
        // Start live updates
        this.startDiscoveryUpdates();
    }

    addDiscoveryStyles() {
        const style = document.createElement('style');
        style.textContent = `
            #receipt-discovery-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.8);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
                backdrop-filter: blur(10px);
            }
            
            .discovery-panel {
                background: var(--bg-card, #1a1f2e);
                border-radius: 16px;
                padding: 2rem;
                max-width: 600px;
                width: 90%;
                max-height: 80vh;
                overflow-y: auto;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
                border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.1));
            }
            
            .discovery-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 1.5rem;
                padding-bottom: 1rem;
                border-bottom: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.1));
            }
            
            .discovery-header h3 {
                color: var(--text-primary, #ffffff);
                margin: 0;
                font-size: 1.5rem;
            }
            
            .discovery-stats {
                display: flex;
                gap: 1.5rem;
            }
            
            .stat-item {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                color: var(--text-secondary, #b8c2d6);
                font-size: 0.9rem;
            }
            
            .stat-item i {
                color: var(--primary-orange, #ff6b35);
            }
            
            .stat-item span {
                font-weight: 600;
                color: var(--text-primary, #ffffff);
            }
            
            .discovery-progress {
                margin-bottom: 1.5rem;
            }
            
            .progress-bar {
                width: 100%;
                height: 8px;
                background: var(--border-subtle, rgba(255, 255, 255, 0.1));
                border-radius: 4px;
                overflow: hidden;
            }
            
            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, var(--primary-orange, #ff6b35), var(--accent-orange, #ff8559));
                border-radius: 4px;
                width: 0%;
                transition: width 0.5s ease-in-out;
            }
            
            .discovery-live-feed {
                margin-bottom: 1.5rem;
            }
            
            .feed-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 1rem;
            }
            
            .feed-header h4 {
                color: var(--text-primary, #ffffff);
                margin: 0;
                font-size: 1.1rem;
            }
            
            .clear-feed-btn {
                background: none;
                border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.1));
                color: var(--text-secondary, #b8c2d6);
                padding: 0.5rem 1rem;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            
            .clear-feed-btn:hover {
                background: var(--bg-hover, rgba(255, 255, 255, 0.05));
                color: var(--text-primary, #ffffff);
            }
            
            .feed-content {
                max-height: 300px;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
                gap: 0.75rem;
            }
            
            .discovery-item {
                background: var(--bg-secondary, #242b3d);
                border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.1));
                border-radius: 12px;
                padding: 1rem;
                animation: discoveryItemSlideIn 0.5s ease-out;
            }
            
            @keyframes discoveryItemSlideIn {
                from {
                    opacity: 0;
                    transform: translateY(20px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            .discovery-item-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 0.5rem;
            }
            
            .discovery-item-title {
                font-weight: 600;
                color: var(--text-primary, #ffffff);
                font-size: 1rem;
            }
            
            .discovery-item-time {
                color: var(--text-muted, #8492a6);
                font-size: 0.8rem;
            }
            
            .discovery-item-details {
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .discovery-item-amount {
                font-weight: 600;
                color: var(--accent-green, #69f0ae);
                font-size: 1.1rem;
            }
            
            .discovery-item-confidence {
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }
            
            .confidence-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
            }
            
            .confidence-dot.high { background: #10b981; }
            .confidence-dot.medium { background: #f59e0b; }
            .confidence-dot.low { background: #ef4444; }
            
            .discovery-actions {
                text-align: center;
            }
            
            .discovery-actions .btn {
                background: var(--primary-orange, #ff6b35);
                border: none;
                color: white;
                padding: 0.75rem 1.5rem;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            
            .discovery-actions .btn:hover {
                background: var(--primary-orange-dark, #e55a2b);
                transform: translateY(-2px);
            }
            
            .receipt-discovery-notification {
                background: var(--bg-card, #242b3d);
                border-radius: 12px;
                padding: 1rem;
                border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.1));
            }
            
            .discovery-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 0.75rem;
            }
            
            .discovery-icon {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                color: var(--primary-orange, #ff6b35);
            }
            
            .receipt-number {
                background: var(--primary-orange, #ff6b35);
                color: white;
                padding: 0.25rem 0.5rem;
                border-radius: 4px;
                font-size: 0.8rem;
                font-weight: 600;
            }
            
            .status-badge {
                padding: 0.25rem 0.5rem;
                border-radius: 4px;
                font-size: 0.8rem;
                font-weight: 600;
            }
            
            .status-badge.found { background: rgba(16, 185, 129, 0.2); color: #10b981; }
            .status-badge.matched { background: rgba(79, 172, 254, 0.2); color: #4facfe; }
            .status-badge.processing { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
            
            .merchant-info {
                margin-bottom: 0.75rem;
            }
            
            .merchant-name {
                margin: 0 0 0.5rem 0;
                color: var(--text-primary, #ffffff);
                font-size: 1.1rem;
            }
            
            .receipt-details {
                display: flex;
                gap: 1rem;
                color: var(--text-secondary, #b8c2d6);
                font-size: 0.9rem;
            }
            
            .amount {
                color: var(--accent-green, #69f0ae);
                font-weight: 600;
            }
            
            .confidence-info {
                margin-bottom: 0.75rem;
            }
            
            .confidence-bar {
                width: 100%;
                height: 4px;
                background: var(--border-subtle, rgba(255, 255, 255, 0.1));
                border-radius: 2px;
                overflow: hidden;
                margin-bottom: 0.5rem;
            }
            
            .confidence-fill {
                height: 100%;
                border-radius: 2px;
                transition: width 0.5s ease-in-out;
            }
            
            .confidence-text {
                font-size: 0.8rem;
                font-weight: 600;
            }
            
            .discovery-footer {
                border-top: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.1));
                padding-top: 0.75rem;
            }
            
            .discovery-stats {
                display: flex;
                gap: 1rem;
                font-size: 0.8rem;
                color: var(--text-muted, #8492a6);
            }
            
            .stat-item {
                display: flex;
                align-items: center;
                gap: 0.25rem;
            }
            
            @keyframes receiptFound {
                0% { transform: scale(0.8) rotate(-5deg); opacity: 0; }
                50% { transform: scale(1.1) rotate(2deg); }
                100% { transform: scale(1) rotate(0deg); opacity: 1; }
            }
            
            @keyframes counterIncrement {
                0% { transform: scale(1); }
                50% { transform: scale(1.3); color: var(--primary-orange, #ff6b35); }
                100% { transform: scale(1); }
            }
            
            @keyframes notificationProgress {
                from { transform: scaleX(1); }
                to { transform: scaleX(0); }
            }
        `;
        document.head.appendChild(style);
    }

    startDiscoveryUpdates() {
        this.discoveryUpdateInterval = setInterval(() => {
            this.updateDiscoveryStats();
        }, 1000);
    }

    updateDiscoveryStats() {
        const foundEl = document.getElementById('discovery-found');
        const processedEl = document.getElementById('discovery-processed');
        const timeEl = document.getElementById('discovery-time');
        const progressEl = document.getElementById('discovery-progress-fill');
        
        if (foundEl) foundEl.textContent = ReceiptDiscoveryState.totalFound;
        if (processedEl) processedEl.textContent = ReceiptDiscoveryState.totalProcessed;
        
        if (timeEl && ReceiptDiscoveryState.startTime) {
            const elapsed = Math.floor((Date.now() - ReceiptDiscoveryState.startTime) / 1000);
            timeEl.textContent = `${elapsed}s`;
        }
        
        if (progressEl) {
            const progress = ReceiptDiscoveryState.totalFound > 0 ? 
                Math.min((ReceiptDiscoveryState.totalProcessed / ReceiptDiscoveryState.totalFound) * 100, 100) : 0;
            progressEl.style.width = `${progress}%`;
        }
    }

    addReceiptDiscovery(receiptData) {
        if (!ReceiptDiscoveryState.active) return;
        
        ReceiptDiscoveryState.totalFound++;
        ReceiptDiscoveryState.discoveries.push({
            ...receiptData,
            timestamp: Date.now(),
            discoveryNumber: ReceiptDiscoveryState.totalFound
        });
        
        // Update counter with animation
        const foundEl = document.getElementById('discovery-found');
        if (foundEl) {
            foundEl.style.animation = 'counterIncrement 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55)';
            setTimeout(() => foundEl.style.animation = '', 600);
        }
        
        // Add to live feed
        this.addToDiscoveryFeed(receiptData);
        
        // Show notification
        this.show('success', 'Receipt found!', {
            title: `Receipt #${ReceiptDiscoveryState.totalFound}`,
            icon: 'fas fa-receipt',
            duration: 4000,
            receiptData: {
                ...receiptData,
                receiptNumber: ReceiptDiscoveryState.totalFound
            }
        });
    }

    addToDiscoveryFeed(receiptData) {
        const feedContent = document.getElementById('discovery-feed-content');
        if (!feedContent) return;
        
        const discoveryItem = document.createElement('div');
        discoveryItem.className = 'discovery-item';
        
        const confidence = receiptData.confidence || 0;
        const confidenceClass = confidence >= 0.9 ? 'high' : confidence >= 0.7 ? 'medium' : 'low';
        
        discoveryItem.innerHTML = `
            <div class="discovery-item-header">
                <div class="discovery-item-title">${receiptData.merchant || 'Unknown Merchant'}</div>
                <div class="discovery-item-time">${this.formatTime(Date.now() - ReceiptDiscoveryState.startTime)}</div>
            </div>
            <div class="discovery-item-details">
                <div class="discovery-item-amount">$${(receiptData.amount || 0).toFixed(2)}</div>
                <div class="discovery-item-confidence">
                    <div class="confidence-dot ${confidenceClass}"></div>
                    <span>${Math.round(confidence * 100)}%</span>
                </div>
            </div>
        `;
        
        feedContent.insertBefore(discoveryItem, feedContent.firstChild);
        
        // Animate the new item
        discoveryItem.style.animation = 'receiptFound 0.8s cubic-bezier(0.68, -0.55, 0.265, 1.55)';
        setTimeout(() => discoveryItem.style.animation = '', 800);
        
        // Limit feed items
        if (feedContent.children.length > 20) {
            feedContent.removeChild(feedContent.lastChild);
        }
    }

    clearDiscoveryFeed() {
        const feedContent = document.getElementById('discovery-feed-content');
        if (feedContent) {
            feedContent.innerHTML = '';
        }
    }

    stopReceiptDiscovery() {
        ReceiptDiscoveryState.active = false;
        
        if (this.discoveryUpdateInterval) {
            clearInterval(this.discoveryUpdateInterval);
        }
        
        if (this.receiptDiscoveryOverlay) {
            this.receiptDiscoveryOverlay.remove();
            this.receiptDiscoveryOverlay = null;
        }
        
        this.show('success', `Discovery complete! Found ${ReceiptDiscoveryState.totalFound} receipts`, {
            title: 'Receipt Discovery Finished',
            icon: 'fas fa-check-circle',
            duration: 5000
        });
    }
}

// Initialize the enhanced notification system
const enhancedNotifications = new EnhancedNotificationManager();

// Global function to start enhanced receipt discovery
function startEnhancedReceiptDiscovery() {
    // Remove simulateReceiptDiscovery function - this should not exist in production
    // simulateReceiptDiscovery() {
    //     this.startReceiptDiscovery();
    //     
    //     const merchants = ['Walmart', 'Target', 'Amazon', 'Starbucks', 'McDonald\'s', 'Home Depot', 'Best Buy', 'Costco'];
    //     const amounts = [45.67, 23.99, 156.78, 8.45, 12.99, 89.99, 299.99, 67.50];
    //     
    //     let discoveryCount = 0;
    //     const maxDiscoveries = 15;
    //     
    //     const discoveryInterval = setInterval(() => {
    //         if (discoveryCount >= maxDiscoveries || !ReceiptDiscoveryState.active) {
    //             clearInterval(discoveryInterval);
    //             setTimeout(() => this.stopReceiptDiscovery(), 2000);
    //             return;
    //         }
    //         
    //         const merchant = merchants[Math.floor(Math.random() * merchants.length)];
    //         const amount = amounts[Math.floor(Math.random() * amounts.length)];
    //         const confidence = 0.7 + Math.random() * 0.3;
    //         
    //         this.addReceiptDiscovery({
    //             merchant,
    //             amount,
    //             date: new Date().toLocaleDateString(),
    //             confidence,
    //             processingTime: 500 + Math.random() * 2000,
    //             searchMethod: Math.random() > 0.5 ? 'AI Scan' : 'Email Search',
    //             matchType: Math.random() > 0.7 ? 'matched' : 'found'
    //         });
    //         
    //         discoveryCount++;
    //     }, 800 + Math.random() * 1200);
    // }
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { EnhancedNotificationManager, enhancedNotifications, startEnhancedReceiptDiscovery };
} 