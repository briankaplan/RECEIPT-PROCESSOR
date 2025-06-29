// TallyUps - Ultimate Financial Intelligence PWA
// Complete Transaction System with Inline Editing, Receipts, and Real Data

console.log('🚀 Script.js loaded and executing...');

// Authentication check
function checkAuthentication() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        console.log('🔒 No authentication token found, redirecting to login...');
        window.location.href = '/login';
        return false;
    }
    
    // Optional: Validate token format (basic check)
    try {
        const tokenParts = token.split('.');
        if (tokenParts.length !== 3) {
            console.log('🔒 Invalid token format, redirecting to login...');
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('user');
            window.location.href = '/login';
            return false;
        }
    } catch (error) {
        console.log('🔒 Token validation error, redirecting to login...');
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = '/login';
        return false;
    }
    
    return true;
}

// Global variables
let app;
let transactions = [];
let filteredTransactions = [];
let currentView = 'table';
let currentSort = { field: 'date', direction: 'desc' };
let currentPage = 1;
let pageSize = 50;
let totalTransactions = 0; // Add total count for proper pagination
let editingTransaction = null;

// TallyUps global object for camera and other features
window.TallyUps = {
    camera: {
        toggle: function() {
            console.log('📷 Camera toggle called');
            showToast('Camera feature coming soon!', 'info');
        }
    },
    logout: function() {
        console.log('🚪 Logging out...');
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = '/login';
    }
};

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Initializing TallyUps...');
    
    // Check authentication first
    if (!checkAuthentication()) {
        return;
    }
    
    initializeApp();
});

function initializeApp() {
    console.log('🎯 Setting up TallyUps Dashboard...');
    
    // Initialize transaction system
    initializeTransactionSystem();
    
    // Setup other dashboard functionality
    setupDashboard();
    
    console.log('✅ TallyUps initialized successfully');
}

function initializeTransactionSystem() {
    console.log('📊 Initializing Transaction System...');
    
    // Load transactions
    loadTransactions();
    
    // Setup view toggle buttons
    setupViewToggle();
    
    // Setup search and filters
    setupFilters();
    
    // Setup sorting
    setupSorting();
    
    // Setup responsive detection
    setupResponsive();
}

async function loadTransactions(page = 1) {
    try {
        console.log(`📊 Loading transactions from API (page ${page}, size ${pageSize})...`);
        
        const response = await fetch(`/transactions?page=${page}&page_size=${pageSize}&date_from=2024-07-01&date_to=2025-06-28`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('📊 API Response:', data);
        
        if (data.success && data.transactions) {
            transactions = data.transactions;
            filteredTransactions = [...transactions];
            totalTransactions = data.total || data.transactions.length; // Get total from API
            currentPage = page;
            
            console.log(`✅ Loaded ${transactions.length} transactions (page ${page} of ${Math.ceil(totalTransactions / pageSize)})`);
            console.log('🔍 Sample transaction:', transactions[0]);
            
            // Apply current sort
            applySorting();
            
            // Render transactions
            console.log('🎨 About to render transactions...');
            renderTransactions();
            updateStats();
            updatePagination();
            
            console.log('🎨 Rendering complete');
        } else {
            console.error('❌ No transaction data in response');
            showError('No transaction data available');
        }
    } catch (error) {
        console.error('❌ Error loading transactions:', error);
        showError('Failed to load transactions: ' + error.message);
    }
}

function setupViewToggle() {
    const viewButtons = document.querySelectorAll('.view-btn');
    
    viewButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const view = btn.dataset.view;
            switchView(view);
            
            // Update active button
            viewButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });
    
    // Set initial view from localStorage
    const savedView = localStorage.getItem('transaction-view') || 'table';
    switchView(savedView);
}

function switchView(view) {
    console.log(`🔄 Switching to ${view} view`);
    
    const container = document.getElementById('transaction-container');
    if (container) {
        container.className = `transaction-container ${view}-view`;
    }
    
    currentView = view;
    localStorage.setItem('transaction-view', view);
    
    // Update active button
    const viewButtons = document.querySelectorAll('.view-btn');
    viewButtons.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.view === view);
    });
    
    // Re-render for the new view
    renderTransactions();
}

function setupFilters() {
    // Search input
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(applyFilters, 300));
    }
    
    // Filter dropdowns
    const businessFilter = document.getElementById('business-filter');
    const categoryFilter = document.getElementById('category-filter');
    const receiptFilter = document.getElementById('receipt-filter');
    const sortFilter = document.getElementById('sort-filter');
    
    if (businessFilter) businessFilter.addEventListener('change', applyFilters);
    if (categoryFilter) categoryFilter.addEventListener('change', applyFilters);
    if (receiptFilter) receiptFilter.addEventListener('change', applyFilters);
    if (sortFilter) sortFilter.addEventListener('change', applySorting);
}

function setupSorting() {
    // Add click handlers to sortable headers
    const sortableHeaders = document.querySelectorAll('.sortable');
    sortableHeaders.forEach(header => {
        header.addEventListener('click', () => {
            const field = header.getAttribute('data-field') || header.textContent.trim().toLowerCase().replace(/\s+/g, '_');
            sortBy(field);
        });
    });
}

function applyFilters() {
    const searchTerm = document.getElementById('search-input')?.value.toLowerCase() || '';
    const businessFilter = document.getElementById('business-filter')?.value || '';
    const categoryFilter = document.getElementById('category-filter')?.value || '';
    const receiptFilter = document.getElementById('receipt-filter')?.value || '';
    
    filteredTransactions = transactions.filter(tx => {
        // Search filter
        if (searchTerm) {
            const searchText = [
                tx.merchant || '',
                tx.description || '',
                tx.category || '',
                tx.business_type || ''
            ].join(' ').toLowerCase();
            
            if (!searchText.includes(searchTerm)) {
                return false;
            }
        }
        
        // Business type filter
        if (businessFilter && tx.business_type !== businessFilter) {
            return false;
        }
        
        // Category filter
        if (categoryFilter && tx.category !== categoryFilter) {
            return false;
        }
        
        // Receipt status filter
        if (receiptFilter) {
            const hasReceipt = tx.has_receipt || tx.receipt_url;
            if (receiptFilter === 'matched' && !hasReceipt) {
                return false;
            }
            if (receiptFilter === 'missing' && hasReceipt) {
                return false;
            }
        }
        
        return true;
    });
    
    // Apply current sorting
    applySorting();
    
    // Reset to first page
    currentPage = 1;
    
    renderTransactions();
    updateStats();
    updatePagination();
}

function applySorting() {
    const sortFilter = document.getElementById('sort-filter');
    if (sortFilter && sortFilter.value) {
        const [field, direction] = sortFilter.value.split('-');
        currentSort = { field, direction };
    }
    
    filteredTransactions.sort((a, b) => {
        let aVal, bVal;
        
        switch (currentSort.field) {
            case 'date':
                aVal = new Date(a.date || a.created_at);
                bVal = new Date(b.date || b.created_at);
                break;
            case 'amount':
                aVal = Math.abs(parseFloat(a.amount || 0));
                bVal = Math.abs(parseFloat(b.amount || 0));
                break;
            case 'merchant':
                aVal = (a.merchant || '').toLowerCase();
                bVal = (b.merchant || '').toLowerCase();
                break;
            case 'business_type':
                aVal = (a.business_type || '').toLowerCase();
                bVal = (b.business_type || '').toLowerCase();
                break;
            case 'category':
                aVal = (a.category || '').toLowerCase();
                bVal = (b.category || '').toLowerCase();
                break;
            default:
                aVal = a[currentSort.field] || '';
                bVal = b[currentSort.field] || '';
        }
        
        if (currentSort.direction === 'asc') {
            return aVal > bVal ? 1 : -1;
        } else {
            return aVal < bVal ? 1 : -1;
        }
    });
}

function sortBy(field) {
    // Toggle direction if same field
    if (currentSort.field === field) {
        currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        currentSort.field = field;
        currentSort.direction = 'desc';
    }
    
    // Update sort filter
    const sortFilter = document.getElementById('sort-filter');
    if (sortFilter) {
        sortFilter.value = `${field}-${currentSort.direction}`;
    }
    
    applySorting();
    renderTransactions();
}

function clearFilters() {
    const searchInput = document.getElementById('search-input');
    const businessFilter = document.getElementById('business-filter');
    const categoryFilter = document.getElementById('category-filter');
    const receiptFilter = document.getElementById('receipt-filter');
    const sortFilter = document.getElementById('sort-filter');
    
    if (searchInput) searchInput.value = '';
    if (businessFilter) businessFilter.value = '';
    if (categoryFilter) categoryFilter.value = '';
    if (receiptFilter) receiptFilter.value = '';
    if (sortFilter) sortFilter.value = 'date-desc';
    
    currentSort = { field: 'date', direction: 'desc' };
    filteredTransactions = [...transactions];
    currentPage = 1;
    
    applySorting();
    renderTransactions();
    updateStats();
    updatePagination();
}

function renderTransactions() {
    console.log('🎨 Rendering transactions...');
    console.log('📊 Current view:', currentView);
    console.log('📊 Filtered transactions:', filteredTransactions.length);
    
    if (currentView === 'table') {
        console.log('📋 Rendering table view...');
        renderTableView();
    } else {
        console.log('🃏 Rendering cards view...');
        renderCardsView();
    }
}

function renderTableView() {
    const tbody = document.getElementById('transaction-tbody');
    console.log('🔍 Table body element:', tbody);
    
    if (!tbody) {
        console.error('❌ Table body element not found');
        return;
    }
    
    tbody.innerHTML = '';
    
    if (filteredTransactions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="no-transactions">
                    <div class="empty-state">
                        <i class="fas fa-inbox"></i>
                        <p>No transactions found</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    console.log('📝 Rendering', filteredTransactions.length, 'transactions');
    
    filteredTransactions.forEach((tx, index) => {
        const row = document.createElement('tr');
        row.className = 'transaction-row';
        row.setAttribute('data-transaction-id', tx._id || tx.id);
        
        const date = new Date(tx.date || tx.created_at);
        const formattedDate = date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric', 
            year: 'numeric' 
        });
        
        const amount = Math.abs(parseFloat(tx.amount || 0));
        const isNegative = parseFloat(tx.amount || 0) < 0;
        
        row.innerHTML = `
            <td class="date-cell">
                <span class="date-display">${formattedDate}</span>
                <input type="date" class="date-edit" value="${date.toISOString().split('T')[0]}" style="display: none;">
            </td>
            <td class="merchant-cell">
                <span class="merchant-display">${tx.merchant || 'Unknown Merchant'}</span>
                <input type="text" class="merchant-edit" value="${tx.merchant || ''}" style="display: none;">
            </td>
            <td class="description-cell">
                <span class="description-display">${tx.description || tx.merchant || 'No description'}</span>
                <textarea class="description-edit" style="display: none;">${tx.description || ''}</textarea>
            </td>
            <td class="business-cell">
                <span class="business-display">${renderBusinessBadge(tx.business_type)}</span>
                <select class="business-edit" style="display: none;">
                    <option value="personal" ${tx.business_type === 'personal' ? 'selected' : ''}>Personal</option>
                    <option value="down-home" ${tx.business_type === 'down-home' ? 'selected' : ''}>Down Home</option>
                    <option value="music-city" ${tx.business_type === 'music-city' ? 'selected' : ''}>Music City</option>
                </select>
            </td>
            <td class="category-cell">
                <span class="category-display">${renderCategoryBadge(tx.category)}</span>
                <select class="category-edit" style="display: none;">
                    <option value="food" ${tx.category === 'food' ? 'selected' : ''}>Food & Dining</option>
                    <option value="transport" ${tx.category === 'transport' ? 'selected' : ''}>Transportation</option>
                    <option value="shopping" ${tx.category === 'shopping' ? 'selected' : ''}>Shopping</option>
                    <option value="travel" ${tx.category === 'travel' ? 'selected' : ''}>Travel</option>
                    <option value="entertainment" ${tx.category === 'entertainment' ? 'selected' : ''}>Entertainment</option>
                    <option value="business" ${tx.category === 'business' ? 'selected' : ''}>Business</option>
                </select>
            </td>
            <td class="amount-cell">
                <span class="amount-display amount ${isNegative ? 'amount-negative' : 'amount-positive'}">
                    $${amount.toFixed(2)}
                </span>
                <input type="number" class="amount-edit" value="${tx.amount || 0}" step="0.01" style="display: none;">
            </td>
            <td class="receipt-cell">
                ${renderReceiptCell(tx)}
            </td>
            <td class="actions-cell">
                <div class="action-buttons">
                    <button class="action-btn edit-btn" onclick="toggleEdit('${tx._id || tx.id}')" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="action-btn save-btn" onclick="saveTransaction('${tx._id || tx.id}')" title="Save" style="display: none;">
                        <i class="fas fa-save"></i>
                    </button>
                    <button class="action-btn cancel-btn" onclick="cancelEdit('${tx._id || tx.id}')" title="Cancel" style="display: none;">
                        <i class="fas fa-times"></i>
                    </button>
                    <button class="action-btn upload-btn" onclick="uploadReceipt('${tx._id || tx.id}')" title="Upload Receipt">
                        <i class="fas fa-upload"></i>
                    </button>
                    <button class="action-btn split-btn" onclick="splitTransaction('${tx._id || tx.id}')" title="Split">
                        <i class="fas fa-cut"></i>
                    </button>
                </div>
            </td>
        `;
        
        tbody.appendChild(row);
        console.log(`✅ Rendered transaction ${index + 1}:`, tx.merchant);
    });
}

function renderCardsView() {
    const container = document.getElementById('transaction-cards');
    console.log('🔍 Cards container element:', container);
    
    if (!container) {
        console.error('❌ Cards container element not found');
        return;
    }
    
    container.innerHTML = '';
    
    if (filteredTransactions.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-inbox"></i>
                <p>No transactions found</p>
            </div>
        `;
        return;
    }
    
    filteredTransactions.forEach((tx, index) => {
        const card = document.createElement('div');
        card.className = 'transaction-card';
        card.setAttribute('data-transaction-id', tx._id || tx.id);
        
        const date = new Date(tx.date || tx.created_at);
        const formattedDate = date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric', 
            year: 'numeric' 
        });
        
        const amount = Math.abs(parseFloat(tx.amount || 0));
        const isNegative = parseFloat(tx.amount || 0) < 0;
        
        card.innerHTML = `
            <div class="card-header">
                <div class="card-merchant">
                    <div class="merchant-name">${tx.merchant || 'Unknown Merchant'}</div>
                    <div class="card-date">${formattedDate}</div>
                </div>
                <div class="card-amount">
                    <div class="amount-value ${isNegative ? 'amount-negative' : 'amount-positive'}">
                        $${amount.toFixed(2)}
                    </div>
                </div>
            </div>
            <div class="card-body">
                <div class="card-description">
                    ${tx.description || tx.merchant || 'No description available'}
                </div>
                <div class="card-meta">
                    ${renderBusinessBadge(tx.business_type)}
                    ${renderCategoryBadge(tx.category)}
                </div>
                <div class="card-receipt">
                    ${renderReceiptCell(tx)}
                </div>
            </div>
            <div class="card-footer">
                <div class="card-actions">
                    <button class="action-btn edit-btn" onclick="toggleEdit('${tx._id || tx.id}')" title="Edit">
                        <i class="fas fa-edit"></i> Edit
                    </button>
                    <button class="action-btn upload-btn" onclick="uploadReceipt('${tx._id || tx.id}')" title="Upload Receipt">
                        <i class="fas fa-upload"></i> Receipt
                    </button>
                    <button class="action-btn split-btn" onclick="splitTransaction('${tx._id || tx.id}')" title="Split">
                        <i class="fas fa-cut"></i> Split
                    </button>
                </div>
            </div>
        `;
        
        container.appendChild(card);
        console.log(`✅ Rendered card ${index + 1}:`, tx.merchant);
    });
}

function renderReceiptCell(tx) {
    if (tx.has_receipt || tx.receipt_url) {
        return `
            <div class="receipt-cell-content">
                <div class="receipt-thumbnail" onclick="viewReceipt('${tx._id || tx.id}')">
                    <img src="${tx.receipt_url || '/static/images/receipt-placeholder.png'}" alt="Receipt" onerror="this.src='/static/images/receipt-placeholder.png'">
                </div>
                <span class="receipt-status receipt-matched">
                    <i class="fas fa-check-circle"></i> Matched
                </span>
            </div>
        `;
    } else {
        return `
            <div class="receipt-cell-content">
                <div class="receipt-thumbnail missing" onclick="uploadReceipt('${tx._id || tx.id}')">
                    <i class="fas fa-plus"></i>
                </div>
                <span class="receipt-status receipt-missing">
                    <i class="fas fa-exclamation-triangle"></i> Missing
                </span>
            </div>
        `;
    }
}

function renderBusinessBadge(businessType) {
    const badges = {
        'personal': '<span class="badge badge-personal"><i class="fas fa-user"></i> Personal</span>',
        'down-home': '<span class="badge badge-down-home"><i class="fas fa-home"></i> Down Home</span>',
        'music-city': '<span class="badge badge-music-city"><i class="fas fa-horse"></i> Music City</span>'
    };
    return badges[businessType] || '<span class="badge badge-personal"><i class="fas fa-user"></i> Personal</span>';
}

function renderCategoryBadge(category) {
    const badges = {
        'food': '<span class="badge badge-category"><i class="fas fa-coffee"></i> Food</span>',
        'shopping': '<span class="badge badge-category"><i class="fas fa-shopping-cart"></i> Shopping</span>',
        'transport': '<span class="badge badge-category"><i class="fas fa-car"></i> Transport</span>',
        'entertainment': '<span class="badge badge-category"><i class="fas fa-film"></i> Entertainment</span>',
        'travel': '<span class="badge badge-category"><i class="fas fa-plane"></i> Travel</span>',
        'business': '<span class="badge badge-category"><i class="fas fa-briefcase"></i> Business</span>'
    };
    return badges[category] || '<span class="badge badge-category"><i class="fas fa-tag"></i> Other</span>';
}

function toggleEdit(transactionId) {
    const row = document.querySelector(`[data-transaction-id="${transactionId}"]`);
    if (!row) return;
    
    const isEditing = row.classList.contains('editing');
    
    if (isEditing) {
        // Cancel editing
        cancelEdit(transactionId);
    } else {
        // Start editing
        row.classList.add('editing');
        
        // Hide display elements, show edit elements
        row.querySelectorAll('.date-display, .merchant-display, .description-display, .business-display, .category-display, .amount-display').forEach(el => {
            el.style.display = 'none';
        });
        
        row.querySelectorAll('.date-edit, .merchant-edit, .description-edit, .business-edit, .category-edit, .amount-edit').forEach(el => {
            el.style.display = 'block';
        });
        
        // Show save/cancel buttons, hide edit button
        row.querySelector('.edit-btn').style.display = 'none';
        row.querySelector('.save-btn').style.display = 'inline-block';
        row.querySelector('.cancel-btn').style.display = 'inline-block';
        
        editingTransaction = transactionId;
    }
}

async function saveTransaction(transactionId) {
    const row = document.querySelector(`[data-transaction-id="${transactionId}"]`);
    if (!row) return;
    
    // Get edited values
    const editedData = {
        date: row.querySelector('.date-edit').value,
        merchant: row.querySelector('.merchant-edit').value,
        description: row.querySelector('.description-edit').value,
        business_type: row.querySelector('.business-edit').value,
        category: row.querySelector('.category-edit').value,
        amount: parseFloat(row.querySelector('.amount-edit').value)
    };
    
    try {
        const response = await fetch(`/api/transactions/${transactionId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(editedData)
        });
        
        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                // Update local data
                const transaction = transactions.find(t => (t._id || t.id) === transactionId);
                if (transaction) {
                    Object.assign(transaction, editedData);
                }
                
                // Exit edit mode
                cancelEdit(transactionId);
                
                // Re-render to show updated data
                renderTransactions();
                
                // Refresh dashboard stats to reflect changes
                loadDashboardStats();
                
                showToast('Transaction updated successfully', 'success');
            } else {
                showError('Failed to update transaction: ' + result.error);
            }
        } else {
            showError('Failed to update transaction');
        }
    } catch (error) {
        console.error('Error updating transaction:', error);
        showError('Failed to update transaction: ' + error.message);
    }
}

function cancelEdit(transactionId) {
    const row = document.querySelector(`[data-transaction-id="${transactionId}"]`);
    if (!row) return;
    
    row.classList.remove('editing');
    
    // Show display elements, hide edit elements
    row.querySelectorAll('.date-display, .merchant-display, .description-display, .business-display, .category-display, .amount-display').forEach(el => {
        el.style.display = 'inline';
    });
    
    row.querySelectorAll('.date-edit, .merchant-edit, .description-edit, .business-edit, .category-edit, .amount-edit').forEach(el => {
        el.style.display = 'none';
    });
    
    // Show edit button, hide save/cancel buttons
    row.querySelector('.edit-btn').style.display = 'inline-block';
    row.querySelector('.save-btn').style.display = 'none';
    row.querySelector('.cancel-btn').style.display = 'none';
    
    editingTransaction = null;
}

function viewReceipt(transactionId) {
    // Open receipt viewer modal
    const transaction = transactions.find(t => (t._id || t.id) === transactionId);
    if (transaction && (transaction.has_receipt || transaction.receipt_url)) {
        // Create receipt viewer modal
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content receipt-viewer">
                <div class="modal-header">
                    <h3>Receipt - ${transaction.merchant}</h3>
                    <button class="close-btn" onclick="this.closest('.modal-overlay').remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body">
                    <img src="${transaction.receipt_url}" alt="Receipt" style="max-width: 100%; height: auto;">
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
}

function uploadReceipt(transactionId) {
    // Create file input and trigger upload
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = async (event) => {
        const file = event.target.files[0];
        if (file) {
            await uploadReceiptToTransaction(transactionId, file);
        }
    };
    input.click();
}

async function uploadReceiptToTransaction(transactionId, file) {
    try {
        const formData = new FormData();
        formData.append('receipt', file);
        formData.append('transaction_id', transactionId);
        
        const response = await fetch('/api/transactions/upload-receipt', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                // Reload transactions to get updated receipt data
                await loadTransactions();
                
                // Refresh dashboard stats to reflect changes
                loadDashboardStats();
                
                showToast('Receipt uploaded successfully', 'success');
            } else {
                showError('Failed to upload receipt: ' + result.error);
            }
        } else {
            showError('Failed to upload receipt');
        }
    } catch (error) {
        console.error('Error uploading receipt:', error);
        showError('Failed to upload receipt: ' + error.message);
    }
}

function splitTransaction(transactionId) {
    // Open split transaction modal
    const transaction = transactions.find(t => (t._id || t.id) === transactionId);
    if (transaction) {
        // Create split modal
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Split Transaction - ${transaction.merchant}</h3>
                    <button class="close-btn" onclick="this.closest('.modal-overlay').remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body">
                    <p>Original Amount: $${Math.abs(parseFloat(transaction.amount || 0)).toFixed(2)}</p>
                    <div class="split-form">
                        <div class="split-part">
                            <label>Part 1 Amount:</label>
                            <input type="number" id="split1-amount" step="0.01">
                            <label>Category:</label>
                            <select id="split1-category">
                                <option value="food">Food & Dining</option>
                                <option value="shopping">Shopping</option>
                                <option value="transport">Transportation</option>
                                <option value="entertainment">Entertainment</option>
                                <option value="business">Business</option>
                            </select>
                        </div>
                        <div class="split-part">
                            <label>Part 2 Amount:</label>
                            <input type="number" id="split2-amount" step="0.01">
                            <label>Category:</label>
                            <select id="split2-category">
                                <option value="food">Food & Dining</option>
                                <option value="shopping">Shopping</option>
                                <option value="transport">Transportation</option>
                                <option value="entertainment">Entertainment</option>
                                <option value="business">Business</option>
                            </select>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn-secondary" onclick="this.closest('.modal-overlay').remove()">Cancel</button>
                    <button class="btn-primary" onclick="saveSplitTransaction('${transactionId}')">Split Transaction</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
}

async function saveSplitTransaction(transactionId) {
    const split1Amount = parseFloat(document.getElementById('split1-amount').value);
    const split1Category = document.getElementById('split1-category').value;
    const split2Amount = parseFloat(document.getElementById('split2-amount').value);
    const split2Category = document.getElementById('split2-category').value;
    
    if (!split1Amount || !split2Amount) {
        showError('Please enter amounts for both parts');
        return;
    }
    
    try {
        const response = await fetch('/api/transactions/split', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                transaction_id: transactionId,
                splits: [
                    { amount: split1Amount, category: split1Category },
                    { amount: split2Amount, category: split2Category }
                ]
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                // Reload transactions
                await loadTransactions();
                
                // Refresh dashboard stats to reflect changes
                loadDashboardStats();
                
                showToast('Transaction split successfully', 'success');
                // Close modal
                document.querySelector('.modal-overlay').remove();
            } else {
                showError('Failed to split transaction: ' + result.error);
            }
        } else {
            showError('Failed to split transaction');
        }
    } catch (error) {
        console.error('Error splitting transaction:', error);
        showError('Failed to split transaction: ' + error.message);
    }
}

function updateStats() {
    const total = totalTransactions; // Use total from API, not filtered length
    const matched = filteredTransactions.filter(tx => tx.has_receipt || tx.receipt_url).length;
    const missing = total - matched;
    const totalAmount = filteredTransactions.reduce((sum, tx) => sum + Math.abs(tx.amount || 0), 0);
    
    // Update pagination summary
    const paginationSummary = document.getElementById('pagination-summary');
    if (paginationSummary) {
        const start = (currentPage - 1) * pageSize + 1;
        const end = Math.min(currentPage * pageSize, total);
        paginationSummary.textContent = `Showing ${start}-${end} of ${total} transactions`;
    }
    
    // Update page info
    const pageInfo = document.getElementById('page-info');
    if (pageInfo) {
        const totalPages = Math.ceil(total / pageSize);
        pageInfo.textContent = `Page ${currentPage} of ${totalPages} • ${pageSize} per page`;
    }
    
    console.log('📊 Stats updated:', { total, matched, missing, totalAmount, currentPage });
}

function updatePagination() {
    const totalPages = Math.ceil(totalTransactions / pageSize);
    const paginationControls = document.getElementById('pagination-controls');
    
    if (!paginationControls) return;
    
    let paginationHTML = '';
    
    if (totalPages > 1) {
        // Previous button
        paginationHTML += `
            <button class="pagination-btn" onclick="changePage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>
                <i class="fas fa-chevron-left"></i>
            </button>
        `;
        
        // Page numbers
        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
                paginationHTML += `
                    <button class="pagination-btn ${i === currentPage ? 'active' : ''}" onclick="changePage(${i})">
                        ${i}
                    </button>
                `;
            } else if (i === currentPage - 3 || i === currentPage + 3) {
                paginationHTML += '<span class="pagination-ellipsis">...</span>';
            }
        }
        
        // Next button
        paginationHTML += `
            <button class="pagination-btn" onclick="changePage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>
                <i class="fas fa-chevron-right"></i>
            </button>
        `;
    }
    
    paginationControls.innerHTML = paginationHTML;
}

async function changePage(page) {
    const totalPages = Math.ceil(totalTransactions / pageSize);
    if (page < 1 || page > totalPages) return;
    
    console.log(`🔄 Changing to page ${page} of ${totalPages}`);
    await loadTransactions(page);
}

function updateBusinessStats(businessBreakdown) {
    console.log('🏢 Updating business stats:', businessBreakdown);
    
    // Business type mapping for case-insensitive matching
    const businessTypeMapping = {
        'personal': 'personal',
        'down home': 'down-home',
        'music city rodeo': 'music-city-rodeo'
    };
    
    // Update business stats in the UI
    Object.keys(businessBreakdown).forEach(businessType => {
        const stats = businessBreakdown[businessType];
        const businessTypeKey = businessType.toLowerCase();
        const cssClass = businessTypeMapping[businessTypeKey] || businessTypeKey;
        
        console.log(`📊 Updating ${businessType} (${cssClass}):`, stats);
        
        // Find the business card by CSS class
        const businessCard = document.querySelector(`.business-card.${cssClass}`);
        if (businessCard) {
            // Update amount
            const amountElement = businessCard.querySelector('.business-amount');
            if (amountElement) {
                amountElement.textContent = `$${stats.amount.toLocaleString()}`;
            }
            
            // Update transaction count
            const countElement = businessCard.querySelector('.business-count');
            if (countElement) {
                countElement.textContent = stats.count;
            }
            
            // Update matched count
            const matchedElement = businessCard.querySelector('.business-matched');
            if (matchedElement) {
                matchedElement.textContent = stats.matched;
            }
            
            // Update missing count
            const missingElement = businessCard.querySelector('.business-missing');
            if (missingElement) {
                missingElement.textContent = stats.missing;
            }
            
            console.log(`✅ Updated ${businessType} card successfully`);
        } else {
            console.warn(`⚠️ Business card not found for: ${businessType} (${cssClass})`);
        }
    });
}

function updateElement(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

function setupResponsive() {
    const checkResponsive = () => {
        if (window.innerWidth <= 768 && currentView === 'table') {
            switchView('cards');
        }
    };
    
    window.addEventListener('resize', checkResponsive);
    checkResponsive();
}

function setupDashboard() {
    // Load dashboard stats
    loadDashboardStats();
    
    // Load system health status
    loadSystemHealth();
    
    // Setup automatic refresh every 30 seconds
    setInterval(loadDashboardStats, 30000);
    setInterval(loadSystemHealth, 30000);
    
    // Setup other dashboard functionality
    console.log('🎯 Dashboard setup complete with live updates');
}

async function loadDashboardStats() {
    try {
        console.log('📊 Loading dashboard stats...');
        const response = await fetch('/api/dashboard-stats');
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                console.log('📈 Dashboard stats received:', data.stats);
                
                // Update all dashboard stat elements
                updateElement('total-expenses', `$${data.stats.total_expenses.toLocaleString()}`);
                updateElement('total-transactions', data.stats.total_transactions);
                updateElement('match-rate', `${data.stats.match_rate}%`);
                updateElement('ai-processed', data.stats.ai_processed);
                updateElement('matched-transactions', data.stats.matched_transactions);
                updateElement('missing-receipts', data.stats.missing_receipts);
                
                // Update business breakdown if available
                if (data.stats.business_breakdown) {
                    updateBusinessStats(data.stats.business_breakdown);
                }
                
                console.log('✅ Dashboard stats updated successfully');
            } else {
                console.error('❌ Dashboard stats API returned error:', data.error);
            }
        } else {
            console.error('❌ Failed to fetch dashboard stats:', response.status);
        }
    } catch (error) {
        console.error('❌ Error loading dashboard stats:', error);
    }
}

async function loadSystemHealth() {
    try {
        console.log('🏥 Loading system health...');
        const response = await fetch('/api/system-health');
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                console.log('🏥 System health received:', data.health);
                
                // Update connection statuses
                updateConnectionStatuses(data.health);
                
                console.log('✅ System health updated successfully');
            } else {
                console.error('❌ System health API returned error:', data.error);
            }
        } else {
            console.error('❌ Failed to fetch system health:', response.status);
        }
    } catch (error) {
        console.error('❌ Error loading system health:', error);
    }
}

function updateConnectionStatuses(health) {
    // Update Teller connection status
    const tellerStatus = document.getElementById('teller-status');
    if (tellerStatus) {
        tellerStatus.textContent = health.teller_connected ? 'Connected' : 'Disconnected';
        tellerStatus.className = health.teller_connected ? 'status-connected' : 'status-disconnected';
    }
    
    // Update Gmail connection statuses
    if (health.gmail_accounts) {
        health.gmail_accounts.forEach(account => {
            const statusElement = document.getElementById(`gmail-status-${account.email.replace(/[^a-zA-Z0-9]/g, '-')}`);
            if (statusElement) {
                statusElement.textContent = account.connected ? 'Connected' : 'Disconnected';
                statusElement.className = account.connected ? 'status-connected' : 'status-disconnected';
            }
        });
    }
}

function debounce(func, wait) {
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

function showError(message) {
    console.error('❌ Error:', message);
    showToast(message, 'error');
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'times-circle' : 'info-circle'}"></i>
            <span>${message}</span>
        </div>
    `;
    
    document.body.appendChild(toast);
    
    // Remove after 5 seconds
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 5000);
}

// ===== MISSING FUNCTIONS FROM HTML =====

// Settings and Theme Functions
function toggleSettingsDropdown() {
    console.log('⚙️ Toggle settings dropdown called');
    const dropdownMenu = document.getElementById('settings-dropdown-menu');
    if (dropdownMenu) {
        const isVisible = dropdownMenu.classList.contains('active');
        
        if (isVisible) {
            dropdownMenu.classList.remove('active');
        } else {
            // Close any other open dropdowns first
            document.querySelectorAll('.settings-dropdown-menu.active').forEach(menu => {
                menu.classList.remove('active');
            });
            
            dropdownMenu.classList.add('active');
            
            // Load connection statuses when dropdown is opened
            loadConnectionStatuses();
        }
    }
}

// Close dropdown when clicking outside
document.addEventListener('click', function(event) {
    const dropdown = document.querySelector('.settings-dropdown');
    const dropdownMenu = document.getElementById('settings-dropdown-menu');
    
    if (dropdown && !dropdown.contains(event.target) && dropdownMenu) {
        dropdownMenu.classList.remove('active');
    }
});

// Teller Connect Integration
let tellerConnect = null;

function initializeTellerConnect() {
    try {
        if (typeof TellerConnect !== 'undefined') {
            tellerConnect = TellerConnect.setup({
                applicationId: 'app_pbvpiocruhfnvkhf1k000', // Your Teller app ID
                environment: 'development',
                onSuccess: handleTellerSuccess,
                onExit: handleTellerExit,
                onError: handleTellerError
            });
            console.log('✅ Teller Connect initialized');
        } else {
            console.error('❌ Teller Connect SDK not loaded');
        }
    } catch (error) {
        console.error('❌ Failed to initialize Teller Connect:', error);
    }
}

function openTellerConnect() {
    console.log('🏦 Opening Teller Connect...');
    
    if (!tellerConnect) {
        console.error('❌ Teller Connect not initialized');
        showNotification('❌ Teller Connect not available. Please refresh the page.', 'error');
        return;
    }
    
    try {
        tellerConnect.open();
        toggleSettingsDropdown(); // Close dropdown
    } catch (error) {
        console.error('❌ Failed to open Teller Connect:', error);
        showNotification('❌ Failed to open connection dialog: ' + error.message, 'error');
    }
}

function handleTellerSuccess(authorization) {
    console.log('🎉 Bank connected successfully:', authorization);
    
    // Save the authorization to our backend
    fetch('/api/connect-bank', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            access_token: authorization.accessToken,
            user_id: authorization.user?.id || 'user_' + Date.now(),
            enrollment_id: authorization.enrollment?.id,
            institution: authorization.enrollment?.institution || 'Bank'
        })
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            showNotification('✅ Bank connected successfully!', 'success');
            loadConnectionStatuses();
        } else {
            throw new Error(result.error || 'Failed to save connection');
        }
    })
    .catch(error => {
        console.error('❌ Failed to save bank connection:', error);
        showNotification('❌ Failed to save connection: ' + error.message, 'error');
    });
}

function handleTellerExit() {
    console.log('🚪 Teller Connect closed');
}

function handleTellerError(error) {
    console.error('❌ Teller Connect error:', error);
    showNotification('❌ Connection failed: ' + error.message, 'error');
}

// Gmail Integration
function connectGmail() {
    console.log('📧 Connecting Gmail...');
    
    fetch('/api/connect-gmail', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'connect' })
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            showNotification('✅ Gmail connected successfully!', 'success');
            loadConnectionStatuses();
        } else {
            throw new Error(result.error || 'Failed to connect Gmail');
        }
    })
    .catch(error => {
        console.error('❌ Failed to connect Gmail:', error);
        showNotification('❌ Failed to connect Gmail: ' + error.message, 'error');
    });
}

function scanEmailReceipts() {
    console.log('🔍 Scanning email receipts...');
    
    showNotification('🔍 Scanning emails for receipts...', 'info');
    
    fetch('/api/scan-emails-for-receipts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ days_back: 30, max_emails: 50 })
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            const receiptCount = result.receipts_found || 0;
            showNotification(`✅ Found ${receiptCount} receipts in emails!`, 'success');
        } else {
            throw new Error(result.error || 'Failed to scan emails');
        }
    })
    .catch(error => {
        console.error('❌ Failed to scan emails:', error);
        showNotification('❌ Failed to scan emails: ' + error.message, 'error');
    });
}

// Google Sheets Integration
function connectGoogleSheets() {
    console.log('📊 Connecting Google Sheets...');
    showNotification('📊 Google Sheets integration coming soon!', 'info');
}

function exportToSheets() {
    console.log('📤 Exporting to Google Sheets...');
    
    fetch('/api/export-to-sheets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ export_type: 'all' })
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            showNotification('✅ Data exported to Google Sheets!', 'success');
        } else {
            throw new Error(result.error || 'Failed to export data');
        }
    })
    .catch(error => {
        console.error('❌ Failed to export to sheets:', error);
        showNotification('❌ Failed to export: ' + error.message, 'error');
    });
}

// Cloud Storage Integration
function connectCloudStorage() {
    console.log('☁️ Connecting cloud storage...');
    showNotification('☁️ Cloud storage integration coming soon!', 'info');
}

function backupData() {
    console.log('💾 Backing up data...');
    showNotification('💾 Backup functionality coming soon!', 'info');
}

// Bank Transaction Sync
function syncBankTransactions() {
    console.log('🔄 Syncing bank transactions...');
    
    showNotification('🔄 Syncing transactions...', 'info');
    
    fetch('/api/sync-bank-transactions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sync_historical: true, days_back: 365 })
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            const transactionCount = result.transactions_synced || 0;
            showNotification(`✅ Synced ${transactionCount} transactions!`, 'success');
            loadConnectionStatuses();
        } else {
            throw new Error(result.error || 'Failed to sync transactions');
        }
    })
    .catch(error => {
        console.error('❌ Failed to sync transactions:', error);
        showNotification('❌ Failed to sync: ' + error.message, 'error');
    });
}

// System Settings
function changeTheme(theme) {
    console.log('🎨 Changing theme to:', theme);
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    showNotification(`🎨 Theme changed to ${theme}`, 'success');
}

function toggleNotifications(enabled) {
    console.log('🔔 Notifications:', enabled ? 'enabled' : 'disabled');
    localStorage.setItem('notifications', enabled);
    showNotification(`🔔 Notifications ${enabled ? 'enabled' : 'disabled'}`, 'success');
}

function openSystemSettings() {
    console.log('⚙️ Opening system settings...');
    showNotification('⚙️ Advanced settings coming soon!', 'info');
}

// Load connection statuses
async function loadConnectionStatuses() {
    try {
        // Load bank connection status
        const bankResponse = await fetch('/api/connection-stats');
        const bankStats = await bankResponse.json();
        
        const bankStatus = document.getElementById('bank-connection-status');
        const syncBtn = document.getElementById('sync-bank-btn');
        
        if (bankStats.success && bankStats.connected_accounts > 0) {
            bankStatus.innerHTML = `
                <div class="status-item connected">
                    <i class="fas fa-circle status-dot"></i>
                    <span>${bankStats.connected_accounts} bank(s) connected</span>
                </div>
            `;
            syncBtn.style.display = 'block';
        } else {
            bankStatus.innerHTML = `
                <div class="status-item disconnected">
                    <i class="fas fa-circle status-dot"></i>
                    <span>No banks connected</span>
                </div>
            `;
            syncBtn.style.display = 'none';
        }
        
        // Load Gmail status
        const gmailResponse = await fetch('/api/gmail-accounts');
        const gmailData = await gmailResponse.json();
        
        const gmailStatus = document.getElementById('email-connection-status');
        const scanBtn = document.getElementById('scan-email-btn');
        
        if (gmailData.success && gmailData.accounts && gmailData.accounts.length > 0) {
            gmailStatus.innerHTML = `
                <div class="status-item connected">
                    <i class="fas fa-circle status-dot"></i>
                    <span>${gmailData.accounts.length} Gmail account(s) connected</span>
                </div>
            `;
            scanBtn.style.display = 'block';
        } else {
            gmailStatus.innerHTML = `
                <div class="status-item disconnected">
                    <i class="fas fa-circle status-dot"></i>
                    <span>No Gmail accounts connected</span>
                </div>
            `;
            scanBtn.style.display = 'none';
        }
        
        // Load other service statuses
        const systemResponse = await fetch('/api/system-health');
        const systemHealth = await systemResponse.json();
        
        // Google Sheets status
        const sheetsStatus = document.getElementById('sheets-connection-status');
        const exportBtn = document.getElementById('export-sheets-btn');
        
        if (systemHealth.services && systemHealth.services.sheets && systemHealth.services.sheets.status === 'connected') {
            sheetsStatus.innerHTML = `
                <div class="status-item connected">
                    <i class="fas fa-circle status-dot"></i>
                    <span>Google Sheets connected</span>
                </div>
            `;
            exportBtn.style.display = 'block';
        } else {
            sheetsStatus.innerHTML = `
                <div class="status-item disconnected">
                    <i class="fas fa-circle status-dot"></i>
                    <span>Not connected</span>
                </div>
            `;
            exportBtn.style.display = 'none';
        }
        
        // Storage status
        const storageStatus = document.getElementById('storage-connection-status');
        const backupBtn = document.getElementById('backup-btn');
        
        if (systemHealth.services && systemHealth.services.storage && systemHealth.services.storage.status === 'connected') {
            storageStatus.innerHTML = `
                <div class="status-item connected">
                    <i class="fas fa-circle status-dot"></i>
                    <span>Cloud storage connected</span>
                </div>
            `;
            backupBtn.style.display = 'block';
        } else {
            storageStatus.innerHTML = `
                <div class="status-item disconnected">
                    <i class="fas fa-circle status-dot"></i>
                    <span>Not connected</span>
                </div>
            `;
            backupBtn.style.display = 'none';
        }
        
    } catch (error) {
        console.error('❌ Failed to load connection statuses:', error);
    }
}

// Initialize Teller Connect when page loads
document.addEventListener('DOMContentLoaded', function() {
    initializeTellerConnect();
    
    // Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    const themeSelector = document.getElementById('theme-selector');
    if (themeSelector) {
        themeSelector.value = savedTheme;
    }
    
    // Load saved notification setting
    const notificationsEnabled = localStorage.getItem('notifications') === 'true';
    const notificationsToggle = document.getElementById('notifications-toggle');
    if (notificationsToggle) {
        notificationsToggle.checked = notificationsEnabled;
    }
});

