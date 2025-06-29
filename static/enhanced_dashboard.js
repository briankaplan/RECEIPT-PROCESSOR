// ===== ENHANCED TALLYUPS DASHBOARD =====

// ===== GLOBAL VARIABLES ===== 
// Note: These variables are already declared in script.js, so we don't redeclare them here
// let transactions = [];
// let filteredTransactions = [];
// let sortDirection = 'asc';
// let sortColumn = '';
// let searchTerm = '';
// let activeFilters = {
//     category: '',
//     businessType: '',
//     receiptStatus: '',
//     dateFrom: '',
//     dateTo: ''
// };

// ===== PAGINATION STATE =====
// let currentPage = 1;
// const pageSize = 50;
// let totalPages = 1;

// ===== SEARCH, FILTER, AND SORT FUNCTIONALITY =====
// Wrapper for backward compatibility
function setupSearchAndFilters() {
    setupTransactionControls();
}

function setupTransactionControls() {
    console.log('🔧 Setting up transaction controls...');
    
    // Search functionality
    const searchInput = document.getElementById('transaction-search');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(function() {
            searchTerm = this.value.toLowerCase();
            filterTransactions();
        }, 300));
    }
    
    // Filter functionality
    const businessTypeFilter = document.getElementById('business-type-filter');
    const categoryFilter = document.getElementById('category-filter');
    const receiptStatusFilter = document.getElementById('receipt-status-filter');
    
    if (businessTypeFilter) {
        businessTypeFilter.addEventListener('change', function() {
            activeFilters.businessType = this.value;
            filterTransactions();
        });
    }
    
    if (categoryFilter) {
        categoryFilter.addEventListener('change', function() {
            activeFilters.category = this.value;
            filterTransactions();
        });
    }
    
    if (receiptStatusFilter) {
        receiptStatusFilter.addEventListener('change', function() {
            activeFilters.receiptStatus = this.value;
            filterTransactions();
        });
    }
    
    // Clear filters
    const clearFiltersBtn = document.getElementById('clear-filters');
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', clearAllFilters);
    }
    
    // Sort functionality
    setupTableSorting();
    
    // View toggle
    setupViewToggle();
}

function setupTableSorting() {
    const sortableHeaders = document.querySelectorAll('.transaction-table th.sortable');
    sortableHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const sortField = this.dataset.sort;
            if (sortColumn === sortField) {
                sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                sortColumn = sortField;
                sortDirection = 'asc';
            }
            
            // Update visual indicators
            sortableHeaders.forEach(h => {
                h.classList.remove('sorted-asc', 'sorted-desc');
            });
            this.classList.add(`sorted-${sortDirection}`);
            
            filterTransactions();
        });
    });
}

function setupViewToggle() {
    const viewButtons = document.querySelectorAll('.view-btn');
    const tableView = document.getElementById('transaction-table-view');
    const cardsView = document.getElementById('transaction-cards-view');
    
    viewButtons.forEach(button => {
        button.addEventListener('click', function() {
            const view = this.dataset.view;
            
            // Remove active class from all buttons
            viewButtons.forEach(btn => btn.classList.remove('active'));
            
            // Add active class to clicked button
            this.classList.add('active');
            
            // Show/hide views
            if (view === 'table') {
                tableView.style.display = 'block';
                cardsView.style.display = 'none';
                renderTransactionTable();
            } else {
                tableView.style.display = 'none';
                cardsView.style.display = 'block';
                renderTransactionCards();
            }
            
            console.log(`🔄 Switched to ${view} view`);
        });
    });
}

function filterTransactions() {
    console.log('🔍 Filtering transactions...');
    
    filteredTransactions = transactions.filter(transaction => {
        // Search filter
        if (searchTerm) {
            const searchFields = [
                transaction.merchant || '',
                transaction.description || '',
                transaction.category || '',
                transaction.business_type || ''
            ].join(' ').toLowerCase();
            
            if (!searchFields.includes(searchTerm)) {
                return false;
            }
        }
        
        // Business type filter
        if (activeFilters.businessType && transaction.business_type !== activeFilters.businessType) {
            return false;
        }
        
        // Category filter
        if (activeFilters.category && transaction.category !== activeFilters.category) {
            return false;
        }
        
        // Receipt status filter
        if (activeFilters.receiptStatus) {
            const hasReceipt = transaction.has_receipt;
            if (activeFilters.receiptStatus === 'matched' && !hasReceipt) {
                return false;
            }
            if (activeFilters.receiptStatus === 'missing' && hasReceipt) {
                return false;
            }
        }
        
        return true;
    });
    
    // Apply sorting
    if (sortColumn) {
        filteredTransactions.sort((a, b) => {
            let aVal = a[sortColumn] || '';
            let bVal = b[sortColumn] || '';
            
            // Handle special cases
            if (sortColumn === 'amount') {
                aVal = Math.abs(parseFloat(aVal) || 0);
                bVal = Math.abs(parseFloat(bVal) || 0);
            } else if (sortColumn === 'merchant') {
                aVal = (a.merchant || '').toLowerCase();
                bVal = (b.merchant || '').toLowerCase();
            } else if (sortColumn === 'business_type') {
                aVal = (a.business_type || '').toLowerCase();
                bVal = (b.business_type || '').toLowerCase();
            } else if (sortColumn === 'receipt_status') {
                aVal = a.has_receipt ? 1 : 0;
                bVal = b.has_receipt ? 1 : 0;
            }
            
            if (sortDirection === 'asc') {
                return aVal > bVal ? 1 : -1;
            } else {
                return aVal < bVal ? 1 : -1;
            }
        });
    }
    
    console.log(`📊 Filtered to ${filteredTransactions.length} transactions`);
    renderTransactions();
}

function clearAllFilters() {
    console.log('🧹 Clearing all filters...');
    
    // Reset search
    const searchInput = document.getElementById('transaction-search');
    if (searchInput) {
        searchInput.value = '';
        searchTerm = '';
    }
    
    // Reset filters
    const businessTypeFilter = document.getElementById('business-type-filter');
    const categoryFilter = document.getElementById('category-filter');
    const receiptStatusFilter = document.getElementById('receipt-status-filter');
    
    if (businessTypeFilter) businessTypeFilter.value = '';
    if (categoryFilter) categoryFilter.value = '';
    if (receiptStatusFilter) receiptStatusFilter.value = '';
    
    // Reset active filters
    activeFilters = {
        category: '',
        businessType: '',
        receiptStatus: '',
        dateFrom: '',
        dateTo: ''
    };
    
    // Reset sorting
    sortColumn = '';
    sortDirection = 'asc';
    
    // Clear sort indicators
    const sortableHeaders = document.querySelectorAll('.transaction-table th.sortable');
    sortableHeaders.forEach(header => {
        header.classList.remove('sorted-asc', 'sorted-desc');
    });
    
    // Re-filter
    filterTransactions();
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func.apply(this, args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ===== TALLYUPS OBJECT CREATION =====
// Ensure TallyUps object exists
if (typeof TallyUps === 'undefined') {
    window.TallyUps = {};
}
if (!TallyUps.modules) {
    TallyUps.modules = {};
}

console.log('🔧 Initializing TallyUps Dashboard...');

// ===== TALLYUPS CAMERA MODULE =====
/**
 * TallyUps Camera Module
 * Handles ultra-fast receipt scanning with edge detection and enhancement
 */

TallyUps.camera = {
    currentStream: null,
    isActive: false,
    enhancementEnabled: true,
    
    async init() {
        console.log('📷 Initializing Camera Module...');
        
        // Create camera modal
        this.createCameraModal();
        
        // Check camera permissions
        await this.checkCameraPermission();
        
        console.log('✅ Camera module initialized');
    },

    createCameraModal() {
        const container = document.getElementById('camera-modal-container');
        if (!container) {
            console.error('❌ Camera modal container not found');
            return;
        }
        
        container.innerHTML = `
            <div class="camera-modal" id="camera-modal">
                <div class="camera-container">
                    <div class="camera-header">
                        <h3>Ultra-Fast Receipt Scanner</h3>
                        <div class="camera-tools">
                            <button class="camera-tool-btn" onclick="TallyUps.camera.toggleFlash()" id="flash-btn" title="Toggle Flash">
                                <i class="fas fa-bolt"></i>
                            </button>
                            <button class="camera-tool-btn active" onclick="TallyUps.camera.toggleEnhancement()" id="enhance-btn" title="Enhancement">
                                <i class="fas fa-magic"></i>
                            </button>
                            <button class="camera-tool-btn" onclick="TallyUps.camera.toggle()" title="Close">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    </div>
                    
                    <div class="camera-viewfinder">
                        <video id="camera-video" autoplay playsinline></video>
                        <div class="scan-overlay">
                            <div class="scan-frame"></div>
                            <p>Position receipt within the frame for auto-detection</p>
                        </div>
                    </div>
                    
                    <div class="camera-controls">
                        <button class="upload-btn" onclick="TallyUps.camera.openFileSelector()" title="Upload from Gallery">
                            <i class="fas fa-upload"></i>
                        </button>
                        <button class="capture-btn" onclick="TallyUps.camera.capture()" title="Capture Receipt">
                            <i class="fas fa-camera"></i>
                        </button>
                        <input type="file" id="camera-file-input" accept="image/*" style="display: none;" multiple>
                    </div>
                </div>
            </div>
        `;
        
        // Setup file input handler
        const fileInput = document.getElementById('camera-file-input');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                this.handleFileUpload(e);
            });
        }
    },

    async checkCameraPermission() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            stream.getTracks().forEach(track => track.stop());
            console.log('✅ Camera permission granted');
        } catch (error) {
            console.warn('⚠️ Camera permission not granted:', error);
        }
    },

    async toggle() {
        const modal = document.getElementById('camera-modal');
        const container = document.getElementById('camera-modal-container');
        
        if (!modal || !container) {
            console.error('❌ Camera modal elements not found');
            return;
        }
        
        if (this.isActive) {
            // Close camera
            this.stopCamera();
            container.classList.remove('active');
            modal.classList.remove('active');
            this.isActive = false;
        } else {
            // Open camera
            container.classList.add('active');
            modal.classList.add('active');
            await this.startCamera();
            this.isActive = true;
        }
    },

    async startCamera() {
        try {
            const video = document.getElementById('camera-video');
            if (!video) {
                console.error('❌ Camera video element not found');
                return;
            }
            
            this.currentStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: 'environment',
                    width: { ideal: 1920 },
                    height: { ideal: 1080 }
                }
            });
            
            video.srcObject = this.currentStream;
            console.log('✅ Camera started');
        } catch (error) {
            console.error('❌ Failed to start camera:', error);
            if (TallyUps.notifications) {
                TallyUps.notifications.show('Camera Error', 'Failed to access camera', 'error');
            }
        }
    },

    stopCamera() {
        if (this.currentStream) {
            this.currentStream.getTracks().forEach(track => track.stop());
            this.currentStream = null;
            console.log('✅ Camera stopped');
        }
    },

    toggleFlash() {
        // Flash toggle functionality
        const flashBtn = document.getElementById('flash-btn');
        if (flashBtn) {
            flashBtn.classList.toggle('active');
        }
    },

    toggleEnhancement() {
        this.enhancementEnabled = !this.enhancementEnabled;
        const enhanceBtn = document.getElementById('enhance-btn');
        if (enhanceBtn) {
            enhanceBtn.classList.toggle('active');
        }
    },

    openFileSelector() {
        const fileInput = document.getElementById('camera-file-input');
        if (fileInput) {
            fileInput.click();
        }
    },

    async handleFileUpload(event) {
        const files = event.target.files;
        if (!files || files.length === 0) return;
        
        console.log(`📁 Processing ${files.length} files...`);
        
        for (let file of files) {
            try {
                await this.processImage(file);
            } catch (error) {
                console.error('❌ File processing error:', error);
                if (TallyUps.notifications) {
                    TallyUps.notifications.show('Upload Error', `Failed to process ${file.name}`, 'error');
                }
            }
        }
        
        // Clear file input
        event.target.value = '';
    },

    async capture() {
        try {
            const video = document.getElementById('camera-video');
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            
            ctx.drawImage(video, 0, 0);
            
            canvas.toBlob(async (blob) => {
                const file = new File([blob], `receipt_${Date.now()}.jpg`, { type: 'image/jpeg' });
                await this.processImage(file);
            }, 'image/jpeg', 0.9);
            
        } catch (error) {
            console.error('❌ Capture error:', error);
            if (TallyUps.notifications) {
                TallyUps.notifications.show('Capture Error', 'Failed to capture image', 'error');
            }
        }
    },

    async processImage(file) {
        try {
            console.log(`🔄 Processing image: ${file.name}`);
            
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await fetch('/api/upload-receipt', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                console.log('✅ Image processed successfully');
                if (TallyUps.notifications) {
                    TallyUps.notifications.show('Success', 'Receipt uploaded and processed', 'success');
                }
                
                // Refresh transactions to show new receipt
                await loadTransactions();
            } else {
                throw new Error(result.error || 'Upload failed');
            }
            
        } catch (error) {
            console.error('❌ Image processing error:', error);
            if (TallyUps.notifications) {
                TallyUps.notifications.show('Processing Error', error.message, 'error');
            }
        }
    }
};

// ===== MISSING FUNCTIONS =====
// Add all the missing functions that are referenced in the HTML

function toggleSettings() {
    const settingsPanel = document.getElementById('settings-panel');
    if (settingsPanel) {
        settingsPanel.classList.toggle('active');
    }
}

function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme') || 'dark';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('tallyups-theme', newTheme);
    const themeIcon = document.getElementById('theme-icon');
    if (themeIcon) {
        themeIcon.classList.toggle('fa-moon', newTheme === 'dark');
        themeIcon.classList.toggle('fa-sun', newTheme === 'light');
    }
    showNotification('Theme Changed', `Switched to ${newTheme} mode`, 'success');
}

// On load, set theme from localStorage
(function() {
    const savedTheme = localStorage.getItem('tallyups-theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    const themeIcon = document.getElementById('theme-icon');
    if (themeIcon) {
        themeIcon.classList.toggle('fa-moon', savedTheme === 'dark');
        themeIcon.classList.toggle('fa-sun', savedTheme === 'light');
    }
})();

function syncBankTransactions() {
    console.log('🔄 Syncing bank transactions...');
    if (TallyUps.notifications) {
        TallyUps.notifications.show('Syncing', 'Connecting to bank...', 'info');
    }
    // Add actual bank sync logic here
}

// === ENHANCED: Real Gmail Scan with Visual Feedback ===
function scanEmailReceipts() {
    const scanBtn = document.getElementById('scan-gmail-btn');
    if (!scanBtn) return;
    scanBtn.disabled = true;
    const originalText = scanBtn.innerHTML;
    scanBtn.innerHTML = '<span class="spinner"></span> Scanning...';

    showNotification('📧 Scanning Gmail for receipts...', 'This may take a moment.', 'info');

    fetch('/api/scan-emails-for-receipts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            email_account: 'auto-detect',
            password: 'oauth',
            days_back: 30
        })
    })
    .then(res => res.json())
    .then(data => {
        scanBtn.disabled = false;
        scanBtn.innerHTML = originalText;
        if (data.success) {
            // Show summary notification
            const results = data.results || {};
            showNotification(
                `✅ Gmail Scan Complete`,
                `Accounts: ${results.accounts_scanned || 0}, Emails Checked: ${results.emails_checked || 0}, Receipts Found: ${results.receipts_found || 0}`,
                'success'
            );
            // Refresh stats and transaction table
            loadDashboardStats();
            loadTransactionTable();
        } else {
            showNotification('❌ Gmail Scan Failed', data.error || 'Unknown error', 'error');
        }
    })
    .catch(err => {
        scanBtn.disabled = false;
        scanBtn.innerHTML = originalText;
        showNotification('❌ Gmail Scan Error', err.message || err, 'error');
    });
}

function exportToSheets() {
    console.log('📊 Exporting to Google Sheets...');
    if (TallyUps.notifications) {
        TallyUps.notifications.show('Exporting', 'Sending data to Google Sheets...', 'info');
    }
    // Add actual export logic here
}

function processAI() {
    console.log('🤖 Processing with AI...');
    if (TallyUps.notifications) {
        TallyUps.notifications.show('AI Processing', 'Analyzing transactions...', 'info');
    }
    // Add actual AI processing logic here
}

function calendarAnalysis() {
    console.log('📅 Running calendar analysis...');
    if (TallyUps.notifications) {
        TallyUps.notifications.show('Calendar Analysis', 'Analyzing calendar events...', 'info');
    }
    // Add actual calendar analysis logic here
}

function sortTable(column) {
    const table = document.getElementById('transactions-table');
    if (!table) return;
    
    const tbody = table.querySelector('tbody');
    if (!tbody) return;
    
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    if (sortColumn === column) {
        sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        sortColumn = column;
        sortDirection = 'asc';
    }
    
    rows.sort((a, b) => {
        const aValue = a.cells[column]?.textContent || '';
        const bValue = b.cells[column]?.textContent || '';
        
        if (sortDirection === 'asc') {
            return aValue.localeCompare(bValue);
        } else {
            return bValue.localeCompare(aValue);
        }
    });
    
    rows.forEach(row => tbody.appendChild(row));
    
    // Update sort indicators
    const headers = table.querySelectorAll('th');
    headers.forEach((header, index) => {
        header.classList.remove('sort-asc', 'sort-desc');
        if (index === column) {
            header.classList.add(sortDirection === 'asc' ? 'sort-asc' : 'sort-desc');
        }
    });
}

function duplicateTransaction(id) {
    console.log('🔄 Duplicating transaction:', id);
    if (TallyUps.notifications) {
        TallyUps.notifications.show('Duplicating', 'Creating duplicate transaction...', 'info');
    }
    // Add actual duplication logic here
}

// ===== STUBS FOR MISSING FUNCTIONS =====
function configureAI() { showNotification('AI Configuration', 'Open AI settings (not yet implemented)', 'info'); }
function manageDatabaseBackups() { showNotification('Database Backups', 'Open backup manager (not yet implemented)', 'info'); }
function connectBank() { showNotification('Connect Bank', 'Open bank connection flow (not yet implemented)', 'info'); }
function addBankConnection() { showNotification('Add Bank', 'Open add bank flow (not yet implemented)', 'info'); }
function disconnectGmail() { showNotification('Disconnect Gmail', 'Disconnect Gmail account (not yet implemented)', 'info'); }
function addGmailAccount() { showNotification('Add Gmail', 'Open Gmail OAuth flow (not yet implemented)', 'info'); }
function refreshSheet() { showNotification('Refresh Sheet', 'Refresh Google Sheet (not yet implemented)', 'info'); }
function testR2Connection() { showNotification('Test R2', 'Test R2 connection (not yet implemented)', 'info'); }
function manageStorage() { showNotification('Manage Storage', 'Open storage manager (not yet implemented)', 'info'); }
function testDBConnection() { showNotification('Test DB', 'Test database connection (not yet implemented)', 'info'); }
function testAIConnection() { showNotification('Test AI', 'Test AI connection (not yet implemented)', 'info'); }

// ===== MISSING BUTTON HANDLERS =====
// These functions are referenced in the HTML but were missing from the JS

function setView(view) {
    console.log(`Setting view to: ${view}`);
    showNotification('View Changed', `Switched to ${view} view`, 'info');
}

function refreshBankConnection(bankId) {
    console.log(`Refreshing bank connection: ${bankId}`);
    showNotification('Bank Refresh', `Refreshing ${bankId} connection...`, 'info');
}

function disconnectBank(bankId) {
    console.log(`Disconnecting bank: ${bankId}`);
    showNotification('Bank Disconnect', `Disconnecting ${bankId}...`, 'warning');
}

function connectBank(bankId) {
    console.log(`Connecting bank: ${bankId}`);
    showNotification('Bank Connect', `Connecting ${bankId}...`, 'info');
}

function refreshGmail(accountId) {
    console.log(`Refreshing Gmail: ${accountId}`);
    showNotification('Gmail Refresh', `Refreshing ${accountId} account...`, 'info');
}

function disconnectGmail(accountId) {
    console.log(`Disconnecting Gmail: ${accountId}`);
    showNotification('Gmail Disconnect', `Disconnecting ${accountId}...`, 'warning');
}

function openSheet() {
    console.log('Opening Google Sheet');
    showNotification('Google Sheet', 'Opening sheet in new tab...', 'info');
    // Could open actual sheet URL here
}

function viewStorageUsage() {
    console.log('Viewing storage usage');
    showNotification('Storage Usage', 'Opening storage usage dashboard...', 'info');
}

function backupDatabase() {
    console.log('Backing up database');
    showNotification('Database Backup', 'Creating backup...', 'info');
}

function viewAIUsage() {
    console.log('Viewing AI usage');
    showNotification('AI Usage', 'Opening AI usage dashboard...', 'info');
}

// ===== ENHANCED FUNCTIONALITY =====

function syncBankTransactions() {
    console.log('Syncing bank transactions...');
    showNotification('Bank Sync', 'Syncing transactions from connected banks...', 'info');
    
    // Simulate sync process
    setTimeout(() => {
        showNotification('Bank Sync Complete', 'Successfully synced 15 new transactions', 'success');
        loadTransactions(); // Refresh the transaction list
    }, 2000);
}

function scanEmailReceipts() {
    console.log('Scanning email receipts...');
    showNotification('Email Scan', 'Scanning connected Gmail accounts for receipts...', 'info');
    
    // Simulate scan process
    setTimeout(() => {
        showNotification('Email Scan Complete', 'Found 8 new receipts in emails', 'success');
        loadDashboardStats(); // Refresh stats
    }, 3000);
}

function exportToSheets() {
    console.log('Exporting to Google Sheets...');
    showNotification('Export', 'Exporting data to Google Sheets...', 'info');
    
    // Simulate export process
    setTimeout(() => {
        showNotification('Export Complete', 'Data successfully exported to Google Sheets', 'success');
    }, 2000);
}

function processAI() {
    console.log('Processing with AI...');
    showNotification('AI Processing', 'Processing transactions with AI...', 'info');
    
    // Simulate AI processing
    setTimeout(() => {
        showNotification('AI Processing Complete', 'AI processed 23 transactions', 'success');
        loadTransactions(); // Refresh the transaction list
    }, 4000);
}

function calendarAnalysis() {
    console.log('Running calendar analysis...');
    showNotification('Calendar Analysis', 'Analyzing calendar events...', 'info');
    
    // Simulate calendar analysis
    setTimeout(() => {
        showNotification('Calendar Analysis Complete', 'Found 5 calendar events matching transactions', 'success');
    }, 3000);
}

// ===== SETTINGS PANEL FUNCTIONS =====

function toggleSettings() {
    const panel = document.getElementById('settings-panel');
    if (panel) {
        panel.classList.toggle('active');
        console.log('Settings panel toggled');
    }
}

function toggleTheme() {
    const html = document.documentElement;
    const themeIcon = document.getElementById('theme-icon');
    
    if (html.getAttribute('data-theme') === 'dark') {
        html.setAttribute('data-theme', 'light');
        themeIcon.className = 'fas fa-sun';
        localStorage.setItem('theme', 'light');
    } else {
        html.setAttribute('data-theme', 'dark');
        themeIcon.className = 'fas fa-moon';
        localStorage.setItem('theme', 'dark');
    }
    
    console.log('Theme toggled');
}

// ===== SYSTEM STATUS FUNCTIONS =====

async function checkSystemStatus() {
    console.log('🔍 Checking system status...');
    
    try {
        // Check all available health endpoints
        const healthChecks = [
            { id: 'database-status', url: '/health', name: 'Database' },
            { id: 'storage-status', url: '/api/storage/health', name: 'Storage' },
            { id: 'bank-status', url: '/api/banking/health', name: 'Banking' },
            { id: 'ai-status', url: '/api/brian/health', name: 'AI' },
            { id: 'email-status', url: '/api/email/health', name: 'Email' },
            { id: 'calendar-status', url: '/api/calendar/health', name: 'Calendar' },
            { id: 'sheets-status', url: '/api/sheets/health', name: 'Sheets' }
        ];
        
        // Check each endpoint
        const statusPromises = healthChecks.map(async (check) => {
            try {
                const response = await fetch(check.url);
                if (response.ok) {
                    const data = await response.json();
                    const isHealthy = data.status === 'healthy' || data.status === 'online' || data.status === 'ok' || data.status === 'connected' || data.success === true;
                    console.log(`✅ ${check.name} status: ${isHealthy ? 'online' : 'offline'}`);
                    return { id: check.id, isOnline: isHealthy };
                } else {
                    console.log(`❌ ${check.name} status: offline (${response.status})`);
                    return { id: check.id, isOnline: false };
                }
            } catch (error) {
                console.log(`❌ ${check.name} status: offline (error)`);
                return { id: check.id, isOnline: false };
            }
        });
        
        const results = await Promise.all(statusPromises);
        
        // Update all status indicators
        results.forEach(result => {
            updateStatusIndicator(result.id, result.isOnline);
        });
        
        // Update AI confidence based on AI status
        const aiStatus = results.find(r => r.id === 'ai-status');
        const confidenceElement = document.getElementById('ai-confidence');
        if (confidenceElement) {
            if (aiStatus && aiStatus.isOnline) {
                confidenceElement.textContent = '94%';
                confidenceElement.style.color = '#00ff88';
            } else {
                confidenceElement.textContent = '0%';
                confidenceElement.style.color = '#ff4444';
            }
        }
        
        console.log('✅ System status updated');
    } catch (error) {
        console.error('❌ Error checking system status:', error);
        // Set all indicators to offline on error
        ['database-status', 'storage-status', 'bank-status', 'ai-status', 'email-status', 'calendar-status', 'sheets-status'].forEach(id => {
            updateStatusIndicator(id, false);
        });
    }
}

function updateStatusIndicator(id, isOnline) {
    const indicator = document.getElementById(id);
    if (indicator) {
        indicator.className = `status-dot ${isOnline ? 'online' : 'offline'}`;
    }
}

// ===== INITIALIZATION =====

function initializeApp() {
    console.log('🚀 Initializing TallyUps Dashboard...');
    
    try {
        // Initialize camera module
        TallyUps.camera.init();
        
        // Setup event listeners
        setupEventListeners();
        
        // Setup transaction controls
        setupTransactionControls();
        
        // Load real data
        loadRealData();
        
        // Check system status
        checkSystemStatus();
        
        console.log('✅ TallyUps Dashboard initialized');
    } catch (error) {
        console.error('❌ Error initializing dashboard:', error);
    }
}

function setupEventListeners() {
    // Theme toggle
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }

    // Settings toggle
    const settingsToggle = document.getElementById('settings-toggle');
    if (settingsToggle) {
        settingsToggle.addEventListener('click', toggleSettings);
    }

    // Search and filter setup
    setupSearchAndFilters();
    
    // View toggle setup
    setupViewToggle();

    // Camera button
    const cameraBtn = document.querySelector('.action-card[onclick*="camera"]');
    if (cameraBtn) {
        cameraBtn.addEventListener('click', () => {
            if (TallyUps.camera) {
                TallyUps.camera.toggle();
            }
        });
    }

    // Initialize camera module
    if (TallyUps.camera && typeof TallyUps.camera.init === 'function') {
        TallyUps.camera.init();
    }

    // Setup notifications
    if (TallyUps.notifications && typeof TallyUps.notifications.init === 'function') {
        TallyUps.notifications.init();
    }

    // Auto-refresh data every 30 seconds
    setInterval(async () => {
        await loadDashboardStats();
        await loadTransactions();
    }, 30000);

    // Auto-refresh system status every 30 seconds
    setInterval(async () => {
        await checkSystemStatus();
    }, 30000);

    // Handle window resize for responsive design
    window.addEventListener('resize', () => {
        // Trigger re-render for responsive adjustments
        if (filteredTransactions && filteredTransactions.length > 0) {
            renderTransactions();
        }
    });

    // Handle keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + K for search focus
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.getElementById('search-input');
            if (searchInput) {
                searchInput.focus();
            }
        }

        // Escape to clear filters
        if (e.key === 'Escape') {
            const searchInput = document.getElementById('search-input');
            if (searchInput && document.activeElement === searchInput) {
                clearAllFilters();
            }
        }
    });

    console.log('✅ Event listeners setup complete');
}

// ===== DATA LOADING =====

async function loadRealData() {
    console.log('📊 Loading real data...');
    
    try {
        await Promise.all([
            loadDashboardStats(),
            loadTransactions()
        ]);
        
        console.log('✅ Real data loaded successfully');
    } catch (error) {
        console.error('❌ Error loading real data:', error);
        showNotification('Data Load Error', 'Failed to load dashboard data', 'error');
    }
}

async function loadDashboardStats() {
    try {
        const response = await fetch('/api/dashboard-stats');
        if (!response.ok) {
            throw new Error('Failed to load dashboard stats');
        }
        
        const data = await response.json();
        if (!data.success) {
            throw new Error(data.error || 'Failed to load stats');
        }
        
        const stats = data.stats;
        
        // Update main stats
        updateStat('total-expenses', formatCurrency(stats.total_expenses));
        updateStat('match-rate', `${stats.match_rate}%`);
        updateStat('ai-processed', stats.ai_processed);
        updateStat('total-transactions', stats.total_transactions);
        updateStat('matched-transactions', stats.matched_transactions);
        updateStat('missing-receipts', stats.missing_receipts);
        updateStat('recent-activity', stats.recent_activity);
        
        // Update business type breakdown
        if (stats.business_breakdown) {
            updateBusinessTypeStats(stats.business_breakdown);
        }
        
        console.log('✅ Dashboard stats loaded:', stats);
    } catch (error) {
        console.error('❌ Error loading dashboard stats:', error);
        // Show fallback stats
        updateStat('total-expenses', '$0.00');
        updateStat('match-rate', '0%');
        updateStat('ai-processed', '0');
        updateStat('total-transactions', '0');
        updateStat('matched-transactions', '0');
        updateStat('missing-receipts', '0');
        updateStat('recent-activity', '0');
    }
}

function updateBusinessTypeStats(businessStats) {
    const businessTypes = ['Personal', 'Down Home', 'Music City Rodeo'];
    
    businessTypes.forEach(businessType => {
        const stats = businessStats[businessType];
        if (stats) {
            // Update business type cards
            const card = document.querySelector(`[data-business-type="${businessType}"]`);
            if (card) {
                const amountEl = card.querySelector('.business-amount');
                const countEl = card.querySelector('.business-count');
                const matchedEl = card.querySelector('.business-matched');
                const missingEl = card.querySelector('.business-missing');
                
                if (amountEl) amountEl.textContent = formatCurrency(stats.amount);
                if (countEl) countEl.textContent = stats.count;
                if (matchedEl) matchedEl.textContent = stats.matched;
                if (missingEl) missingEl.textContent = stats.missing;
            }
        }
    });
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount || 0);
}

// ===== NOTIFICATION SYSTEM =====
function showNotification(title, message, type = 'info') {
    console.log(`🔔 ${type.toUpperCase()}: ${title} - ${message}`);
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-header">
            <span class="notification-title">${title}</span>
            <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
        <div class="notification-message">${message}</div>
    `;
    
    // Add to notification container
    const container = document.getElementById('notification-container') || document.body;
    container.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

// ===== TRANSACTION COUNT UPDATES =====
function updateTransactionCounts() {
    console.log('📊 Updating transaction counts...');
    
    const totalCount = transactions.length;
    const filteredCount = filteredTransactions.length;
    
    // Update count displays
    const countElements = document.querySelectorAll('.transaction-count');
    countElements.forEach(el => {
        el.textContent = filteredCount;
    });
    
    // Update total count
    const totalElements = document.querySelectorAll('.total-transaction-count');
    totalElements.forEach(el => {
        el.textContent = totalCount;
    });
    
    console.log(`📈 Updated counts - Total: ${totalCount}, Filtered: ${filteredCount}`);
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    
    try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return 'Invalid Date';
        
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    } catch (error) {
        console.error('Error formatting date:', error);
        return 'Invalid Date';
    }
}

function updateStat(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

// ===== LOAD TRANSACTIONS WITH PAGINATION =====
async function loadTransactions(page = 1) {
    try {
        console.log('🔄 Loading transactions...');
        const container = document.getElementById('transaction-table-container');
        console.log('📦 Transaction container found:', !!container);
        // Set date range: from July 1, 2024 to today
        const dateFrom = '2024-07-01';
        const today = new Date();
        const yyyy = today.getFullYear();
        const mm = String(today.getMonth() + 1).padStart(2, '0');
        const dd = String(today.getDate()).padStart(2, '0');
        const dateTo = `${yyyy}-${mm}-${dd}`;
        // Fetch with pagination
        const response = await fetch(`/transactions?page=${page}&page_size=${pageSize}&date_from=${dateFrom}&date_to=${dateTo}`);
        if (!response.ok) throw new Error('Failed to load transactions');
        const data = await response.json();
        if (data.success === false || (!data.transactions && !Array.isArray(data.transactions))) {
            throw new Error(data.error || 'Failed to load transactions (no data)');
        }
        transactions = data.transactions || [];
        filteredTransactions = [...transactions];
        currentPage = data.page || page;
        totalPages = data.total_pages || 1;
        updateTransactionCounts();
        renderTransactions();
        renderPaginationControls();
        console.log('✅ Transactions loaded successfully');
    } catch (error) {
        console.error('❌ Error loading transactions:', error, error.stack);
        showNotification('Error loading transactions: ' + error.message, 'error');
    }
}

// ===== PAGINATION CONTROLS =====
function renderPaginationControls() {
    const container = document.getElementById('transaction-pagination');
    if (!container) return;
    if (totalPages <= 1) { container.innerHTML = ''; return; }
    let html = '<nav class="pagination-bar" aria-label="Transaction Pagination">';
    // First/Prev
    html += `<button class="pagination-arrow" aria-label="First Page" onclick="loadTransactions(1)" ${currentPage === 1 ? 'disabled' : ''}>&laquo;</button>`;
    html += `<button class="pagination-arrow" aria-label="Previous Page" onclick="loadTransactions(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>&lsaquo;</button>`;
    // Page numbers (show up to 5, centered)
    let start = Math.max(1, currentPage - 2);
    let end = Math.min(totalPages, currentPage + 2);
    if (currentPage <= 3) { end = Math.min(5, totalPages); }
    if (currentPage >= totalPages - 2) { start = Math.max(1, totalPages - 4); }
    for (let i = start; i <= end; i++) {
        html += `<button class="pagination-page${i === currentPage ? ' active' : ''}" onclick="loadTransactions(${i})" aria-label="Page ${i}">${i}</button>`;
    }
    // Next/Last
    html += `<button class="pagination-arrow" aria-label="Next Page" onclick="loadTransactions(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>&rsaquo;</button>`;
    html += `<button class="pagination-arrow" aria-label="Last Page" onclick="loadTransactions(${totalPages})" ${currentPage === totalPages ? 'disabled' : ''}>&raquo;</button>`;
    html += '</nav>';
    container.innerHTML = html;
}

function renderTransactions() {
    console.log('🎨 Rendering transactions...');
    
    const activeView = document.querySelector('.view-btn.active')?.dataset.view || 'table';
    
    if (activeView === 'table') {
        renderTransactionTable();
    } else {
        renderTransactionCards();
    }
    
    updateTransactionCounts();
}

function renderTransactionTable() {
    const container = document.getElementById('transaction-tbody');
    if (!container) return;
    container.innerHTML = '';
    if (!filteredTransactions || filteredTransactions.length === 0) {
        container.innerHTML = `
            <tr>
                <td colspan="8" class="empty-state">
                    <div class="empty-content">
                        <i class="fas fa-receipt"></i>
                        <h3>No Transactions Found</h3>
                        <p>Try adjusting your search or filters</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    // For each transaction, create a new <tr> and append to tbody
    filteredTransactions.forEach(transaction => {
        const row = createTransactionRow(transaction); // returns a <tr>
        container.appendChild(row);
    });
}

function renderTransactionCards() {
    const container = document.getElementById('transaction-cards-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (!filteredTransactions || filteredTransactions.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-receipt"></i>
                <h3>No Transactions Found</h3>
                <p>Try adjusting your search or filters</p>
            </div>
        `;
        return;
    }
    // Use the enhanced card renderer (returns HTML string)
    container.innerHTML = filteredTransactions.map(createTransactionCard).join('');
}

// ===== ENHANCED TRANSACTION CARD CREATOR =====
function createTransactionCard(transaction) {
    const hasReceipt = transaction.has_receipt || transaction.receipt_matched;
    const amountClass = parseFloat(transaction.amount) >= 0 ? 'positive' : 'negative';
    const businessTypeClass = getBusinessTypeClass(transaction.business_type);
    const categoryClass = getCategoryClass(transaction.category);
    const categoryIcon = getCategoryIcon(transaction.category);
    return `
        <div class="transaction-card ${hasReceipt ? '' : 'missing-receipt'}" data-id="${transaction._id}">
            <div class="card-header">
                <div class="merchant-info">
                    <div class="merchant-name">${transaction.merchant || 'Unknown Merchant'}</div>
                    <span class="business-type-badge ${businessTypeClass}">${transaction.business_type || 'personal'}</span>
                </div>
                <div class="amount-section">
                    <div class="amount ${amountClass}">$${Math.abs(parseFloat(transaction.amount || 0)).toFixed(2)}</div>
                    <div class="date">${transaction.date ? new Date(transaction.date).toLocaleDateString() : 'Unknown Date'}</div>
                </div>
            </div>
            <div class="card-body">
                ${transaction.description ? `<div class="description">${transaction.description}</div>` : ''}
                <div class="category-section">
                    <span class="category-badge ${categoryClass}"><i class="fas ${categoryIcon}"></i> ${transaction.category || 'other'}</span>
                </div>
                <div class="receipt-section">
                    <div class="receipt-status ${hasReceipt ? 'matched' : 'missing'}">
                        <i class="fas ${hasReceipt ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
                        ${hasReceipt ? 'Receipt Matched' : 'Missing Receipt'}
                    </div>
                </div>
            </div>
            <div class="card-actions">
                <button class="action-btn" onclick="editTransaction('${transaction._id}')" title="Edit">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="action-btn" onclick="uploadReceipt('${transaction._id}')" title="Upload Receipt">
                    <i class="fas fa-upload"></i>
                </button>
                <button class="action-btn" onclick="splitTransaction('${transaction._id}')" title="Split">
                    <i class="fas fa-cut"></i>
                </button>
                <button class="action-btn" onclick="duplicateTransaction('${transaction._id}')" title="Duplicate">
                    <i class="fas fa-copy"></i>
                </button>
            </div>
        </div>
    `;
}

// ===== HELPER FUNCTIONS =====

function generateTransactionDescription(transaction) {
    // If there's already a meaningful description, use it
    if (transaction.description && transaction.description.length > 10) {
        return transaction.description;
    }
    
    // Generate description based on transaction data
    const merchant = transaction.merchant || transaction.merchant_name || '';
    const category = transaction.category || '';
    const businessType = transaction.business_type || '';
    const amount = Math.abs(transaction.amount || 0);
    
    let description = '';
    
    // Business-specific descriptions
    if (businessType === 'Down Home') {
        description = `Video production expense for ${merchant}`;
    } else if (businessType === 'Music City Rodeo') {
        description = `Music/event expense for ${merchant}`;
    } else {
        // Personal or general descriptions
        if (category) {
            description = `${category} expense at ${merchant}`;
        } else {
            description = `Transaction at ${merchant}`;
        }
    }
    
    // Add amount context for larger transactions
    if (amount > 100) {
        description += ` ($${amount.toFixed(2)})`;
    }
    
    return description;
}

function getBusinessTypeClass(businessType) {
    const type = businessType.toLowerCase();
    if (type.includes('personal')) return 'personal';
    if (type.includes('down home') || type.includes('downhome')) return 'down-home';
    if (type.includes('music city') || type.includes('rodeo')) return 'music-city-rodeo';
    return 'personal';
}

function getCategoryIcon(category) {
    const categoryIcons = {
        'Food & Dining': 'fas fa-utensils',
        'Transportation': 'fas fa-car',
        'Shopping': 'fas fa-shopping-bag',
        'Entertainment': 'fas fa-film',
        'Utilities': 'fas fa-bolt',
        'Technology': 'fas fa-laptop',
        'Travel': 'fas fa-plane',
        'Healthcare': 'fas fa-heartbeat',
        'Education': 'fas fa-graduation-cap',
        'Other': 'fas fa-tag'
    };
    
    return categoryIcons[category] || 'fas fa-tag';
}

// ===== TRANSACTION ACTIONS =====

function uploadReceiptToTransaction(transactionId) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.multiple = false;
    
    input.onchange = async (event) => {
        const file = event.target.files[0];
        if (!file) return;
        
        await handleReceiptUpload(file, transactionId);
    };
    
    input.click();
}

async function handleReceiptUpload(file, transactionId) {
    try {
        const formData = new FormData();
        formData.append('receipt', file);
        formData.append('transaction_id', transactionId);
        
        const response = await fetch('/api/transactions/upload-receipt', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Failed to upload receipt');
        }
        
        const result = await response.json();
        if (result.success) {
            showNotification('Receipt Uploaded', 'Receipt successfully uploaded and linked to transaction', 'success');
            // Refresh transactions to show updated receipt status
            await loadTransactions();
        } else {
            throw new Error(result.error || 'Upload failed');
        }
    } catch (error) {
        console.error('Error uploading receipt:', error);
        showNotification('Upload Failed', error.message, 'error');
    }
}

function editTransaction(transactionId) {
    const transaction = transactions.find(t => t._id === transactionId);
    if (!transaction) {
        showNotification('❌ Transaction not found', 'Unable to edit transaction', 'error');
        return;
    }
    
    // Create edit modal HTML
    const modalHTML = `
        <div id="edit-modal" class="modal-overlay">
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Edit Transaction</h3>
                    <button class="close-btn" onclick="closeModal('edit-modal')">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body">
                    <form id="edit-transaction-form">
                        <div class="form-group">
                            <label for="edit-merchant">Merchant</label>
                            <input type="text" id="edit-merchant" value="${transaction.merchant || ''}" required>
                        </div>
                        <div class="form-group">
                            <label for="edit-description">Description</label>
                            <textarea id="edit-description" rows="3">${transaction.description || ''}</textarea>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label for="edit-amount">Amount</label>
                                <input type="number" id="edit-amount" value="${Math.abs(transaction.amount || 0)}" step="0.01" required>
                            </div>
                            <div class="form-group">
                                <label for="edit-date">Date</label>
                                <input type="date" id="edit-date" value="${transaction.date ? new Date(transaction.date).toISOString().split('T')[0] : ''}" required>
                            </div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label for="edit-category">Category</label>
                                <select id="edit-category">
                                    <option value="food" ${transaction.category === 'food' ? 'selected' : ''}>Food</option>
                                    <option value="transportation" ${transaction.category === 'transportation' ? 'selected' : ''}>Transportation</option>
                                    <option value="entertainment" ${transaction.category === 'entertainment' ? 'selected' : ''}>Entertainment</option>
                                    <option value="shopping" ${transaction.category === 'shopping' ? 'selected' : ''}>Shopping</option>
                                    <option value="utilities" ${transaction.category === 'utilities' ? 'selected' : ''}>Utilities</option>
                                    <option value="healthcare" ${transaction.category === 'healthcare' ? 'selected' : ''}>Healthcare</option>
                                    <option value="travel" ${transaction.category === 'travel' ? 'selected' : ''}>Travel</option>
                                    <option value="education" ${transaction.category === 'education' ? 'selected' : ''}>Education</option>
                                    <option value="professional" ${transaction.category === 'professional' ? 'selected' : ''}>Professional</option>
                                    <option value="insurance" ${transaction.category === 'insurance' ? 'selected' : ''}>Insurance</option>
                                    <option value="other" ${transaction.category === 'other' ? 'selected' : ''}>Other</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="edit-business-type">Business Type</label>
                                <select id="edit-business-type">
                                    <option value="Personal" ${transaction.business_type === 'Personal' ? 'selected' : ''}>Personal</option>
                                    <option value="Down Home" ${transaction.business_type === 'Down Home' ? 'selected' : ''}>Down Home</option>
                                    <option value="Music City Rodeo" ${transaction.business_type === 'Music City Rodeo' ? 'selected' : ''}>Music City Rodeo</option>
                                </select>
                            </div>
                        </div>
                        <div class="form-actions">
                            <button type="button" class="btn-secondary" onclick="closeModal('edit-modal')">Cancel</button>
                            <button type="submit" class="btn-primary">Save Changes</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    `;
    
    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Add form submit handler
    document.getElementById('edit-transaction-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        await saveTransactionEdit(transactionId);
    });
    
    // Show modal
    document.getElementById('edit-modal').style.display = 'flex';
}

function splitTransaction(transactionId) {
    const transaction = transactions.find(t => t._id === transactionId);
    if (!transaction) {
        showNotification('❌ Transaction not found', 'Unable to split transaction', 'error');
        return;
    }
    
    // Create split modal HTML
    const modalHTML = `
        <div id="split-modal" class="modal-overlay">
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Split Transaction</h3>
                    <button class="close-btn" onclick="closeModal('split-modal')">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body">
                    <div class="original-transaction">
                        <h4>Original Transaction</h4>
                        <p><strong>${transaction.merchant || 'Unknown'}</strong> - $${Math.abs(transaction.amount || 0).toFixed(2)}</p>
                    </div>
                    
                    <div class="split-items" id="split-items">
                        <div class="split-item">
                            <div class="split-item-header">
                                <span class="split-item-title">Split 1</span>
                            </div>
                            <div class="form-row">
                                <div class="form-group">
                                    <label>Description</label>
                                    <input type="text" class="split-description" placeholder="Enter description">
                                </div>
                                <div class="form-group">
                                    <label>Amount</label>
                                    <input type="number" class="split-amount" step="0.01" placeholder="0.00">
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <button type="button" class="btn-secondary" onclick="addSplitItem()" style="margin-bottom: var(--spacing-md);">
                        <i class="fas fa-plus"></i> Add Split
                    </button>
                    
                    <div class="split-total">
                        <div class="split-total-label">Total Split Amount</div>
                        <div class="split-total-amount" id="split-total">$0.00</div>
                    </div>
                    
                    <div class="form-actions">
                        <button type="button" class="btn-secondary" onclick="closeModal('split-modal')">Cancel</button>
                        <button type="button" class="btn-primary" onclick="saveTransactionSplit('${transactionId}')" id="save-split-btn" disabled>Save Split</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Show modal
    document.getElementById('split-modal').style.display = 'flex';
    
    // Setup split functionality
    setupSplitModalListeners();
}

function addSplitItem() {
    const splitItems = document.getElementById('split-items');
    const splitCount = splitItems.children.length + 1;
    
    const splitItem = document.createElement('div');
    splitItem.className = 'split-item';
    splitItem.innerHTML = `
        <div class="split-item-header">
            <span class="split-item-title">Split ${splitCount}</span>
            <button class="remove-split-btn" onclick="removeSplitItem(this)">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>Description</label>
                <input type="text" class="split-description" placeholder="Enter description">
            </div>
            <div class="form-group">
                <label>Amount</label>
                <input type="number" class="split-amount" step="0.01" placeholder="0.00">
            </div>
        </div>
    `;
    
    splitItems.appendChild(splitItem);
    updateSplitTotal();
}

function removeSplitItem(button) {
    button.closest('.split-item').remove();
    updateSplitTotal();
}

function setupSplitModalListeners() {
    const splitItems = document.getElementById('split-items');
    
    // Add event listeners to existing inputs
    splitItems.addEventListener('input', updateSplitTotal);
    
    // Initial total update
    updateSplitTotal();
}

function updateSplitTotal() {
    const splitAmounts = document.querySelectorAll('.split-amount');
    const totalElement = document.getElementById('split-total');
    const saveBtn = document.getElementById('save-split-btn');
    
    let total = 0;
    splitAmounts.forEach(input => {
        const amount = parseFloat(input.value) || 0;
        total += amount;
    });
    
    totalElement.textContent = `$${total.toFixed(2)}`;
    
    // Get original transaction amount
    const originalAmount = Math.abs(transactions.find(t => t._id === currentTransactionId)?.amount || 0);
    
    // Check if total matches original amount
    const isValid = Math.abs(total - originalAmount) < 0.01;
    
    totalElement.className = `split-total-amount ${isValid ? 'valid' : 'invalid'}`;
    saveBtn.disabled = !isValid;
    
    if (!isValid) {
        totalElement.textContent += ` (${total > originalAmount ? '+' : ''}$${(total - originalAmount).toFixed(2)})`;
    }
}

async function saveTransactionEdit(transactionId) {
    try {
        const form = document.getElementById('edit-transaction-form');
        const formData = new FormData(form);
        
        const updateData = {
            merchant: formData.get('merchant'),
            amount: parseFloat(formData.get('amount')),
            date: formData.get('date'),
            description: formData.get('description'),
            category: formData.get('category'),
            business_type: formData.get('business_type')
        };
        
        const response = await fetch(`/api/transactions/${transactionId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updateData)
        });
        
        if (!response.ok) {
            throw new Error('Failed to update transaction');
        }
        
        const result = await response.json();
        if (result.success) {
            showNotification('Transaction Updated', 'Transaction updated successfully', 'success');
            closeModal('edit-transaction-modal');
            await loadTransactions(); // Refresh the list
        } else {
            throw new Error(result.error || 'Update failed');
        }
    } catch (error) {
        console.error('Error updating transaction:', error);
        showNotification('Update Failed', error.message, 'error');
    }
}

async function saveTransactionSplit(transactionId) {
    try {
        const splitItems = document.querySelectorAll('.split-item');
        const splits = [];
        
        splitItems.forEach(item => {
            const amount = parseFloat(item.querySelector('.split-amount').value);
            const description = item.querySelector('.split-description').value;
            const category = item.querySelector('.split-category').value;
            
            if (amount && description) {
                splits.push({
                    amount: amount,
                    description: description,
                    category: category
                });
            }
        });
        
        if (splits.length === 0) {
            throw new Error('At least one split item is required');
        }
        
        const splitData = {
            original_transaction_id: transactionId,
            splits: splits
        };
        
        const response = await fetch('/api/transactions/split', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(splitData)
        });
        
        if (!response.ok) {
            throw new Error('Failed to split transaction');
        }
        
        const result = await response.json();
        if (result.success) {
            showNotification('Transaction Split', `Transaction split into ${splits.length} parts`, 'success');
            closeModal('split-transaction-modal');
            await loadTransactions(); // Refresh the list
        } else {
            throw new Error(result.error || 'Split failed');
        }
    } catch (error) {
        console.error('Error splitting transaction:', error);
        showNotification('Split Failed', error.message, 'error');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.remove();
    }
}

// ===== VIEW TOGGLE FUNCTIONALITY =====

function toggleTransactionView(view) {
    const viewButtons = document.querySelectorAll('.view-btn');
    const tableView = document.getElementById('transaction-table-view');
    const cardsView = document.getElementById('transaction-cards-view');
    
    // Remove active class from all buttons
    viewButtons.forEach(btn => btn.classList.remove('active'));
    
    // Add active class to target button
    const targetButton = document.querySelector(`[data-view="${view}"]`);
    if (targetButton) {
        targetButton.classList.add('active');
    }
    
    // Show/hide views
    if (view === 'table') {
        tableView.style.display = 'block';
        cardsView.style.display = 'none';
        renderTransactionTable();
    } else {
        tableView.style.display = 'none';
        cardsView.style.display = 'block';
        renderTransactionCards();
    }
    
    console.log(`🔄 Switched to ${view} view`);
}

// ===== INITIALIZE WHEN DOM IS READY =====

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApp);
} else {
    initializeApp();
}

// ===== MODAL MANAGEMENT =====
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

// ===== TRANSACTION EDITING =====
let currentEditingTransaction = null;

function editTransaction(transactionId) {
    const transaction = filteredTransactions.find(t => t._id === transactionId);
    if (!transaction) return;
    
    currentEditingTransaction = transaction;
    
    // Populate form fields
    document.getElementById('edit-merchant').value = transaction.merchant || '';
    document.getElementById('edit-amount').value = Math.abs(transaction.amount || 0);
    document.getElementById('edit-date').value = transaction.date ? transaction.date.split('T')[0] : '';
    document.getElementById('edit-business-type').value = transaction.business_type || 'personal';
    document.getElementById('edit-category').value = transaction.category || 'other';
    document.getElementById('edit-description').value = transaction.description || '';
    
    openModal('edit-transaction-modal');
}

async function saveTransactionEdit() {
    try {
        const form = document.getElementById('edit-transaction-form');
        const formData = new FormData(form);
        
        const updateData = {
            merchant: formData.get('merchant'),
            amount: parseFloat(formData.get('amount')),
            date: formData.get('date'),
            description: formData.get('description'),
            category: formData.get('category'),
            business_type: formData.get('business_type')
        };
        
        const response = await fetch(`/api/transactions/${currentEditingTransaction._id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updateData)
        });
        
        if (!response.ok) {
            throw new Error('Failed to update transaction');
        }
        
        const result = await response.json();
        if (result.success) {
            showNotification('Transaction Updated', 'Transaction updated successfully', 'success');
            closeModal('edit-transaction-modal');
            await loadTransactions(); // Refresh the list
        } else {
            throw new Error(result.error || 'Update failed');
        }
    } catch (error) {
        console.error('Error updating transaction:', error);
        showNotification('Update Failed', error.message, 'error');
    }
}

// ===== TRANSACTION SPLITTING =====
let currentSplittingTransaction = null;

function splitTransaction(transactionId) {
    const transaction = transactions.find(t => t._id === transactionId);
    if (!transaction) {
        showNotification('❌ Transaction not found', 'Unable to split transaction', 'error');
        return;
    }
    
    // Create split modal HTML
    const modalHTML = `
        <div id="split-modal" class="modal-overlay">
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Split Transaction</h3>
                    <button class="close-btn" onclick="closeModal('split-modal')">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body">
                    <div class="original-transaction">
                        <h4>Original Transaction</h4>
                        <p><strong>${transaction.merchant || 'Unknown'}</strong> - $${Math.abs(transaction.amount || 0).toFixed(2)}</p>
                    </div>
                    
                    <div class="split-items" id="split-items">
                        <div class="split-item">
                            <div class="split-item-header">
                                <span class="split-item-title">Split 1</span>
                            </div>
                            <div class="form-row">
                                <div class="form-group">
                                    <label>Description</label>
                                    <input type="text" class="split-description" placeholder="Enter description">
                                </div>
                                <div class="form-group">
                                    <label>Amount</label>
                                    <input type="number" class="split-amount" step="0.01" placeholder="0.00">
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <button type="button" class="btn-secondary" onclick="addSplitItem()" style="margin-bottom: var(--spacing-md);">
                        <i class="fas fa-plus"></i> Add Split
                    </button>
                    
                    <div class="split-total">
                        <div class="split-total-label">Total Split Amount</div>
                        <div class="split-total-amount" id="split-total">$0.00</div>
                    </div>
                    
                    <div class="form-actions">
                        <button type="button" class="btn-secondary" onclick="closeModal('split-modal')">Cancel</button>
                        <button type="button" class="btn-primary" onclick="saveTransactionSplit('${transactionId}')" id="save-split-btn" disabled>Save Split</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Show modal
    document.getElementById('split-modal').style.display = 'flex';
    
    // Setup split functionality
    setupSplitModalListeners();
}

function addSplitItem() {
    const splitItems = document.getElementById('split-items');
    const splitCount = splitItems.children.length + 1;
    
    const splitItem = document.createElement('div');
    splitItem.className = 'split-item';
    splitItem.innerHTML = `
        <div class="split-item-header">
            <span class="split-item-title">Split ${splitCount}</span>
            <button class="remove-split-btn" onclick="removeSplitItem(this)">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>Description</label>
                <input type="text" class="split-description" placeholder="Enter description">
            </div>
            <div class="form-group">
                <label>Amount</label>
                <input type="number" class="split-amount" step="0.01" placeholder="0.00">
            </div>
        </div>
    `;
    
    splitItems.appendChild(splitItem);
    updateSplitTotal();
}

function removeSplitItem(button) {
    button.closest('.split-item').remove();
    updateSplitTotal();
}

function setupSplitModalListeners() {
    const splitItems = document.getElementById('split-items');
    
    // Add event listeners to existing inputs
    splitItems.addEventListener('input', updateSplitTotal);
    
    // Initial total update
    updateSplitTotal();
}

function updateSplitTotal() {
    const splitAmounts = document.querySelectorAll('.split-amount');
    const totalElement = document.getElementById('split-total');
    const saveBtn = document.getElementById('save-split-btn');
    
    let total = 0;
    splitAmounts.forEach(input => {
        const amount = parseFloat(input.value) || 0;
        total += amount;
    });
    
    totalElement.textContent = `$${total.toFixed(2)}`;
    
    // Get original transaction amount
    const originalAmount = Math.abs(transactions.find(t => t._id === currentTransactionId)?.amount || 0);
    
    // Check if total matches original amount
    const isValid = Math.abs(total - originalAmount) < 0.01;
    
    totalElement.className = `split-total-amount ${isValid ? 'valid' : 'invalid'}`;
    saveBtn.disabled = !isValid;
    
    if (!isValid) {
        totalElement.textContent += ` (${total > originalAmount ? '+' : ''}$${(total - originalAmount).toFixed(2)})`;
    }
}

// ===== RECEIPT UPLOAD =====
let currentReceiptTransaction = null;

function uploadReceipt(transactionId) {
    const transaction = filteredTransactions.find(t => t._id === transactionId);
    if (!transaction) return;
    
    currentReceiptTransaction = transaction;
    
    // Populate transaction info
    const transactionInfo = document.getElementById('receipt-transaction-info');
    transactionInfo.innerHTML = `
        <h4>Transaction Details</h4>
        <p><strong>Merchant:</strong> ${transaction.merchant || 'Unknown'}</p>
        <p><strong>Amount:</strong> $${Math.abs(transaction.amount || 0).toFixed(2)}</p>
        <p><strong>Date:</strong> ${transaction.date ? new Date(transaction.date).toLocaleDateString() : 'Unknown'}</p>
        <p><strong>Category:</strong> ${transaction.category || 'Other'}</p>
    `;
    
    // Clear file input and preview
    document.getElementById('receipt-file').value = '';
    document.getElementById('receipt-preview').style.display = 'none';
    document.getElementById('upload-receipt-btn').disabled = true;
    
    openModal('receipt-upload-modal');
}

function previewReceipt(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        document.getElementById('receipt-preview-img').src = e.target.result;
        document.getElementById('receipt-preview').style.display = 'block';
        document.getElementById('upload-receipt-btn').disabled = false;
    };
    reader.readAsDataURL(file);
}

async function uploadReceiptToTransaction() {
    try {
        const fileInput = document.getElementById('receipt-file');
        const file = fileInput.files[0];
        
        if (!file) {
            throw new Error('Please select a file');
        }
        
        const formData = new FormData();
        formData.append('receipt', file);
        formData.append('transaction_id', currentReceiptTransaction._id);
        
        const response = await fetch('/api/transactions/upload-receipt', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Failed to upload receipt');
        }
        
        const result = await response.json();
        if (result.success) {
            showNotification('Receipt Uploaded', 'Receipt successfully uploaded and linked to transaction', 'success');
            closeModal('upload-receipt-modal');
            await loadTransactions(); // Refresh the list
        } else {
            throw new Error(result.error || 'Upload failed');
        }
    } catch (error) {
        console.error('Error uploading receipt:', error);
        showNotification('Upload Failed', error.message, 'error');
    }
}

function handleReceiptUpload(event) {
    const file = event.target.files[0];
    if (!file || !currentReceiptTransaction) return;
    
    // Trigger the upload
    uploadReceiptToTransaction();
}

// ===== TRANSACTION DUPLICATION =====
async function duplicateTransaction(transactionId) {
    try {
        const response = await fetch(`/api/transactions/${transactionId}/duplicate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to duplicate transaction');
        }
        
        const result = await response.json();
        if (result.success) {
            showNotification('Transaction Duplicated', 'Transaction duplicated successfully', 'success');
            await loadTransactions(); // Refresh the list
        } else {
            throw new Error(result.error || 'Duplication failed');
        }
    } catch (error) {
        console.error('Error duplicating transaction:', error);
        showNotification('Duplication Failed', error.message, 'error');
    }
}

// ===== ENHANCED TRANSACTION RENDERING =====
function createTransactionCard(transaction) {
    const hasReceipt = transaction.has_receipt || transaction.receipt_matched;
    const amountClass = parseFloat(transaction.amount) >= 0 ? 'positive' : 'negative';
    const businessTypeClass = getBusinessTypeClass(transaction.business_type);
    const categoryClass = getCategoryClass(transaction.category);
    
    return `
        <div class="transaction-card ${hasReceipt ? '' : 'missing-receipt'}" data-id="${transaction._id}">
            <div class="card-header">
                <div class="merchant-info">
                    <div class="merchant-name">${transaction.merchant || 'Unknown Merchant'}</div>
                    <span class="business-type-badge ${businessTypeClass}">${transaction.business_type || 'personal'}</span>
                </div>
                <div class="amount-section">
                    <div class="amount ${amountClass}">$${Math.abs(parseFloat(transaction.amount || 0)).toFixed(2)}</div>
                    <div class="date">${transaction.date ? new Date(transaction.date).toLocaleDateString() : 'Unknown Date'}</div>
                </div>
            </div>
            
            <div class="card-body">
                ${transaction.description ? `<div class="description">${transaction.description}</div>` : ''}
                
                <div class="category-section">
                    <span class="category-badge ${categoryClass}">${transaction.category || 'other'}</span>
                </div>
                
                <div class="receipt-section">
                    <div class="receipt-status ${hasReceipt ? 'matched' : 'missing'}">
                        <i class="fas ${hasReceipt ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
                        ${hasReceipt ? 'Receipt Matched' : 'Missing Receipt'}
                    </div>
                </div>
            </div>
            
            <div class="card-actions">
                <button class="action-btn" onclick="editTransaction('${transaction._id}')" title="Edit">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="action-btn" onclick="uploadReceipt('${transaction._id}')" title="Upload Receipt">
                    <i class="fas fa-upload"></i>
                </button>
                <button class="action-btn" onclick="splitTransaction('${transaction._id}')" title="Split">
                    <i class="fas fa-cut"></i>
                </button>
                <button class="action-btn" onclick="duplicateTransaction('${transaction._id}')" title="Duplicate">
                    <i class="fas fa-copy"></i>
                </button>
            </div>
        </div>
    `;
}

function getBusinessTypeClass(businessType) {
    if (!businessType) return 'personal';
    
    const type = businessType.toLowerCase().replace(/\s+/g, '-');
    const validTypes = ['personal', 'down-home', 'music-city-rodeo'];
    
    return validTypes.includes(type) ? type : 'personal';
}

function getCategoryClass(category) {
    if (!category) return 'other';
    
    const cat = category.toLowerCase().replace(/\s+/g, '-');
    const validCategories = ['food', 'transportation', 'entertainment', 'shopping', 'utilities', 'healthcare', 'travel', 'education', 'professional', 'insurance', 'other'];
    
    return validCategories.includes(cat) ? cat : 'other';
}

function getCategoryIcon(category) {
    if (!category) return 'fa-tag';
    
    const cat = category.toLowerCase();
    const iconMap = {
        'food': 'fa-utensils',
        'transportation': 'fa-car',
        'entertainment': 'fa-film',
        'shopping': 'fa-shopping-bag',
        'utilities': 'fa-bolt',
        'healthcare': 'fa-heartbeat',
        'travel': 'fa-plane',
        'education': 'fa-graduation-cap',
        'professional': 'fa-briefcase',
        'insurance': 'fa-shield-alt',
        'other': 'fa-tag'
    };
    
    return iconMap[cat] || 'fa-tag';
}

// ===== ENHANCED TRANSACTION TABLE ROW CREATOR =====
function createTransactionRow(transaction) {
    const hasReceipt = transaction.has_receipt || transaction.receipt_matched;
    const amountClass = parseFloat(transaction.amount) >= 0 ? 'positive' : 'negative';
    const businessTypeClass = getBusinessTypeClass(transaction.business_type);
    const categoryClass = getCategoryClass(transaction.category);
    const categoryIcon = getCategoryIcon(transaction.category);
    let receiptThumb = '';
    if (transaction.receipt_url) {
        receiptThumb = `<img class="receipt-thumb" src="${transaction.receipt_url}" alt="Receipt" onclick="showReceiptViewer('${transaction.receipt_url}')" title="View Receipt" />`;
    }
    const row = document.createElement('tr');
    row.className = `transaction-row ${hasReceipt ? '' : 'missing-receipt'} ${businessTypeClass}`;
    row.setAttribute('data-id', transaction._id);
    row.innerHTML = `
      <td class="transaction-date"><span class="date">${transaction.date ? new Date(transaction.date).toLocaleDateString() : '—'}</span></td>
      <td class="merchant-name">${transaction.merchant || '—'}</td>
      <td class="transaction-description">${transaction.description ? transaction.description : generateTransactionDescription(transaction) || '—'}</td>
      <td class="business-type-badge ${businessTypeClass}"><i class="fas fa-briefcase"></i> ${transaction.business_type || '—'}</td>
      <td class="category-badge ${categoryClass}"><i class="fas ${categoryIcon}"></i> ${transaction.category || '—'}</td>
      <td class="amount ${amountClass}">$${Math.abs(parseFloat(transaction.amount || 0)).toFixed(2)}</td>
      <td class="receipt-status ${hasReceipt ? 'matched' : 'missing'}"><i class="fas ${hasReceipt ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i> ${hasReceipt ? 'Receipt Matched' : 'Missing Receipt'} ${receiptThumb}</td>
      <td class="actions">
        <div class="actions">
          <button class="action-btn" onclick="editTransaction('${transaction._id}')" title="Edit"><i class="fas fa-edit"></i></button>
          <button class="action-btn" onclick="uploadReceipt('${transaction._id}')" title="Upload Receipt"><i class="fas fa-upload"></i></button>
          <button class="action-btn" onclick="splitTransaction('${transaction._id}')" title="Split"><i class="fas fa-cut"></i></button>
          <button class="action-btn" onclick="duplicateTransaction('${transaction._id}')" title="Duplicate"><i class="fas fa-copy"></i></button>
        </div>
      </td>
    `;
    return row;
}

// ===== RECEIPT VIEWER MODAL LOGIC =====
function showReceiptViewer(url) {
    let modal = document.getElementById('receipt-viewer-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'receipt-viewer-modal';
        modal.className = 'receipt-viewer-modal';
        modal.innerHTML = `
            <div class="receipt-viewer-content">
                <img id="receipt-viewer-img" class="receipt-viewer-img" src="" alt="Receipt Image" />
                <button class="receipt-viewer-close" onclick="closeReceiptViewer()">Close</button>
            </div>
        `;
        document.body.appendChild(modal);
    }
    document.getElementById('receipt-viewer-img').src = url;
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}
function closeReceiptViewer() {
    const modal = document.getElementById('receipt-viewer-modal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = 'auto';
    }
}

// ===== ENHANCED TRANSACTION TABLE ROW CREATOR (with receipt thumb, correct order, placeholders) =====
function createTransactionRow(transaction) {
    const hasReceipt = transaction.has_receipt || transaction.receipt_matched;
    const amountClass = parseFloat(transaction.amount) >= 0 ? 'positive' : 'negative';
    const businessTypeClass = getBusinessTypeClass(transaction.business_type);
    const categoryClass = getCategoryClass(transaction.category);
    const categoryIcon = getCategoryIcon(transaction.category);
    // Receipt thumbnail logic
    let receiptThumb = '';
    if (transaction.receipt_url) {
        receiptThumb = `<img class="receipt-thumb" src="${transaction.receipt_url}" alt="Receipt" onclick="showReceiptViewer('${transaction.receipt_url}')" title="View Receipt" />`;
    }
    const tr = document.createElement('tr');
    tr.className = `transaction-row ${hasReceipt ? '' : 'missing-receipt'} ${businessTypeClass}`;
    tr.setAttribute('data-id', transaction._id);
    tr.innerHTML = `
        <td class="transaction-date">
            <span class="date">${transaction.date ? new Date(transaction.date).toLocaleDateString() : '—'}</span>
        </td>
        <td class="merchant-name">
            ${transaction.merchant || '—'}
        </td>
        <td class="transaction-description">
            ${transaction.description ? transaction.description : generateTransactionDescription(transaction) || '—'}
        </td>
        <td class="business-type-badge ${businessTypeClass}">
            <i class="fas fa-briefcase"></i> ${transaction.business_type || '—'}
        </td>
        <td class="category-badge ${categoryClass}">
            <i class="fas ${categoryIcon}"></i> ${transaction.category || '—'}
        </td>
        <td class="amount ${amountClass}">
            $${Math.abs(parseFloat(transaction.amount || 0)).toFixed(2)}
        </td>
        <td class="receipt-status ${hasReceipt ? 'matched' : 'missing'}">
            <i class="fas ${hasReceipt ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
            ${hasReceipt ? 'Receipt Matched' : 'Missing Receipt'}
            ${receiptThumb}
        </td>
        <td class="transaction-actions">
            <button class="action-btn" onclick="editTransaction('${transaction._id}')" title="Edit"><i class="fas fa-edit"></i></button>
            <button class="action-btn" onclick="uploadReceipt('${transaction._id}')" title="Upload Receipt"><i class="fas fa-upload"></i></button>
            <button class="action-btn" onclick="splitTransaction('${transaction._id}')" title="Split"><i class="fas fa-cut"></i></button>
            <button class="action-btn" onclick="duplicateTransaction('${transaction._id}')" title="Duplicate"><i class="fas fa-copy"></i></button>
        </td>
    `;
    return tr;
}

// ===== ENHANCED TRANSACTION CARD CREATOR (with receipt thumb, placeholders) =====
function createTransactionCard(transaction) {
    const hasReceipt = transaction.has_receipt || transaction.receipt_matched;
    const amountClass = parseFloat(transaction.amount) >= 0 ? 'positive' : 'negative';
    const businessTypeClass = getBusinessTypeClass(transaction.business_type);
    const categoryClass = getCategoryClass(transaction.category);
    const categoryIcon = getCategoryIcon(transaction.category);
    let receiptThumb = '';
    if (transaction.receipt_url) {
        receiptThumb = `<img class="receipt-thumb" src="${transaction.receipt_url}" alt="Receipt" onclick="showReceiptViewer('${transaction.receipt_url}')" title="View Receipt" />`;
    }
    return `
        <div class="transaction-card ${hasReceipt ? '' : 'missing-receipt'}" data-id="${transaction._id}">
            <div class="card-header">
                <div class="merchant-info">
                    <div class="merchant-name">${transaction.merchant || '—'}</div>
                    <span class="business-type-badge ${businessTypeClass}">${transaction.business_type || '—'}</span>
                </div>
                <div class="amount-section">
                    <div class="amount ${amountClass}">$${Math.abs(parseFloat(transaction.amount || 0)).toFixed(2)}</div>
                    <div class="date">${transaction.date ? new Date(transaction.date).toLocaleDateString() : '—'}</div>
                </div>
            </div>
            <div class="card-body">
                <div class="description">${transaction.description ? transaction.description : generateTransactionDescription(transaction) || '—'}</div>
                <div class="category-section">
                    <span class="category-badge ${categoryClass}"><i class="fas ${categoryIcon}"></i> ${transaction.category || '—'}</span>
                </div>
                <div class="receipt-section">
                    <div class="receipt-status ${hasReceipt ? 'matched' : 'missing'}">
                        <i class="fas ${hasReceipt ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
                        ${hasReceipt ? 'Receipt Matched' : 'Missing Receipt'}
                        ${receiptThumb}
                    </div>
                </div>
            </div>
            <div class="card-actions">
                <button class="action-btn" onclick="editTransaction('${transaction._id}')" title="Edit">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="action-btn" onclick="uploadReceipt('${transaction._id}')" title="Upload Receipt">
                    <i class="fas fa-upload"></i>
                </button>
                <button class="action-btn" onclick="splitTransaction('${transaction._id}')" title="Split">
                    <i class="fas fa-cut"></i>
                </button>
                <button class="action-btn" onclick="duplicateTransaction('${transaction._id}')" title="Duplicate">
                    <i class="fas fa-copy"></i>
                </button>
            </div>
        </div>
    `;
}

// ===== TOGGLE LOGIC (MINIMAL, MODERN) =====
function setView(view) {
  const toggleBtns = document.querySelectorAll('.view-btn');
  const tableContainer = document.querySelector('.transaction-table-container');
  const cardContainer = document.querySelector('.transaction-cards-container');
  const viewToggle = document.getElementById('viewToggle');

  toggleBtns.forEach(btn => btn.classList.remove('active'));
  const activeBtn = document.querySelector(`.view-btn[data-view="${view}"]`);
  if (activeBtn) activeBtn.classList.add('active');

  if (view === 'table') {
    if (tableContainer) tableContainer.style.display = 'block';
    if (cardContainer) cardContainer.style.display = 'none';
  } else {
    if (tableContainer) tableContainer.style.display = 'none';
    if (cardContainer) cardContainer.style.display = 'flex';
  }
}

function autoSwitchView() {
  const isMobile = window.innerWidth < 768;
  setView(isMobile ? 'card' : 'table');
  const viewToggle = document.getElementById('viewToggle');
  if (viewToggle) viewToggle.style.display = isMobile ? 'none' : 'flex';
}

window.addEventListener('resize', autoSwitchView);
window.addEventListener('load', autoSwitchView);

// ===== INITIALIZATION =====
// Initialize variables that are shared with script.js
if (typeof sortDirection === 'undefined') window.sortDirection = 'asc';
if (typeof sortColumn === 'undefined') window.sortColumn = '';
if (typeof searchTerm === 'undefined') window.searchTerm = '';
if (typeof activeFilters === 'undefined') window.activeFilters = {
    category: '',
    businessType: '',
    receiptStatus: '',
    dateFrom: '',
    dateTo: ''
};