// AI Receipt Scanner Logic for FinanceFlow
// This file powers the camera, upload, extraction, and R2/MongoDB integration

// DOM Elements
const video = document.getElementById('camera-video');
const captureCanvas = document.getElementById('capture-canvas');
const thumbnailGrid = document.getElementById('thumbnail-grid');
const resultsContainer = document.getElementById('results-container');
const processingOverlay = document.getElementById('processing-overlay');
const processingText = document.getElementById('processing-text');
const processingDetail = document.getElementById('processing-detail');

let stream = null;
let capturedReceipts = [];

// Camera Functions
async function startCamera() {
    try {
        if (stream) {
            stopCamera();
            return;
        }
        const constraints = {
            video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } }
        };
        stream = await navigator.mediaDevices.getUserMedia(constraints);
        video.srcObject = stream;
        video.style.display = 'block';
        document.getElementById('viewfinder-overlay').classList.add('hidden');
    } catch (error) {
        showToast('Camera access denied', 'error');
    }
}

function stopCamera() {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
    }
    video.style.display = 'none';
    document.getElementById('viewfinder-overlay').classList.remove('hidden');
}

// Capture Image from Camera
async function captureImage() {
    if (!stream || !video.videoWidth) {
        showToast('Camera not ready', 'error');
        return;
    }
    const ctx = captureCanvas.getContext('2d');
    captureCanvas.width = video.videoWidth;
    captureCanvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0, captureCanvas.width, captureCanvas.height);
    captureCanvas.toBlob(async (blob) => {
        if (blob) {
            await processAndSaveReceipt(blob);
        } else {
            showToast('Failed to capture image', 'error');
        }
    }, 'image/jpeg', 0.95);
}

// Upload File(s)
function uploadFile() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.multiple = true;
    input.onchange = async (event) => {
        const files = Array.from(event.target.files);
        for (const file of files) {
            await processAndSaveReceipt(file);
        }
    };
    input.click();
}

// Main: Process and Save Receipt
async function processAndSaveReceipt(file) {
    showProcessingOverlay('Extracting Receipt', 'AI is reading your receipt...');
    try {
        // 1. Extract receipt data
        const extractForm = new FormData();
        extractForm.append('receipt_file', file);
        const extractResp = await fetch('/api/process-single-receipt', {
            method: 'POST',
            body: extractForm
        });
        if (!extractResp.ok) throw new Error('Extraction failed');
        const extractData = await extractResp.json();
        if (extractData.status !== 'success') throw new Error(extractData.message || 'Extraction error');

        // 2. Save to R2/MongoDB
        showProcessingOverlay('Saving Receipt', 'Uploading to secure cloud...');
        const saveForm = new FormData();
        saveForm.append('receipt_file', file);
        saveForm.append('extracted_data', JSON.stringify(extractData.extracted_data));
        const saveResp = await fetch('/api/save-processed-receipt', {
            method: 'POST',
            body: saveForm
        });
        if (!saveResp.ok) throw new Error('Save failed');
        const saveData = await saveResp.json();
        if (!saveData.success) throw new Error(saveData.error || 'Save error');

        // 3. Show result in UI
        addResultPanel({
            extracted: extractData.extracted_data,
            r2_url: saveData.r2_url,
            receipt_id: saveData.receipt_id
        });
        showToast('Receipt processed and saved!', 'success');
    } catch (err) {
        showToast(err.message || 'Processing failed', 'error');
    } finally {
        hideProcessingOverlay();
    }
}

// Add Result Panel to UI
function addResultPanel({extracted, r2_url, receipt_id}) {
    const panel = document.createElement('div');
    panel.className = 'result-panel show';
    panel.innerHTML = `
        <div class="result-header">
            <div class="result-info">
                <i class="fas fa-receipt"></i>
                <div>
                    <div class="result-title">${extracted.merchant || 'Unknown Merchant'}</div>
                    <div class="result-subtitle">${extracted.date || ''}</div>
                </div>
            </div>
            <div class="result-actions">
                ${r2_url ? `<a href="${r2_url}" target="_blank" class="action-icon" title="View Image"><i class="fas fa-image"></i></a>` : ''}
            </div>
        </div>
        <div class="result-data">
            <div class="data-row"><span class="data-label">Amount</span><span class="data-value">${extracted.total_amount || extracted.amount || ''}</span></div>
            <div class="data-row"><span class="data-label">Category</span><span class="data-value">${extracted.category || ''}</span></div>
            <div class="data-row"><span class="data-label">Business Type</span><span class="data-value">${extracted.business_type || ''}</span></div>
            <div class="data-row"><span class="data-label">Confidence</span><span class="data-value">${(extracted.overall_confidence || extracted.confidence_score || 0).toFixed(2)}</span></div>
            <div class="data-row"><span class="data-label">Receipt ID</span><span class="data-value">${receipt_id}</span></div>
        </div>
    `;
    resultsContainer.prepend(panel);
}

// Processing Overlay
function showProcessingOverlay(title, detail) {
    processingText.textContent = title;
    processingDetail.textContent = detail;
    processingOverlay.classList.add('show');
}
function hideProcessingOverlay() {
    processingOverlay.classList.remove('show');
}

// Toast Notifications
function showToast(msg, type='info') {
    let toast = document.createElement('div');
    toast.className = `toast show ${type}`;
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => { toast.classList.remove('show'); toast.remove(); }, 3500);
}

// Hook up UI buttons (if not already wired in HTML)
window.startCamera = startCamera;
window.captureImage = captureImage;
window.uploadFile = uploadFile; 