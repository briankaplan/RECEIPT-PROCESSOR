// TallyUps - Ultimate Financial Intelligence PWA
// Main Application Script

class TallyUpsApp {
    constructor() {
        this.currentSection = 'dashboard';
        this.transactions = [];
        this.receipts = [];
        this.analytics = {};
        this.settings = {};
        this.isLoading = false;
        
        this.init();
    }

    async init() {
        console.log('🚀 Initializing TallyUps PWA...');
        
        // Initialize UI
        this.setupEventListeners();
        this.loadSettings();
        
        // Load initial data
        await this.loadDashboard();
        await this.updateSystemStatus();
        
        // Set up periodic updates
        this.setupPeriodicUpdates();
        
        console.log('✅ TallyUps PWA initialized');
    }

    setupEventListeners() {
        // Theme toggle
        window.toggleTheme = () => this.toggleTheme();
        
        // Navigation
        window.showSection = (section) => this.showSection(section);
        
        // Global error handling
        window.addEventListener('error', (e) => {
            console.error('App error:', e);
            this.showToast('An error occurred', 'error');
        });
    }

    // ========================================================================
    // NAVIGATION & UI
    // ========================================================================

    showSection(sectionName) {
        // Update navigation
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[onclick="showSection('${sectionName}')"]`).classList.add('active');

        // Update content sections
        document.querySelectorAll('.content-section').forEach(section => {
            section.classList.remove('active');
        });
        document.getElementById(sectionName).classList.add('active');

        this.currentSection = sectionName;
        
        // Load section-specific content
        this.loadSectionContent(sectionName);
    }

    async loadSectionContent(sectionName) {
        switch(sectionName) {
            case 'dashboard':
                await this.loadDashboard();
                break;
            case 'transactions':
                await this.loadTransactions();
                break;
            case 'receipts':
                await this.loadReceipts();
                break;
            case 'analytics':
                await this.loadAnalytics();
                break;
            case 'settings':
                await this.loadSettings();
                break;
        }
    }

    toggleTheme() {
        const html = document.documentElement;
        const currentTheme = html.getAttribute('data-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        
        html.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        
        // Update theme toggle icon
        const themeIcon = document.querySelector('.theme-toggle i');
        themeIcon.className = newTheme === 'light' ? 'fas fa-sun' : 'fas fa-moon';
        
        this.showToast(`Switched to ${newTheme} theme`, 'success');
    }

    // ========================================================================
    // DASHBOARD
    // ========================================================================

    async loadDashboard() {
        const dashboardSection = document.getElementById('dashboard');
        
        try {
            // Show loading
            dashboardSection.innerHTML = '<div class="loading">Loading dashboard...</div>';
            
            // Load dashboard stats
            const statsResponse = await fetch('/api/dashboard-stats');
            const stats = await statsResponse.json();
            
            // Load recent transactions
            const transactionsResponse = await fetch('/api/transactions?limit=5');
            const transactions = await transactionsResponse.json();
            
            // Render dashboard
            dashboardSection.innerHTML = this.renderDashboard(stats, transactions);
            
            // Set up dashboard event listeners
            this.setupDashboardEvents();
            
        } catch (error) {
            console.error('Dashboard load error:', error);
            dashboardSection.innerHTML = `
                <div class="card">
                    <h3>Dashboard</h3>
                    <p>Unable to load dashboard data. Please check your connection.</p>
                    <button class="btn-primary" onclick="app.loadDashboard()">Retry</button>
                </div>
            `;
        }
    }

    renderDashboard(stats, transactions) {
        const statsData = stats.success ? stats : { total_transactions: 0, total_amount: 0, ai_match_rate: 0, pending_receipts: 0 };
        const transactionsData = transactions.success ? transactions.transactions || [] : [];
        
        return `
            <div class="dashboard-grid">
                <!-- Stats Cards -->
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon">
                            <i class="fas fa-list"></i>
                        </div>
                        <div class="stat-content">
                            <div class="stat-value">${statsData.total_transactions || 0}</div>
                            <div class="stat-label">Total Transactions</div>
                        </div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon">
                            <i class="fas fa-dollar-sign"></i>
                        </div>
                        <div class="stat-content">
                            <div class="stat-value">$${(statsData.total_amount || 0).toLocaleString()}</div>
                            <div class="stat-label">Total Amount</div>
                        </div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon">
                            <i class="fas fa-robot"></i>
                        </div>
                        <div class="stat-content">
                            <div class="stat-value">${statsData.ai_match_rate || 0}%</div>
                            <div class="stat-label">AI Match Rate</div>
                        </div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon">
                            <i class="fas fa-receipt"></i>
                        </div>
                        <div class="stat-content">
                            <div class="stat-value">${statsData.pending_receipts || 0}</div>
                            <div class="stat-label">Pending Receipts</div>
                        </div>
                    </div>
                </div>

                <!-- Quick Actions -->
                <div class="action-grid">
                    <div class="action-card" onclick="app.showSection('receipts')">
                        <i class="fas fa-camera action-icon"></i>
                        <div class="action-title">Scan Receipt</div>
                        <div class="action-description">Use camera or upload receipt for AI processing</div>
                    </div>
                    
                    <div class="action-card" onclick="app.showSection('transactions')">
                        <i class="fas fa-list action-icon"></i>
                        <div class="action-title">View Transactions</div>
                        <div class="action-description">Manage and categorize your transactions</div>
                    </div>
                    
                    <div class="action-card" onclick="app.showSection('analytics')">
                        <i class="fas fa-chart-bar action-icon"></i>
                        <div class="action-title">Analytics</div>
                        <div class="action-description">View detailed financial insights</div>
                    </div>
                    
                    <div class="action-card" onclick="app.connectBank()">
                        <i class="fas fa-university action-icon"></i>
                        <div class="action-title">Connect Bank</div>
                        <div class="action-description">Link your bank accounts for automatic sync</div>
                    </div>
                </div>

                <!-- Recent Activity -->
                <div class="recent-activity">
                    <h3>Recent Activity</h3>
                    <div class="activity-list">
                        ${this.renderRecentActivity(transactionsData)}
                    </div>
                </div>
            </div>
        `;
    }

    renderRecentActivity(transactions) {
        if (!transactions || transactions.length === 0) {
            return '<p>No recent activity. Start by scanning a receipt or connecting your bank.</p>';
        }
        
        return transactions.map(transaction => `
            <div class="activity-item">
                <div class="activity-icon">
                    <i class="fas fa-${transaction.category === 'Business' ? 'briefcase' : 'shopping-cart'}"></i>
                </div>
                <div class="activity-content">
                    <div class="activity-title">${transaction.name || 'Transaction'}</div>
                    <div class="activity-subtitle">${transaction.date || 'Recent'}</div>
                </div>
                <div class="activity-amount ${transaction.amount < 0 ? 'negative' : 'positive'}">
                    $${Math.abs(transaction.amount || 0).toFixed(2)}
                </div>
            </div>
        `).join('');
    }

    setupDashboardEvents() {
        // Add any dashboard-specific event listeners here
    }

    // ========================================================================
    // TRANSACTIONS
    // ========================================================================

    async loadTransactions() {
        const transactionsSection = document.getElementById('transactions');
        
        try {
            transactionsSection.innerHTML = '<div class="loading">Loading transactions...</div>';
            
            const response = await fetch('/api/transactions');
            const data = await response.json();
            
            if (data.success) {
                this.transactions = data.transactions || [];
                transactionsSection.innerHTML = this.renderTransactions();
                this.setupTransactionEvents();
            } else {
                throw new Error(data.error || 'Failed to load transactions');
            }
        } catch (error) {
            console.error('Transactions load error:', error);
            transactionsSection.innerHTML = `
                <div class="card">
                    <h3>Transactions</h3>
                    <p>Unable to load transactions. ${error.message}</p>
                    <button class="btn-primary" onclick="app.loadTransactions()">Retry</button>
                </div>
            `;
        }
    }

    renderTransactions() {
        const isMobile = window.innerWidth <= 900;
        const container = document.getElementById('transactionRows');
        const transactionCount = document.getElementById('transactionCount');
        const totalAmount = document.getElementById('totalAmount');
        const showingCount = document.getElementById('showingCount');
        const aiConfidence = document.getElementById('aiConfidence');
        const paginationInfo = document.getElementById('paginationInfo');
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');

        if (this.isLoading) {
            container.innerHTML = '<div class="loading">Loading transactions...</div>';
            return;
        }

        // Update counts
        transactionCount.textContent = this.transactions.length;
        showingCount.textContent = this.filteredTransactions.length;

        // Calculate total amount
        const total = this.filteredTransactions.reduce((sum, t) => sum + (t.amount || 0), 0);
        totalAmount.textContent = `$${Math.abs(total).toFixed(2)}`;
        totalAmount.style.color = total >= 0 ? 'var(--success)' : 'var(--error)';

        // Calculate AI confidence
        const aiMatched = this.filteredTransactions.filter(t => t.ai_confidence > 0.7).length;
        const avgConfidence = this.filteredTransactions.length > 0 ? 
            (Math.round((aiMatched / this.filteredTransactions.length) * 100)) : 0;
        aiConfidence.textContent = `${avgConfidence}%`;

        // Pagination
        const totalPages = Math.ceil(this.filteredTransactions.length / this.itemsPerPage);
        const startIndex = (this.currentPage - 1) * this.itemsPerPage;
        const endIndex = startIndex + this.itemsPerPage;
        const pageTransactions = this.filteredTransactions.slice(startIndex, endIndex);

        paginationInfo.textContent = `Page ${this.currentPage} of ${totalPages}`;
        prevBtn.disabled = this.currentPage <= 1;
        nextBtn.disabled = this.currentPage >= totalPages;

        if (this.filteredTransactions.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 2rem; color: var(--text-secondary);">
                    <p>No transactions found matching your filters.</p>
                    <button class="control-btn primary" onclick="syncBanks()">Connect Bank</button>
                </div>
            `;
            return;
        }

        if (isMobile) {
            // Render as cards
            container.innerHTML = pageTransactions.map(transaction => {
                const isEditing = this.editingTransaction === transaction._id;
                const isSelected = this.selectedTransactions.has(transaction._id);
                return `
                    <div class="transaction-card animate__animated animate__fadeInUp ${isSelected ? 'selected' : ''}" data-id="${transaction._id}">
                        <div class="transaction-card-header">
                            <div class="transaction-checkbox ${isSelected ? 'checked' : ''}" 
                                onclick="toggleTransactionSelection('${transaction._id}')" data-id="${transaction._id}">
                                ${isSelected ? '✓' : ''}
                            </div>
                            <div class="transaction-name">${transaction.name || transaction.merchant_name || 'Unknown'}</div>
                            <div class="transaction-amount ${(transaction.amount || 0) > 0 ? 'income' : 'expense'}">
                                ${(transaction.amount || 0) > 0 ? '+' : ''}${Math.abs(transaction.amount || 0).toFixed(2)}
                            </div>
                        </div>
                        <div class="transaction-card-body">
                            <div class="transaction-category">${this.getCategoryName(transaction.category)}</div>
                            <div class="transaction-date">${this.formatDate(transaction.date)}</div>
                            <div class="transaction-meta">
                                ${transaction.account || 'Unknown'} • AI: ${Math.round((transaction.ai_confidence || 0) * 100)}%
                                ${transaction.business_type ? ` • ${transaction.business_type}` : ''}
                            </div>
                            <div class="transaction-actions">
                                <button class="action-btn-small" onclick="editTransaction('${transaction._id}')">Edit</button>
                                <button class="action-btn-small" onclick="duplicateTransaction('${transaction._id}')">Copy</button>
                                <button class="action-btn-small" onclick="deleteTransaction('${transaction._id}')">Delete</button>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        } else {
            // Render as table
            container.innerHTML = pageTransactions.map(transaction => {
                const isEditing = this.editingTransaction === transaction._id;
                const isSelected = this.selectedTransactions.has(transaction._id);
                return `
                    <div class="transaction-row animate__animated animate__fadeInUp ${isSelected ? 'selected' : ''}" data-id="${transaction._id}">
                        <div class="transaction-checkbox ${isSelected ? 'checked' : ''}" 
                            onclick="toggleTransactionSelection('${transaction._id}')" data-id="${transaction._id}">
                            ${isSelected ? '✓' : ''}
                        </div>
                        <div class="transaction-info">
                            <div class="transaction-name">${transaction.name || transaction.merchant_name || 'Unknown'}</div>
                            <div class="transaction-description">${transaction.description || ''}</div>
                            <div class="transaction-meta">
                                ${transaction.account || 'Unknown'} • AI: ${Math.round((transaction.ai_confidence || 0) * 100)}%
                                ${transaction.business_type ? ` • ${transaction.business_type}` : ''}
                            </div>
                        </div>
                        <div class="transaction-category">${this.getCategoryName(transaction.category)}</div>
                        <div class="transaction-amount ${(transaction.amount || 0) > 0 ? 'income' : 'expense'}">
                            ${(transaction.amount || 0) > 0 ? '+' : ''}${Math.abs(transaction.amount || 0).toFixed(2)}
                        </div>
                        <div class="transaction-date">${this.formatDate(transaction.date)}</div>
                        <div class="transaction-actions">
                            <button class="action-btn-small" onclick="editTransaction('${transaction._id}')">Edit</button>
                            <button class="action-btn-small" onclick="duplicateTransaction('${transaction._id}')">Copy</button>
                            <button class="action-btn-small" onclick="deleteTransaction('${transaction._id}')">Delete</button>
                        </div>
                    </div>
                `;
            }).join('');
        }
    }

    setupTransactionEvents() {
        // Add transaction-specific event listeners
    }

    // ========================================================================
    // RECEIPTS
    // ========================================================================

    async loadReceipts() {
        const receiptsSection = document.getElementById('receipts');
        
        try {
            receiptsSection.innerHTML = '<div class="loading">Loading receipts...</div>';
            
            const response = await fetch('/api/receipts');
            const data = await response.json();
            
            if (data.success) {
                this.receipts = data.receipts || [];
                receiptsSection.innerHTML = this.renderReceipts();
                this.setupReceiptEvents();
            } else {
                throw new Error(data.error || 'Failed to load receipts');
            }
        } catch (error) {
            console.error('Receipts load error:', error);
            receiptsSection.innerHTML = `
                <div class="card">
                    <h3>Receipts</h3>
                    <p>Unable to load receipts. ${error.message}</p>
                    <button class="btn-primary" onclick="app.loadReceipts()">Retry</button>
                </div>
            `;
        }
    }

    renderReceipts() {
        return `
            <div class="receipts-container">
                <div class="receipts-header">
                    <h3>Receipt Processing</h3>
                    <div class="receipt-actions">
                        <button class="btn-primary" onclick="app.openCamera()">
                            <i class="fas fa-camera"></i> Camera
                        </button>
                        <button class="btn-secondary" onclick="app.uploadReceipt()">
                            <i class="fas fa-upload"></i> Upload
                        </button>
                        <button class="btn-secondary" onclick="app.scanEmails()">
                            <i class="fas fa-envelope"></i> Scan Emails
                        </button>
                    </div>
                </div>
                
                <div class="receipt-upload-area" id="receipt-upload-area">
                    <div class="upload-zone" onclick="app.uploadReceipt()">
                        <i class="fas fa-cloud-upload-alt"></i>
                        <h4>Upload Receipt</h4>
                        <p>Click to select or drag and drop receipt images</p>
                    </div>
                </div>
                
                <div class="receipts-list">
                    <h4>Processed Receipts (${this.receipts.length})</h4>
                    ${this.receipts.map(receipt => this.renderReceiptItem(receipt)).join('')}
                </div>
            </div>
        `;
    }

    renderReceiptItem(receipt) {
        return `
            <div class="receipt-item">
                <div class="receipt-image">
                    <img src="${receipt.image_url || '/static/placeholder.png'}" alt="Receipt">
                </div>
                <div class="receipt-details">
                    <h5>${receipt.merchant || 'Unknown Merchant'}</h5>
                    <p>Amount: $${receipt.amount || 0}</p>
                    <p>Date: ${new Date(receipt.date).toLocaleDateString()}</p>
                    <p>Status: ${receipt.status || 'Processed'}</p>
                </div>
                <div class="receipt-actions">
                    <button class="btn-secondary btn-sm" onclick="app.viewReceipt('${receipt._id}')">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn-secondary btn-sm" onclick="app.reprocessReceipt('${receipt._id}')">
                        <i class="fas fa-redo"></i>
                    </button>
                </div>
            </div>
        `;
    }

    setupReceiptEvents() {
        // Set up drag and drop
        const uploadArea = document.getElementById('receipt-upload-area');
        if (uploadArea) {
            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.classList.add('drag-over');
            });
            
            uploadArea.addEventListener('dragleave', () => {
                uploadArea.classList.remove('drag-over');
            });
            
            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('drag-over');
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    this.processReceiptFiles(files);
                }
            });
        }
    }

    // ========================================================================
    // ANALYTICS
    // ========================================================================

    async loadAnalytics() {
        const analyticsSection = document.getElementById('analytics');
        
        try {
            analyticsSection.innerHTML = '<div class="loading">Loading analytics...</div>';
            
            const response = await fetch('/api/analytics/summary');
            const data = await response.json();
            
            if (data.success) {
                this.analytics = data;
                analyticsSection.innerHTML = this.renderAnalytics();
            } else {
                throw new Error(data.error || 'Failed to load analytics');
            }
        } catch (error) {
            console.error('Analytics load error:', error);
            analyticsSection.innerHTML = `
                <div class="card">
                    <h3>Analytics</h3>
                    <p>Unable to load analytics. ${error.message}</p>
                    <button class="btn-primary" onclick="app.loadAnalytics()">Retry</button>
                </div>
            `;
        }
    }

    renderAnalytics() {
        return `
            <div class="analytics-container">
                <div class="analytics-header">
                    <h3>Financial Analytics</h3>
                    <div class="analytics-actions">
                        <button class="btn-primary" onclick="app.exportAnalytics()">
                            <i class="fas fa-download"></i> Export Report
                        </button>
                        <button class="btn-secondary" onclick="app.generateTaxSummary()">
                            <i class="fas fa-file-invoice"></i> Tax Summary
                        </button>
                    </div>
                </div>
                
                <div class="analytics-grid">
                    ${this.renderAnalyticsCards()}
                </div>
                
                <div class="analytics-charts">
                    ${this.renderAnalyticsCharts()}
                </div>
            </div>
        `;
    }

    renderAnalyticsCards() {
        // This would render various analytics cards
        return `
            <div class="analytics-card">
                <h4>Business Breakdown</h4>
                <div class="business-stats">
                    <div class="business-stat">
                        <span class="stat-label">Personal</span>
                        <span class="stat-value">$${(this.analytics.personal?.amount || 0).toLocaleString()}</span>
                    </div>
                    <div class="business-stat">
                        <span class="stat-label">Down Home</span>
                        <span class="stat-value">$${(this.analytics.down_home?.amount || 0).toLocaleString()}</span>
                    </div>
                    <div class="business-stat">
                        <span class="stat-label">MCR</span>
                        <span class="stat-value">$${(this.analytics.mcr?.amount || 0).toLocaleString()}</span>
                    </div>
                </div>
            </div>
        `;
    }

    renderAnalyticsCharts() {
        // This would render charts and graphs
        return '<p>Charts and graphs would be rendered here</p>';
    }

    // ========================================================================
    // SETTINGS
    // ========================================================================

    async loadSettings() {
        const settingsSection = document.getElementById('settings');
        
        try {
            settingsSection.innerHTML = '<div class="loading">Loading settings...</div>';
            
            const response = await fetch('/api/memory/user-settings');
            const data = await response.json();
            
            if (data.success) {
                this.settings = data.settings || {};
            }
            
            settingsSection.innerHTML = this.renderSettings();
            this.setupSettingsEvents();
        } catch (error) {
            console.error('Settings load error:', error);
            settingsSection.innerHTML = `
                <div class="card">
                    <h3>Settings</h3>
                    <p>Unable to load settings. ${error.message}</p>
                    <button class="btn-primary" onclick="app.loadSettings()">Retry</button>
                </div>
            `;
        }
    }

    renderSettings() {
        return `
            <div class="settings-container">
                <h3>Settings</h3>
                
                <div class="settings-section">
                    <h4>Appearance</h4>
                    <div class="setting-item">
                        <label>Theme</label>
                        <select onchange="app.updateSetting('theme', this.value)">
                            <option value="dark" ${this.settings.theme === 'dark' ? 'selected' : ''}>Dark</option>
                            <option value="light" ${this.settings.theme === 'light' ? 'selected' : ''}>Light</option>
                        </select>
                    </div>
                </div>
                
                <div class="settings-section">
                    <h4>Integrations</h4>
                    <div class="setting-item">
                        <label>Bank Connection</label>
                        <button class="btn-primary" onclick="app.connectBank()">Connect Bank</button>
                    </div>
                    <div class="setting-item">
                        <label>Email Scanning</label>
                        <button class="btn-secondary" onclick="app.setupEmailScanning()">Setup Email</button>
                    </div>
                    <div class="setting-item">
                        <label>Calendar Integration</label>
                        <button class="btn-secondary" onclick="app.setupCalendar()">Setup Calendar</button>
                    </div>
                </div>
                
                <div class="settings-section">
                    <h4>Notifications</h4>
                    <div class="setting-item">
                        <label>Push Notifications</label>
                        <button class="btn-primary" onclick="app.requestNotificationPermission()">Enable</button>
                    </div>
                </div>
                
                <div class="settings-section">
                    <h4>Data Management</h4>
                    <div class="setting-item">
                        <label>Export Data</label>
                        <button class="btn-secondary" onclick="app.exportAllData()">Export All</button>
                    </div>
                    <div class="setting-item">
                        <label>Clear Data</label>
                        <button class="btn-secondary" onclick="app.clearAllData()">Clear All</button>
                    </div>
                </div>
            </div>
        `;
    }

    setupSettingsEvents() {
        // Add settings-specific event listeners
    }

    // ========================================================================
    // API INTEGRATIONS
    // ========================================================================

    async updateSystemStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            const statusElement = document.getElementById('system-status-text');
            if (statusElement) {
                if (data.all_systems_operational) {
                    statusElement.textContent = 'All Systems Operational';
                    document.querySelector('.system-status').style.borderColor = 'var(--accent-green)';
                } else {
                    statusElement.textContent = 'Systems Initializing';
                    document.querySelector('.system-status').style.borderColor = 'var(--accent-yellow)';
                }
            }
        } catch (error) {
            console.log('Status check failed:', error);
        }
    }

    async connectBank() {
        try {
            window.location.href = '/connect';
        } catch (error) {
            this.showToast('Failed to connect bank', 'error');
        }
    }

    async syncTransactions() {
        try {
            this.showToast('Syncing transactions...', 'info');
            
            const response = await fetch('/api/sync-bank-transactions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast('Transactions synced successfully', 'success');
                await this.loadTransactions();
            } else {
                throw new Error(data.error || 'Sync failed');
            }
        } catch (error) {
            this.showToast('Failed to sync transactions', 'error');
        }
    }

    async exportTransactions() {
        try {
            this.showToast('Exporting transactions...', 'info');
            
            const response = await fetch('/api/export-to-sheets', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast('Transactions exported successfully', 'success');
            } else {
                throw new Error(data.error || 'Export failed');
            }
        } catch (error) {
            this.showToast('Failed to export transactions', 'error');
        }
    }

    async updateTransactionCategory(transactionId, category) {
        try {
            const response = await fetch(`/api/transactions/${transactionId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ category })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast('Category updated', 'success');
            } else {
                throw new Error(data.error || 'Update failed');
            }
        } catch (error) {
            this.showToast('Failed to update category', 'error');
        }
    }

    async editTransaction(id) {
        // Open edit modal or inline edit (implement as needed)
        // For now, just highlight row/card and scroll into view
        this.editingTransaction = id;
        this.renderTransactions();
        setTimeout(() => {
            const el = document.querySelector(`[data-id='${id}']`);
            if (el) {
                el.classList.add('animate__pulse');
                el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                setTimeout(() => el.classList.remove('animate__pulse'), 800);
            }
        }, 100);
        // TODO: Open modal or inline form
    }

    async analyzeTransaction(transactionId) {
        try {
            this.showToast('Analyzing transaction...', 'info');
            
            const response = await fetch('/api/ai-chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: `Analyze transaction ${transactionId} and provide insights`
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showModal('AI Analysis', data.response);
            } else {
                throw new Error(data.error || 'Analysis failed');
            }
        } catch (error) {
            this.showToast('Failed to analyze transaction', 'error');
        }
    }

    async openCamera() {
        try {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                this.showToast('Camera not available', 'error');
                return;
            }
            
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            this.showCameraModal(stream);
        } catch (error) {
            this.showToast('Failed to access camera', 'error');
        }
    }

    async uploadReceipt() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/*';
        input.multiple = true;
        
        input.onchange = (e) => {
            const files = Array.from(e.target.files);
            this.processReceiptFiles(files);
        };
        
        input.click();
    }

    async processReceiptFiles(files) {
        try {
            this.showToast('Processing receipts...', 'info');
            
            for (const file of files) {
                const formData = new FormData();
                formData.append('receipt', file);
                
                const response = await fetch('/api/process-receipt', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    this.showToast(`Receipt processed: ${data.merchant}`, 'success');
                } else {
                    throw new Error(data.error || 'Processing failed');
                }
            }
            
            await this.loadReceipts();
        } catch (error) {
            this.showToast('Failed to process receipts', 'error');
        }
    }

    async scanEmails() {
        try {
            this.showToast('Scanning emails for receipts...', 'info');
            
            const response = await fetch('/api/scan-emails-for-receipts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast(`Found ${data.receipts_found || 0} receipts in emails`, 'success');
                await this.loadReceipts();
            } else {
                throw new Error(data.error || 'Email scan failed');
            }
        } catch (error) {
            this.showToast('Failed to scan emails', 'error');
        }
    }

    async viewReceipt(receiptId) {
        // This would show receipt details
        this.showToast('View receipt feature coming soon', 'info');
    }

    async reprocessReceipt(receiptId) {
        try {
            this.showToast('Reprocessing receipt...', 'info');
            
            const response = await fetch(`/api/receipts/${receiptId}/reprocess`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast('Receipt reprocessed', 'success');
                await this.loadReceipts();
            } else {
                throw new Error(data.error || 'Reprocessing failed');
            }
        } catch (error) {
            this.showToast('Failed to reprocess receipt', 'error');
        }
    }

    async exportAnalytics() {
        try {
            this.showToast('Exporting analytics...', 'info');
            
            const response = await fetch('/api/export-business-report', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast('Analytics exported successfully', 'success');
            } else {
                throw new Error(data.error || 'Export failed');
            }
        } catch (error) {
            this.showToast('Failed to export analytics', 'error');
        }
    }

    async generateTaxSummary() {
        try {
            this.showToast('Generating tax summary...', 'info');
            
            const response = await fetch('/api/generate-tax-summary', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast('Tax summary generated', 'success');
            } else {
                throw new Error(data.error || 'Generation failed');
            }
        } catch (error) {
            this.showToast('Failed to generate tax summary', 'error');
        }
    }

    async updateSetting(key, value) {
        try {
            const response = await fetch('/api/memory/user-settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ [key]: value })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.settings[key] = value;
                this.showToast('Setting updated', 'success');
                
                if (key === 'theme') {
                    document.documentElement.setAttribute('data-theme', value);
                }
            } else {
                throw new Error(data.error || 'Update failed');
            }
        } catch (error) {
            this.showToast('Failed to update setting', 'error');
        }
    }

    async setupEmailScanning() {
        this.showToast('Email scanning setup coming soon', 'info');
    }

    async setupCalendar() {
        this.showToast('Calendar setup coming soon', 'info');
    }

    async requestNotificationPermission() {
        try {
            if ('Notification' in window) {
                const permission = await Notification.requestPermission();
                if (permission === 'granted') {
                    this.showToast('Notifications enabled', 'success');
                } else {
                    this.showToast('Notifications denied', 'error');
                }
            } else {
                this.showToast('Notifications not supported', 'error');
            }
        } catch (error) {
            this.showToast('Failed to request notification permission', 'error');
        }
    }

    async exportAllData() {
        this.showToast('Export all data feature coming soon', 'info');
    }

    async clearAllData() {
        if (confirm('Are you sure you want to clear all data? This cannot be undone.')) {
            try {
                this.showToast('Clearing data...', 'info');
                
                const response = await fetch('/api/clear-test-data', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                
                const data = await response.json();
                
                if (data.success) {
                    this.showToast('Data cleared successfully', 'success');
                    await this.loadDashboard();
                } else {
                    throw new Error(data.error || 'Clear failed');
                }
            } catch (error) {
                this.showToast('Failed to clear data', 'error');
            }
        }
    }

    // ========================================================================
    // UTILITIES
    // ========================================================================

    showToast(message, type = 'info') {
        // Use the enhanced notifications system if available
        if (window.showToast) {
            window.showToast(message, type);
        } else {
            // Fallback toast
            console.log(`${type.toUpperCase()}: ${message}`);
        }
    }

    showModal(title, content) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal">
                <div class="modal-header">
                    <h3>${title}</h3>
                    <button onclick="this.closest('.modal-overlay').remove()">&times;</button>
                </div>
                <div class="modal-content">
                    ${content}
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Close on backdrop click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }

    showCameraModal(stream) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal">
                <div class="modal-header">
                    <h3>Camera</h3>
                    <button onclick="this.closest('.modal-overlay').remove()">&times;</button>
                </div>
                <div class="modal-content">
                    <video autoplay style="width: 100%; max-width: 500px;"></video>
                    <div class="camera-controls">
                        <button class="btn-primary" onclick="app.captureReceipt()">Capture</button>
                        <button class="btn-secondary" onclick="this.closest('.modal-overlay').remove()">Cancel</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        const video = modal.querySelector('video');
        video.srcObject = stream;
        
        // Store stream for cleanup
        modal.stream = stream;
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                stream.getTracks().forEach(track => track.stop());
                modal.remove();
            }
        });
    }

    async captureReceipt() {
        const video = document.getElementById('cameraVideo');
        const canvas = document.getElementById('cameraCanvas');
        
        if (video && canvas) {
            const context = canvas.getContext('2d');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            context.drawImage(video, 0, 0);
            
            canvas.toBlob(async (blob) => {
                if (blob) {
                    await this.uploadReceiptBlob(blob);
                }
            }, 'image/jpeg', 0.8);
        }
    }

    async uploadReceiptBlob(blob) {
        try {
            const formData = new FormData();
            formData.append('receipt', blob, 'receipt.jpg');
            
            const response = await fetch('/api/upload-receipt', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const result = await response.json();
                this.closeModal('cameraModal');
                // Optionally refresh transactions or show success message
                if (this.applyFilters) {
                    this.applyFilters();
                }
            }
        } catch (e) {
            console.error('Upload error:', e);
        }
    }

    setupPeriodicUpdates() {
        // Update system status every 30 seconds
        setInterval(() => {
            this.updateSystemStatus();
        }, 30000);
        
        // Refresh dashboard data every 60 seconds
        setInterval(() => {
            if (this.currentSection === 'dashboard') {
                this.loadDashboard();
            }
        }, 60000);
    }

    // App filter and pagination methods
    setSearch(value) {
        this.search = value;
        this.currentPage = 1;
        this.applyFilters();
        animateTransactionRows();
    }
    setCategoryFilter(value) {
        this.categoryFilter = value;
        this.currentPage = 1;
        this.applyFilters();
        animateTransactionRows();
    }
    setStatusFilter(value) {
        this.statusFilter = value;
        this.currentPage = 1;
        this.applyFilters();
        animateTransactionRows();
    }
    setDateFrom(value) {
        this.dateFrom = value;
        this.currentPage = 1;
        this.applyFilters();
        animateTransactionRows();
    }
    setDateTo(value) {
        this.dateTo = value;
        this.currentPage = 1;
        this.applyFilters();
        animateTransactionRows();
    }
    setBusinessTypeFilter(value) {
        this.businessTypeFilter = value;
        this.currentPage = 1;
        this.applyFilters();
        animateTransactionRows();
    }
    setAmountMin(value) {
        this.amountMin = value;
        this.currentPage = 1;
        this.applyFilters();
        animateTransactionRows();
    }
    setAmountMax(value) {
        this.amountMax = value;
        this.currentPage = 1;
        this.applyFilters();
        animateTransactionRows();
    }
    clearFilters() {
        this.search = '';
        this.categoryFilter = '';
        this.statusFilter = '';
        this.dateFrom = '';
        this.dateTo = '';
        this.businessTypeFilter = '';
        this.amountMin = '';
        this.amountMax = '';
        document.getElementById('searchInput').value = '';
        document.getElementById('categoryFilter').value = '';
        document.getElementById('statusFilter').value = '';
        document.getElementById('dateFrom').value = '';
        document.getElementById('dateTo').value = '';
        document.getElementById('businessTypeFilter').value = '';
        document.getElementById('amountMin').value = '';
        document.getElementById('amountMax').value = '';
        this.currentPage = 1;
        this.applyFilters();
        animateTransactionRows();
    }
    prevPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.renderTransactions();
            animateTransactionRows();
        }
    }
    nextPage() {
        const totalPages = Math.ceil(this.filteredTransactions.length / this.itemsPerPage);
        if (this.currentPage < totalPages) {
            this.currentPage++;
            this.renderTransactions();
            animateTransactionRows();
        }
    }

    applyFilters() {
        let filtered = this.transactions;
        // Search
        if (this.search && this.search.trim() !== '') {
            const q = this.search.trim().toLowerCase();
            filtered = filtered.filter(t =>
                (t.name && t.name.toLowerCase().includes(q)) ||
                (t.merchant_name && t.merchant_name.toLowerCase().includes(q)) ||
                (t.description && t.description.toLowerCase().includes(q))
            );
        }
        // Category
        if (this.categoryFilter && this.categoryFilter !== '') {
            filtered = filtered.filter(t => t.category === this.categoryFilter);
        }
        // Status
        if (this.statusFilter && this.statusFilter !== '') {
            filtered = filtered.filter(t => t.status === this.statusFilter);
        }
        // Date range
        if (this.dateFrom && this.dateFrom !== '') {
            filtered = filtered.filter(t => t.date && t.date >= this.dateFrom);
        }
        if (this.dateTo && this.dateTo !== '') {
            filtered = filtered.filter(t => t.date && t.date <= this.dateTo);
        }
        // Business type
        if (this.businessTypeFilter && this.businessTypeFilter !== '') {
            filtered = filtered.filter(t => t.business_type === this.businessTypeFilter);
        }
        // Amount min
        if (this.amountMin && this.amountMin !== '') {
            filtered = filtered.filter(t => Math.abs(t.amount || 0) >= parseFloat(this.amountMin));
        }
        // Amount max
        if (this.amountMax && this.amountMax !== '') {
            filtered = filtered.filter(t => Math.abs(t.amount || 0) <= parseFloat(this.amountMax));
        }
        this.filteredTransactions = filtered;
        this.renderTransactions();
    }

    toggleTransactionSelection(id) {
        if (!this.selectedTransactions) this.selectedTransactions = new Set();
        if (this.selectedTransactions.has(id)) {
            this.selectedTransactions.delete(id);
        } else {
            this.selectedTransactions.add(id);
        }
        this.renderTransactions();
    }

    async duplicateTransaction(id) {
        const tx = this.transactions.find(t => t._id === id);
        if (!tx) return;
        try {
            const res = await fetch('/api/transactions/duplicate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id })
            });
            if (res.ok) {
                // Refresh transactions
                const data = await res.json();
                this.transactions = data.transactions || this.transactions;
                this.applyFilters();
                animateTransactionRows();
            }
        } catch (e) {
            // Optionally show error
        }
    }

    async deleteTransaction(id) {
        if (!confirm('Delete this transaction?')) return;
        try {
            const res = await fetch(`/api/transactions/${id}`, { method: 'DELETE' });
            if (res.ok) {
                // Remove from local list
                this.transactions = this.transactions.filter(t => t._id !== id);
                this.applyFilters();
                animateTransactionRows();
            }
        } catch (e) {
            // Optionally show error
        }
    }

    // Modal functionality
    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'block';
            modal.classList.add('animate__fadeIn');
            document.body.style.overflow = 'hidden';
            
            // Focus management
            const firstFocusable = modal.querySelector('button, input, select, textarea');
            if (firstFocusable) firstFocusable.focus();
            
            // Close on backdrop click
            modal.addEventListener('click', function(e) {
                if (e.target === modal) closeModal(modalId);
            });
            
            // Close on escape key
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') closeModal(modalId);
            });
        }
    }

    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('animate__fadeIn');
            modal.classList.add('animate__fadeOut');
            setTimeout(() => {
                modal.style.display = 'none';
                modal.classList.remove('animate__fadeOut');
                document.body.style.overflow = '';
            }, 300);
        }
    }

    // Camera scanner functionality
    let currentStream = null;
    let facingMode = 'environment';

    async function startCamera() {
        try {
            if (currentStream) {
                currentStream.getTracks().forEach(track => track.stop());
            }
            
            const constraints = {
                video: {
                    facingMode: facingMode,
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            };
            
            currentStream = await navigator.mediaDevices.getUserMedia(constraints);
            const video = document.getElementById('cameraVideo');
            if (video) {
                video.srcObject = currentStream;
            }
        } catch (e) {
            console.error('Camera error:', e);
            // Fallback to file upload
        }
    }

    async function switchCamera() {
        facingMode = facingMode === 'environment' ? 'user' : 'environment';
        await startCamera();
    }

    async function uploadReceipt() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/*';
        input.onchange = async (e) => {
            const file = e.target.files[0];
            if (file) {
                await uploadReceiptBlob(file);
            }
        };
        input.click();
    }

    async function uploadReceiptBlob(blob) {
        try {
            const formData = new FormData();
            formData.append('receipt', blob, 'receipt.jpg');
            
            const response = await fetch('/api/upload-receipt', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const result = await response.json();
                closeModal('cameraModal');
                // Optionally refresh transactions or show success message
                if (app && app.applyFilters) {
                    app.applyFilters();
                }
            }
        } catch (e) {
            console.error('Upload error:', e);
        }
    }

    // Initialize camera when modal opens
    document.addEventListener('DOMContentLoaded', function() {
        const cameraModal = document.getElementById('cameraModal');
        if (cameraModal) {
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
                        if (cameraModal.style.display === 'block') {
                            startCamera();
                        } else if (cameraModal.style.display === 'none') {
                            if (currentStream) {
                                currentStream.getTracks().forEach(track => track.stop());
                                currentStream = null;
                            }
                        }
                    }
                });
            });
            
            observer.observe(cameraModal, { attributes: true });
        }
    });

    // Make functions globally available
    window.toggleTransactionSelection = id => app.toggleTransactionSelection(id);
    window.editTransaction = id => app.editTransaction(id);
    window.duplicateTransaction = id => app.duplicateTransaction(id);
    window.deleteTransaction = id => app.deleteTransaction(id);

    // Modal functionality
    function openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'block';
            modal.classList.add('animate__fadeIn');
            document.body.style.overflow = 'hidden';
            
            // Focus management
            const firstFocusable = modal.querySelector('button, input, select, textarea');
            if (firstFocusable) firstFocusable.focus();
            
            // Close on backdrop click
            modal.addEventListener('click', function(e) {
                if (e.target === modal) closeModal(modalId);
            });
            
            // Close on escape key
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') closeModal(modalId);
            });
        }
    }

    function closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('animate__fadeIn');
            modal.classList.add('animate__fadeOut');
            setTimeout(() => {
                modal.style.display = 'none';
                modal.classList.remove('animate__fadeOut');
                document.body.style.overflow = '';
            }, 300);
        }
    }

    // Camera scanner functionality
    let currentStream = null;
    let facingMode = 'environment';

    async function startCamera() {
        try {
            if (currentStream) {
                currentStream.getTracks().forEach(track => track.stop());
            }
            
            const constraints = {
                video: {
                    facingMode: facingMode,
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            };
            
            currentStream = await navigator.mediaDevices.getUserMedia(constraints);
            const video = document.getElementById('cameraVideo');
            if (video) {
                video.srcObject = currentStream;
            }
        } catch (e) {
            console.error('Camera error:', e);
            // Fallback to file upload
        }
    }

    async function captureReceipt() {
        const video = document.getElementById('cameraVideo');
        const canvas = document.getElementById('cameraCanvas');
        
        if (video && canvas) {
            const context = canvas.getContext('2d');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            context.drawImage(video, 0, 0);
            
            canvas.toBlob(async (blob) => {
                if (blob) {
                    await uploadReceiptBlob(blob);
                }
            }, 'image/jpeg', 0.8);
        }
    }

    async function switchCamera() {
        facingMode = facingMode === 'environment' ? 'user' : 'environment';
        await startCamera();
    }

    async function uploadReceipt() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/*';
        input.onchange = async (e) => {
            const file = e.target.files[0];
            if (file) {
                await uploadReceiptBlob(file);
            }
        };
        input.click();
    }

    async function uploadReceiptBlob(blob) {
        try {
            const formData = new FormData();
            formData.append('receipt', blob, 'receipt.jpg');
            
            const response = await fetch('/api/upload-receipt', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const result = await response.json();
                closeModal('cameraModal');
                // Optionally refresh transactions or show success message
                if (app && app.applyFilters) {
                    app.applyFilters();
                }
            }
        } catch (e) {
            console.error('Upload error:', e);
        }
    }

    // Initialize camera when modal opens
    document.addEventListener('DOMContentLoaded', function() {
        const cameraModal = document.getElementById('cameraModal');
        if (cameraModal) {
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
                        if (cameraModal.style.display === 'block') {
                            startCamera();
                        } else if (cameraModal.style.display === 'none') {
                            if (currentStream) {
                                currentStream.getTracks().forEach(track => track.stop());
                                currentStream = null;
                            }
                        }
                    }
                });
            });
            
            observer.observe(cameraModal, { attributes: true });
        }
    });

    // Make functions globally available
    window.openModal = openModal;
    window.closeModal = closeModal;
    window.captureReceipt = captureReceipt;
    window.switchCamera = switchCamera;
    window.uploadReceipt = uploadReceipt;
}

// Initialize the app when the page loads
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new TallyUpsApp();
});

// Make app globally available
window.app = app;

document.addEventListener('DOMContentLoaded', async function() {
  // Filter controls
  document.getElementById('searchInput').addEventListener('input', function(e) {
    app.setSearch(e.target.value);
  });
  document.getElementById('categoryFilter').addEventListener('change', function(e) {
    app.setCategoryFilter(e.target.value);
  });
  document.getElementById('statusFilter').addEventListener('change', function(e) {
    app.setStatusFilter(e.target.value);
  });
  document.getElementById('dateFrom').addEventListener('change', function(e) {
    app.setDateFrom(e.target.value);
  });
  document.getElementById('dateTo').addEventListener('change', function(e) {
    app.setDateTo(e.target.value);
  });
  document.getElementById('businessTypeFilter').addEventListener('change', function(e) {
    app.setBusinessTypeFilter(e.target.value);
  });
  document.getElementById('amountMin').addEventListener('input', function(e) {
    app.setAmountMin(e.target.value);
  });
  document.getElementById('amountMax').addEventListener('input', function(e) {
    app.setAmountMax(e.target.value);
  });
  document.getElementById('clearFiltersBtn').addEventListener('click', function() {
    app.clearFilters();
  });
  document.getElementById('prevBtn').addEventListener('click', function() {
    app.prevPage();
  });
  document.getElementById('nextBtn').addEventListener('click', function() {
    app.nextPage();
  });

  // Show loading
  app.isLoading = true;
  app.renderTransactions();

  // Fetch transactions
  try {
    const res = await fetch('/api/transactions');
    const data = await res.json();
    app.transactions = data.transactions || [];
    app.filteredTransactions = app.transactions;
    app.isLoading = false;
    app.applyFilters();
  } catch (e) {
    app.isLoading = false;
    document.getElementById('transactionRows').innerHTML = '<div class="loading">Failed to load transactions.</div>';
  }

  // Fetch filter options
  try {
    const res = await fetch('/api/transactions/filters');
    const filters = await res.json();
    // Populate category
    const catSel = document.getElementById('categoryFilter');
    catSel.innerHTML = '<option value="">All Categories</option>' +
      (filters.categories || []).map(c => `<option value="${c}">${c}</option>`).join('');
    // Populate status
    const statusSel = document.getElementById('statusFilter');
    statusSel.innerHTML = '<option value="">All Statuses</option>' +
      (filters.statuses || []).map(s => `<option value="${s}">${s}</option>`).join('');
    // Populate business type
    const bizSel = document.getElementById('businessTypeFilter');
    bizSel.innerHTML = '<option value="">All Types</option>' +
      (filters.business_types || []).map(b => `<option value="${b}">${b}</option>`).join('');
  } catch (e) {
    // fallback: leave dropdowns as is
  }
});

// Animate filter and pagination changes
function animateTransactionRows() {
  const container = document.getElementById('transactionRows');
  container.classList.remove('animate__fadeIn');
  void container.offsetWidth;
  container.classList.add('animate__fadeIn');
}
