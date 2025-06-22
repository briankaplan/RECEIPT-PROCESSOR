// Gmail Receipt Processor - Frontend JavaScript

// Global variables
let processingInProgress = false;

// Utility functions
function showAlert(type, message, duration = 5000) {
    const alertArea = document.getElementById('alert-area');
    const alertId = 'alert-' + Date.now();
    
    const alertHTML = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show fade-in" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    alertArea.insertAdjacentHTML('beforeend', alertHTML);
    
    // Auto-remove alert after duration
    setTimeout(() => {
        const alertElement = document.getElementById(alertId);
        if (alertElement) {
            const bsAlert = new bootstrap.Alert(alertElement);
            bsAlert.close();
        }
    }, duration);
}

function checkStatus() {
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateStatusIndicator(data.status);
                updateDashboardStats(data.status);
            } else {
                updateStatusIndicator(null, 'Error checking status');
            }
        })
        .catch(error => {
            console.error('Status check failed:', error);
            updateStatusIndicator(null, 'Connection error');
        });
}

function updateStatusIndicator(status, errorMessage = null) {
    const indicator = document.getElementById('status-indicator');
    
    if (errorMessage) {
        indicator.textContent = errorMessage;
        indicator.className = 'badge bg-danger';
        return;
    }
    
    if (status && status.gmail_connected) {
        indicator.textContent = 'Gmail Connected';
        indicator.className = 'badge bg-success';
    } else {
        indicator.textContent = 'Gmail Disconnected';
        indicator.className = 'badge bg-warning';
    }
}

function updateDashboardStats(status) {
    if (!status) return;
    
    const elements = {
        'processed-count': status.processed_emails || 0,
        'failed-count': status.failed_emails || 0,
        'bank-count': status.bank_statements || 0,
        'files-count': status.downloaded_files || 0
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            // Animate number change
            animateCountChange(element, value);
        }
    });
}

function animateCountChange(element, newValue) {
    const currentValue = parseInt(element.textContent) || 0;
    const increment = newValue > currentValue ? 1 : -1;
    const step = Math.abs(newValue - currentValue) / 10;
    
    if (currentValue === newValue) return;
    
    let current = currentValue;
    const timer = setInterval(() => {
        current += increment * Math.max(1, Math.floor(step));
        
        if ((increment > 0 && current >= newValue) || (increment < 0 && current <= newValue)) {
            current = newValue;
            clearInterval(timer);
        }
        
        element.textContent = current;
    }, 50);
}

// API interaction functions
async function makeAPIRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || `HTTP error! status: ${response.status}`);
        }
        
        return data;
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

// File handling functions
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function validateFileType(file, allowedTypes) {
    const fileExtension = file.name.split('.').pop().toLowerCase();
    return allowedTypes.includes(fileExtension);
}

// Email and receipt processing functions
function displayEmailPreview(emails) {
    if (!emails || emails.length === 0) {
        return '<p class="text-muted">No emails found.</p>';
    }
    
    let html = '<div class="table-responsive">';
    html += '<table class="table table-hover">';
    html += '<thead class="table-light">';
    html += '<tr><th>Subject</th><th>Sender</th><th>Date</th><th>Snippet</th></tr>';
    html += '</thead><tbody>';
    
    emails.forEach(email => {
        html += '<tr>';
        html += `<td class="text-truncate" style="max-width: 200px;">${escapeHtml(email.subject)}</td>`;
        html += `<td class="text-truncate" style="max-width: 150px;">${escapeHtml(email.sender)}</td>`;
        html += `<td class="text-nowrap">${formatDate(email.date)}</td>`;
        html += `<td class="text-truncate" style="max-width: 200px;">${escapeHtml(email.snippet)}</td>`;
        html += '</tr>';
    });
    
    html += '</tbody></table></div>';
    return html;
}

function displayProcessingResults(results) {
    if (!results || !results.details || results.details.length === 0) {
        return '<p class="text-muted">No receipts processed.</p>';
    }
    
    let html = '<div class="accordion" id="resultsAccordion">';
    
    results.details.forEach((detail, index) => {
        const matchCount = detail.matches ? detail.matches.length : 0;
        const confidenceClass = matchCount > 0 ? 'text-success' : 'text-muted';
        
        html += '<div class="accordion-item">';
        html += `<h2 class="accordion-header" id="heading${index}">`;
        html += `<button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse${index}">`;
        html += `<div class="d-flex justify-content-between w-100 me-3">`;
        html += `<span>${escapeHtml(detail.filename)}</span>`;
        html += `<span class="badge bg-secondary">${matchCount} matches</span>`;
        html += `</div>`;
        html += `</button></h2>`;
        
        html += `<div id="collapse${index}" class="accordion-collapse collapse" data-bs-parent="#resultsAccordion">`;
        html += '<div class="accordion-body">';
        
        // Receipt data
        if (detail.receipt_data) {
            html += '<div class="row">';
            html += '<div class="col-md-6">';
            html += '<h6 class="border-start-primary ps-2">Receipt Information</h6>';
            html += '<ul class="list-unstyled">';
            
            if (detail.receipt_data.merchant) {
                html += `<li><strong>Merchant:</strong> ${escapeHtml(detail.receipt_data.merchant)}</li>`;
            }
            if (detail.receipt_data.date) {
                html += `<li><strong>Date:</strong> ${escapeHtml(detail.receipt_data.date)}</li>`;
            }
            if (detail.receipt_data.total_amount) {
                html += `<li><strong>Amount:</strong> $${detail.receipt_data.total_amount.toFixed(2)}</li>`;
            }
            if (detail.receipt_data.payment_method) {
                html += `<li><strong>Payment:</strong> ${escapeHtml(detail.receipt_data.payment_method)}</li>`;
            }
            
            html += '</ul>';
            html += '</div>';
            
            // Bank matches
            html += '<div class="col-md-6">';
            if (detail.matches && detail.matches.length > 0) {
                html += '<h6 class="border-start-success ps-2">Bank Statement Matches</h6>';
                
                detail.matches.slice(0, 3).forEach((match, matchIndex) => {
                    const confidence = (match.confidence * 100).toFixed(1);
                    const confidenceBadge = match.confidence > 0.8 ? 'bg-success' : match.confidence > 0.6 ? 'bg-warning' : 'bg-secondary';
                    
                    html += '<div class="card mb-2">';
                    html += '<div class="card-body p-2">';
                    html += `<div class="d-flex justify-content-between align-items-start mb-1">`;
                    html += `<small class="text-muted">Match ${matchIndex + 1}</small>`;
                    html += `<span class="badge ${confidenceBadge}">${confidence}%</span>`;
                    html += `</div>`;
                    
                    if (match.transaction.description) {
                        html += `<div class="small"><strong>Description:</strong> ${escapeHtml(match.transaction.description)}</div>`;
                    }
                    if (match.transaction.amount) {
                        html += `<div class="small"><strong>Amount:</strong> $${Math.abs(match.transaction.amount).toFixed(2)}</div>`;
                    }
                    if (match.transaction.date) {
                        html += `<div class="small"><strong>Date:</strong> ${escapeHtml(match.transaction.date)}</div>`;
                    }
                    
                    if (match.match_reasons && match.match_reasons.length > 0) {
                        html += `<div class="small text-muted mt-1">`;
                        html += `<em>${match.match_reasons.join(', ')}</em>`;
                        html += `</div>`;
                    }
                    
                    html += '</div></div>';
                });
                
                if (detail.matches.length > 3) {
                    html += `<small class="text-muted">... and ${detail.matches.length - 3} more matches</small>`;
                }
            } else {
                html += '<h6 class="border-start-danger ps-2">No Bank Matches Found</h6>';
                html += '<p class="small text-muted">No matching transactions found in bank statements.</p>';
            }
            html += '</div>';
            html += '</div>';
        }
        
        html += '</div></div></div>';
    });
    
    html += '</div>';
    return html;
}

function formatDate(dateString) {
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    } catch (error) {
        return dateString;
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Progress tracking
function showProgress(message, progress = null) {
    const progressArea = document.getElementById('progress-area');
    if (!progressArea) return;
    
    let html = `<div class="d-flex align-items-center mb-2">`;
    html += `<div class="spinner-border spinner-border-sm me-2" role="status"></div>`;
    html += `<span>${message}</span>`;
    html += `</div>`;
    
    if (progress !== null) {
        html += `<div class="progress mb-2">`;
        html += `<div class="progress-bar" role="progressbar" style="width: ${progress}%"></div>`;
        html += `</div>`;
    }
    
    progressArea.innerHTML = html;
}

function hideProgress() {
    const progressArea = document.getElementById('progress-area');
    if (progressArea) {
        progressArea.innerHTML = '';
    }
}

// Local storage for settings
function saveSettings(settings) {
    try {
        localStorage.setItem('gmailReceiptProcessor', JSON.stringify(settings));
    } catch (error) {
        console.warn('Could not save settings to localStorage:', error);
    }
}

function loadSettings() {
    try {
        const saved = localStorage.getItem('gmailReceiptProcessor');
        return saved ? JSON.parse(saved) : {};
    } catch (error) {
        console.warn('Could not load settings from localStorage:', error);
        return {};
    }
}

// Bank Transactions Functions
function initializeDateInputs() {
    const today = new Date();
    const thirtyDaysAgo = new Date(today.getTime() - (30 * 24 * 60 * 60 * 1000));
    
    const endDateInput = document.getElementById('endDate');
    const startDateInput = document.getElementById('startDate');
    
    if (endDateInput) endDateInput.value = today.toISOString().split('T')[0];
    if (startDateInput) startDateInput.value = thirtyDaysAgo.toISOString().split('T')[0];
}

async function loadBankAccounts() {
    try {
        const response = await makeAPIRequest('/api/bank_accounts');
        
        if (response.success) {
            displayBankAccounts(response.accounts);
            populateAccountDropdown(response.accounts);
        } else {
            console.log('Bank accounts not available:', response.error);
        }
    } catch (error) {
        console.error('Failed to load bank accounts:', error);
    }
}

function displayBankAccounts(accounts) {
    const accountsList = document.getElementById('bank-accounts-list');
    const accountsSection = document.getElementById('bank-accounts-section');
    
    if (accounts && accounts.length > 0 && accountsList) {
        accountsList.innerHTML = '';
        
        accounts.forEach(account => {
            const accountCard = document.createElement('div');
            accountCard.className = 'col-md-4 mb-2';
            accountCard.innerHTML = `
                <div class="card">
                    <div class="card-body">
                        <h6 class="card-title">${escapeHtml(account.name)}</h6>
                        <p class="card-text">
                            <small class="text-muted">${escapeHtml(account.institution)}</small><br>
                            <strong>Balance: ${account.currency} ${account.balance.toFixed(2)}</strong><br>
                            <span class="badge bg-secondary">${escapeHtml(account.type)}</span>
                        </p>
                    </div>
                </div>
            `;
            accountsList.appendChild(accountCard);
        });
        
        if (accountsSection) accountsSection.style.display = 'block';
    }
}

function populateAccountDropdown(accounts) {
    const dropdown = document.getElementById('bankAccount');
    
    if (dropdown) {
        // Clear existing options except "All Accounts"
        dropdown.innerHTML = '<option value="">All Accounts</option>';
        
        if (accounts && accounts.length > 0) {
            accounts.forEach(account => {
                const option = document.createElement('option');
                option.value = account.id;
                option.textContent = `${account.name} (${account.institution})`;
                dropdown.appendChild(option);
            });
        }
    }
}

async function loadBankTransactions() {
    const startDate = document.getElementById('startDate')?.value;
    const endDate = document.getElementById('endDate')?.value;
    const accountId = document.getElementById('bankAccount')?.value;
    
    if (!startDate || !endDate) {
        showAlert('error', 'Please select both start and end dates');
        return;
    }
    
    showProgress('Loading bank transactions...');
    
    try {
        const params = new URLSearchParams({
            start_date: startDate,
            end_date: endDate
        });
        
        if (accountId) {
            params.append('account_id', accountId);
        }
        
        const response = await makeAPIRequest(`/api/transactions?${params}`);
        
        if (response.success) {
            displayTransactions(response.transactions);
            showAlert('success', `Loaded ${response.count} transactions`);
        } else {
            showAlert('error', response.error || 'Failed to load transactions');
        }
    } catch (error) {
        showAlert('error', 'Failed to load bank transactions: ' + error.message);
    } finally {
        hideProgress();
    }
}

function displayTransactions(transactions) {
    const tbody = document.getElementById('transactions-tbody');
    const section = document.getElementById('transactions-section');
    
    if (tbody) {
        tbody.innerHTML = '';
        
        if (transactions && transactions.length > 0) {
            transactions.forEach(tx => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${formatDate(tx.date)}</td>
                    <td>${escapeHtml(tx.description)}</td>
                    <td>${escapeHtml(tx.merchant_name)}</td>
                    <td class="${tx.amount < 0 ? 'text-danger' : 'text-success'}">
                        $${Math.abs(tx.amount).toFixed(2)}
                    </td>
                    <td><span class="badge bg-info">${escapeHtml(tx.category)}</span></td>
                    <td><small class="text-muted">${escapeHtml(tx.account_id.substring(0, 8))}...</small></td>
                    <td><span class="badge bg-${tx.status === 'posted' ? 'success' : 'warning'}">${escapeHtml(tx.status)}</span></td>
                `;
                tbody.appendChild(row);
            });
            
            if (section) section.style.display = 'block';
        } else {
            if (section) section.style.display = 'none';
            showAlert('info', 'No transactions found for the selected date range');
        }
    }
}

async function matchReceiptsToTransactions() {
    const startDate = document.getElementById('startDate')?.value;
    const endDate = document.getElementById('endDate')?.value;
    
    if (!startDate || !endDate) {
        showAlert('error', 'Please select both start and end dates');
        return;
    }
    
    showProgress('Finding intelligent receipt matches...');
    
    try {
        const response = await makeAPIRequest('/api/match_receipts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                start_date: startDate,
                end_date: endDate
            })
        });
        
        if (response.success) {
            displayReceiptMatches(response.matches);
            showAlert('success', `Found ${response.matched_count} receipt matches out of ${response.total_receipts} receipts`);
        } else {
            showAlert('error', response.error || 'Failed to match receipts');
        }
    } catch (error) {
        showAlert('error', 'Failed to match receipts: ' + error.message);
    } finally {
        hideProgress();
    }
}

function displayReceiptMatches(matches) {
    const matchesList = document.getElementById('matches-list');
    const section = document.getElementById('matches-section');
    
    if (matchesList) {
        matchesList.innerHTML = '';
        
        if (matches && matches.length > 0) {
            matches.forEach(match => {
                const confidence = Math.round(match.confidence * 100);
                const matchCard = document.createElement('div');
                matchCard.className = 'card mb-3';
                
                matchCard.innerHTML = `
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-5">
                                <h6 class="card-title">Receipt</h6>
                                <p class="card-text">
                                    <strong>Merchant:</strong> ${escapeHtml(match.receipt.merchant)}<br>
                                    <strong>Amount:</strong> $${match.receipt.amount.toFixed(2)}<br>
                                    <strong>Date:</strong> ${formatDate(match.receipt.date)}<br>
                                    ${match.receipt.ai_category ? `<strong>AI Category:</strong> <span class="badge bg-primary">${escapeHtml(match.receipt.ai_category)}</span><br>` : ''}
                                    ${match.receipt.business_purpose ? `<strong>Purpose:</strong> ${escapeHtml(match.receipt.business_purpose)}<br>` : ''}
                                    ${match.receipt.r2_url ? `<a href="${match.receipt.r2_url}" target="_blank" class="btn btn-sm btn-outline-primary mt-1">View Receipt</a>` : ''}
                                </p>
                            </div>
                            <div class="col-md-5">
                                ${match.matched_transaction ? `
                                    <h6 class="card-title">Matched Transaction</h6>
                                    <p class="card-text">
                                        <strong>Description:</strong> ${escapeHtml(match.matched_transaction.description)}<br>
                                        <strong>Merchant:</strong> ${escapeHtml(match.matched_transaction.merchant_name)}<br>
                                        <strong>Amount:</strong> $${Math.abs(match.matched_transaction.amount).toFixed(2)}<br>
                                        <strong>Date:</strong> ${formatDate(match.matched_transaction.date)}<br>
                                        <strong>Status:</strong> <span class="badge bg-success">${escapeHtml(match.matched_transaction.status)}</span>
                                    </p>
                                ` : `
                                    <h6 class="card-title text-muted">No Match Found</h6>
                                    <p class="text-muted">No matching bank transaction found for this receipt.</p>
                                `}
                            </div>
                            <div class="col-md-2">
                                <h6>Match Quality</h6>
                                <div class="text-center">
                                    <div class="progress mb-2">
                                        <div class="progress-bar bg-${confidence > 80 ? 'success' : confidence > 50 ? 'warning' : 'danger'}" 
                                             style="width: ${confidence}%"></div>
                                    </div>
                                    <strong>${confidence}%</strong>
                                    ${match.match_reasons && match.match_reasons.length > 0 ? `
                                        <ul class="list-unstyled mt-2">
                                            ${match.match_reasons.map(reason => `<li><small class="text-muted">• ${escapeHtml(reason)}</small></li>`).join('')}
                                        </ul>
                                    ` : ''}
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                
                matchesList.appendChild(matchCard);
            });
            
            if (section) section.style.display = 'block';
        } else {
            if (section) section.style.display = 'none';
            showAlert('info', 'No receipt matches found for the selected date range');
        }
    }
}

// Keyboard shortcuts
document.addEventListener('keydown', function(event) {
    // Ctrl/Cmd + R: Process receipts
    if ((event.ctrlKey || event.metaKey) && event.key === 'r' && !event.shiftKey) {
        event.preventDefault();
        const processBtn = document.getElementById('process-btn');
        if (processBtn && !processingInProgress) {
            processBtn.click();
        }
    }
    
    // Ctrl/Cmd + S: Scan emails
    if ((event.ctrlKey || event.metaKey) && event.key === 's') {
        event.preventDefault();
        const scanBtn = document.getElementById('scan-btn');
        if (scanBtn && !processingInProgress) {
            scanBtn.click();
        }
    }
});

// Initialize tooltips and popovers
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize Bootstrap popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Set up event listeners for existing functions
    document.getElementById('scan-btn')?.addEventListener('click', scanEmails);
    document.getElementById('process-btn')?.addEventListener('click', processReceipts);
    document.getElementById('upload-btn')?.addEventListener('click', handleFileUpload);
    document.getElementById('export-btn')?.addEventListener('click', exportToSheets);
    
    // Bank transactions event listeners
    document.getElementById('load-transactions-btn')?.addEventListener('click', loadBankTransactions);
    document.getElementById('match-receipts-btn')?.addEventListener('click', matchReceiptsToTransactions);
    
    // Additional receipt capture event listeners
    document.getElementById('google-photos-btn')?.addEventListener('click', scanGooglePhotos);
    document.getElementById('comprehensive-export-btn')?.addEventListener('click', exportComprehensiveData);
    document.getElementById('start-camera-btn')?.addEventListener('click', startCamera);
    document.getElementById('capture-photo-btn')?.addEventListener('click', capturePhoto);
    document.getElementById('retake-photo-btn')?.addEventListener('click', retakePhoto);
    document.getElementById('save-photo-btn')?.addEventListener('click', savePhoto);
    document.getElementById('upload-batch-btn')?.addEventListener('click', uploadBatchFiles);
    
    // File input preview
    document.getElementById('batch-files')?.addEventListener('change', previewBatchFiles);
    
    // Initialize date inputs and load bank accounts
    initializeDateInputs();
    loadBankAccounts();
    
    // Start status monitoring
    checkStatus();
    setInterval(checkStatus, 30000);
    
    // Load saved settings
    const settings = loadSettings();
    console.log('Loaded settings:', settings);
});

// Additional Receipt Capture Functions
async function scanGooglePhotos() {
    showProgress('Scanning Google Photos for receipts...');
    
    try {
        const response = await makeAPIRequest('/api/scan_google_photos', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                days_back: 30
            })
        });
        
        if (response.success) {
            showAlert('success', `Found ${response.photos_found} photos, processed ${response.receipts_processed} receipts, saved ${response.receipts_saved} to database`);
        } else {
            showAlert('error', response.error || 'Failed to scan Google Photos');
        }
    } catch (error) {
        showAlert('error', 'Failed to scan Google Photos: ' + error.message);
    } finally {
        hideProgress();
    }
}

async function exportComprehensiveData() {
    showProgress('Exporting comprehensive receipt data...');
    
    try {
        const response = await makeAPIRequest('/api/export_comprehensive');
        
        if (response.success) {
            // Create downloadable CSV file
            const headers = ['ID', 'Date of Transaction', 'Merchant', 'Price', 'Description (auto)', 'Receipt URL', 'Gmail ID', 'Gmail link to email', 'Match Status', 'Receipt Status', 'Category (full auto categorization)', 'Account', 'Is Subscription', 'Business'];
            
            let csvContent = headers.join(',') + '\n';
            
            response.data.forEach(row => {
                const csvRow = headers.map(header => {
                    let value = row[header] || '';
                    // Escape commas and quotes
                    if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
                        value = '"' + value.replace(/"/g, '""') + '"';
                    }
                    return value;
                }).join(',');
                csvContent += csvRow + '\n';
            });
            
            // Download file
            const blob = new Blob([csvContent], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `comprehensive_receipts_export_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            showAlert('success', `Exported ${response.exported_count} receipts with comprehensive data`);
        } else {
            showAlert('error', response.error || 'Failed to export data');
        }
    } catch (error) {
        showAlert('error', 'Failed to export data: ' + error.message);
    } finally {
        hideProgress();
    }
}

// Camera Functions
let cameraStream = null;
let capturedImageData = null;

async function startCamera() {
    try {
        const video = document.getElementById('camera-video');
        const placeholder = document.getElementById('camera-placeholder');
        const startBtn = document.getElementById('start-camera-btn');
        const captureBtn = document.getElementById('capture-photo-btn');
        
        cameraStream = await navigator.mediaDevices.getUserMedia({ 
            video: { facingMode: 'environment' } // Use back camera if available
        });
        
        video.srcObject = cameraStream;
        video.style.display = 'block';
        placeholder.style.display = 'none';
        startBtn.style.display = 'none';
        captureBtn.style.display = 'inline-block';
        
    } catch (error) {
        showAlert('error', 'Failed to access camera: ' + error.message);
    }
}

function capturePhoto() {
    const video = document.getElementById('camera-video');
    const canvas = document.getElementById('camera-canvas');
    const captureBtn = document.getElementById('capture-photo-btn');
    const retakeBtn = document.getElementById('retake-photo-btn');
    const saveBtn = document.getElementById('save-photo-btn');
    
    // Set canvas size to match video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    // Draw video frame to canvas
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    
    // Get image data
    capturedImageData = canvas.toDataURL('image/jpeg', 0.8);
    
    // Show canvas, hide video
    video.style.display = 'none';
    canvas.style.display = 'block';
    captureBtn.style.display = 'none';
    retakeBtn.style.display = 'inline-block';
    saveBtn.style.display = 'inline-block';
}

function retakePhoto() {
    const video = document.getElementById('camera-video');
    const canvas = document.getElementById('camera-canvas');
    const captureBtn = document.getElementById('capture-photo-btn');
    const retakeBtn = document.getElementById('retake-photo-btn');
    const saveBtn = document.getElementById('save-photo-btn');
    
    // Show video, hide canvas
    video.style.display = 'block';
    canvas.style.display = 'none';
    captureBtn.style.display = 'inline-block';
    retakeBtn.style.display = 'none';
    saveBtn.style.display = 'none';
    
    capturedImageData = null;
}

async function savePhoto() {
    if (!capturedImageData) {
        showAlert('error', 'No photo captured');
        return;
    }
    
    showProgress('Processing receipt photo...');
    
    try {
        const response = await makeAPIRequest('/api/camera_capture', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                image_data: capturedImageData,
                filename: `camera_receipt_${Date.now()}.jpg`
            })
        });
        
        if (response.success) {
            showAlert('success', 'Receipt photo processed and saved successfully');
            
            // Close modal and reset camera
            const modal = bootstrap.Modal.getInstance(document.getElementById('cameraModal'));
            modal.hide();
            resetCamera();
        } else {
            showAlert('error', response.error || 'Failed to process photo');
        }
    } catch (error) {
        showAlert('error', 'Failed to save photo: ' + error.message);
    } finally {
        hideProgress();
    }
}

function resetCamera() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }
    
    const video = document.getElementById('camera-video');
    const canvas = document.getElementById('camera-canvas');
    const placeholder = document.getElementById('camera-placeholder');
    const startBtn = document.getElementById('start-camera-btn');
    const captureBtn = document.getElementById('capture-photo-btn');
    const retakeBtn = document.getElementById('retake-photo-btn');
    const saveBtn = document.getElementById('save-photo-btn');
    
    video.style.display = 'none';
    canvas.style.display = 'none';
    placeholder.style.display = 'block';
    startBtn.style.display = 'inline-block';
    captureBtn.style.display = 'none';
    retakeBtn.style.display = 'none';
    saveBtn.style.display = 'none';
    
    capturedImageData = null;
}

// Batch Upload Functions
function previewBatchFiles() {
    const fileInput = document.getElementById('batch-files');
    const preview = document.getElementById('file-preview');
    
    preview.innerHTML = '';
    
    if (fileInput.files.length === 0) return;
    
    Array.from(fileInput.files).forEach((file, index) => {
        if (file.size > 10 * 1024 * 1024) { // 10MB limit
            showAlert('warning', `File ${file.name} is too large (max 10MB)`);
            return;
        }
        
        const col = document.createElement('div');
        col.className = 'col-md-3 mb-2';
        
        const card = document.createElement('div');
        card.className = 'card';
        
        const reader = new FileReader();
        reader.onload = function(e) {
            if (file.type.startsWith('image/')) {
                card.innerHTML = `
                    <img src="${e.target.result}" class="card-img-top" style="height: 100px; object-fit: cover;">
                    <div class="card-body p-2">
                        <small class="card-text">${file.name}</small>
                        <br><small class="text-muted">${formatFileSize(file.size)}</small>
                    </div>
                `;
            } else {
                card.innerHTML = `
                    <div class="card-body p-2 text-center">
                        <i data-feather="file-text" size="24"></i>
                        <br><small class="card-text">${file.name}</small>
                        <br><small class="text-muted">${formatFileSize(file.size)}</small>
                    </div>
                `;
                feather.replace();
            }
        };
        reader.readAsDataURL(file);
        
        col.appendChild(card);
        preview.appendChild(col);
    });
}

async function uploadBatchFiles() {
    const fileInput = document.getElementById('batch-files');
    
    if (fileInput.files.length === 0) {
        showAlert('error', 'Please select files to upload');
        return;
    }
    
    showProgress('Uploading and processing receipt files...');
    
    try {
        const formData = new FormData();
        Array.from(fileInput.files).forEach(file => {
            formData.append('files', file);
        });
        
        const response = await fetch('/api/batch_upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert('success', `Uploaded ${result.files_uploaded} files, processed ${result.receipts_processed} receipts, saved ${result.receipts_saved} to database`);
            
            // Close modal and reset form
            const modal = bootstrap.Modal.getInstance(document.getElementById('batchUploadModal'));
            modal.hide();
            document.getElementById('batch-upload-form').reset();
            document.getElementById('file-preview').innerHTML = '';
        } else {
            showAlert('error', result.error || 'Failed to upload files');
        }
    } catch (error) {
        showAlert('error', 'Failed to upload files: ' + error.message);
    } finally {
        hideProgress();
    }
}

// Reset camera when modal is closed
document.getElementById('cameraModal')?.addEventListener('hidden.bs.modal', resetCamera);

// Export functions for use in other scripts
window.GmailReceiptProcessor = {
    showAlert,
    checkStatus,
    makeAPIRequest,
    formatFileSize,
    validateFileType,
    displayEmailPreview,
    displayProcessingResults,
    saveSettings,
    loadSettings
};
