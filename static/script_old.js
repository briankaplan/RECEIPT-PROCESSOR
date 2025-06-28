// TallyUps - Ultimate Financial Intelligence PWA
// Complete Transaction System with Inline Editing, Receipts, and Real Data

console.log('🚀 Script.js loaded and executing...');

// Global variables
let app;
let transactions = [];
let filteredTransactions = [];
let currentView = 'table';
let currentSort = { field: 'date', direction: 'desc' };
let currentPage = 1;
let pageSize = 50;
let editingTransaction = null;

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Initializing TallyUps...');
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

async function loadTransactions() {
    try {
        console.log('📊 Loading transactions from API...');
        
        const response = await fetch(`/transactions?page=${currentPage}&page_size=${pageSize}&date_from=2024-07-01&date_to=2025-06-28`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('📊 API Response:', data);
        
        if (data.success && data.transactions) {
            transactions = data.transactions;
            filteredTransactions = [...transactions];
            
            console.log(`✅ Loaded ${transactions.length} transactions`);
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
    const total = filteredTransactions.length;
    const matched = filteredTransactions.filter(tx => tx.has_receipt || tx.receipt_url).length;
    const missing = total - matched;
    const totalAmount = filteredTransactions.reduce((sum, tx) => sum + Math.abs(tx.amount || 0), 0);
    
    // Update pagination summary
    const paginationSummary = document.getElementById('pagination-summary');
    if (paginationSummary) {
        paginationSummary.textContent = `Showing 1-${total} of ${total} transactions`;
    }
    
    // Update page info
    const pageInfo = document.getElementById('page-info');
    if (pageInfo) {
        pageInfo.textContent = `Page 1 of 1 • ${total} per page`;
    }
    
    console.log('📊 Stats updated:', { total, matched, missing, totalAmount });
}

function updatePagination() {
    const totalPages = Math.ceil(filteredTransactions.length / pageSize);
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

function changePage(page) {
    const totalPages = Math.ceil(filteredTransactions.length / pageSize);
    if (page < 1 || page > totalPages) return;
    
    currentPage = page;
    renderTransactions();
    updatePagination();
}

function updateBusinessStats() {
    const businessBreakdown = {};
    
    filteredTransactions.forEach(tx => {
        const businessType = tx.business_type || 'personal';
        if (!businessBreakdown[businessType]) {
            businessBreakdown[businessType] = { total: 0, count: 0 };
        }
        businessBreakdown[businessType].total += Math.abs(tx.amount || 0);
        businessBreakdown[businessType].count += 1;
    });
    
    // Update business stats in the UI
    Object.keys(businessBreakdown).forEach(businessType => {
        const stats = businessBreakdown[businessType];
        const elementId = `${businessType}-stats`;
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = `
                <div class="stat-value">$${stats.total.toFixed(2)}</div>
                <div class="stat-label">${stats.count} transactions</div>
            `;
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
    
    // Setup other dashboard functionality
    console.log('🎯 Dashboard setup complete');
}

async function loadDashboardStats() {
    try {
        const response = await fetch('/api/dashboard-stats');
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                updateElement('total-transactions', data.stats.total_transactions);
                updateElement('matched-transactions', data.stats.matched_transactions);
                updateElement('missing-transactions', data.stats.missing_transactions);
            }
        }
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
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
