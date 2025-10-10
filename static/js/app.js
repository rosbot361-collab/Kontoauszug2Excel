// KontoExport - Single Page Application
const API_BASE = window.location.origin;

// Global State
let selectedFile = null;
let currentJobId = null;
let pollInterval = null;

// DOM Elements
let fileInput, uploadZone, uploadButton, bankSelect, formatSelect;
let uploadState, processingState, completeState, errorState;

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM Content Loaded - Initializing...');

    // Get DOM Elements after page loads
    fileInput = document.getElementById('fileInput');
    uploadZone = document.getElementById('uploadZone');
    uploadButton = document.getElementById('uploadButton');
    bankSelect = document.getElementById('bankSelect');
    formatSelect = document.getElementById('formatSelect');

    uploadState = document.getElementById('uploadState');
    processingState = document.getElementById('processingState');
    completeState = document.getElementById('completeState');
    errorState = document.getElementById('errorState');

    console.log('Elements found:', {
        fileInput: !!fileInput,
        uploadZone: !!uploadZone,
        uploadButton: !!uploadButton,
        bankSelect: !!bankSelect,
        formatSelect: !!formatSelect
    });

    setupEventListeners();
    console.log('Event listeners setup complete');
});

function setupEventListeners() {
    console.log('Setting up event listeners...');

    // File Input
    if (fileInput) {
        fileInput.addEventListener('change', handleFileSelect);
        console.log('File input listener added');
    }

    // Upload Zone Click
    if (uploadZone) {
        uploadZone.addEventListener('click', function() {
            console.log('Upload zone clicked');
            fileInput.click();
        });
        console.log('Upload zone click listener added');

        // Drag & Drop
        uploadZone.addEventListener('dragover', handleDragOver);
        uploadZone.addEventListener('dragleave', handleDragLeave);
        uploadZone.addEventListener('drop', handleDrop);
        console.log('Drag & drop listeners added');
    }

    // Upload Button
    uploadButton.addEventListener('click', startUpload);

    // Remove File Button
    const removeFileBtn = document.getElementById('removeFileBtn');
    if (removeFileBtn) {
        removeFileBtn.addEventListener('click', removeFile);
    }

    // Complete State Buttons
    const deleteBtn = document.getElementById('deleteBtn');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', deleteAndReset);
    }

    const newConversionBtn = document.getElementById('newConversionBtn');
    if (newConversionBtn) {
        newConversionBtn.addEventListener('click', resetToUpload);
    }

    // Error State Button
    const retryBtn = document.getElementById('retryBtn');
    if (retryBtn) {
        retryBtn.addEventListener('click', resetToUpload);
    }
}

// File Handling
function handleFileSelect(event) {
    console.log('File selected via input');
    const file = event.target.files[0];
    if (file) {
        console.log('File:', file.name, file.size, 'bytes');
        processFile(file);
    }
}

function handleDragOver(event) {
    event.preventDefault();
    event.stopPropagation();
    console.log('Drag over');
    uploadZone.classList.add('active');
}

function handleDragLeave(event) {
    event.preventDefault();
    event.stopPropagation();
    console.log('Drag leave');
    uploadZone.classList.remove('active');
}

function handleDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    console.log('File dropped');
    uploadZone.classList.remove('active');

    const file = event.dataTransfer.files[0];
    if (file) {
        console.log('Dropped file:', file.name, file.size, 'bytes');
        processFile(file);
    }
}

function processFile(file) {
    // Validate file type
    if (!file.name.toLowerCase().endsWith('.pdf')) {
        showError('Bitte nur PDF-Dateien hochladen.');
        return;
    }

    // Validate file size (10 MB)
    if (file.size > 10 * 1024 * 1024) {
        showError('Datei zu groß. Maximale Größe: 10 MB');
        return;
    }

    selectedFile = file;
    displayFileInfo(file);
    enableUploadButton();
}

function displayFileInfo(file) {
    const fileInfo = document.getElementById('fileInfo');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');

    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);

    fileInfo.classList.remove('hidden');
    uploadZone.style.display = 'none';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function enableUploadButton() {
    uploadButton.disabled = false;
    uploadButton.classList.remove('opacity-50', 'cursor-not-allowed');
    uploadButton.classList.add('hover:scale-105');
}

function removeFile(event) {
    if (event) event.preventDefault();

    selectedFile = null;
    fileInput.value = '';

    document.getElementById('fileInfo').classList.add('hidden');
    uploadZone.style.display = 'block';

    uploadButton.disabled = true;
    uploadButton.classList.add('opacity-50', 'cursor-not-allowed');
    uploadButton.classList.remove('hover:scale-105');
}

// Upload & Processing
async function startUpload() {
    if (!selectedFile) return;

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('bank', bankSelect.value);
    formData.append('output_format', formatSelect.value);

    // Switch to processing state
    showState('processing');
    updateProcessingStatus('Upload läuft...', 10);

    try {
        const response = await fetch(`${API_BASE}/api/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload fehlgeschlagen');
        }

        const job = await response.json();
        currentJobId = job.job_id;

        updateProcessingStatus('PDF wird analysiert...', 33);
        startPolling();

    } catch (error) {
        console.error('Upload error:', error);
        showError(error.message);
    }
}

// Job Status Polling
function startPolling() {
    pollInterval = setInterval(checkJobStatus, 2000); // Every 2 seconds
    checkJobStatus(); // First check immediately
}

function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

async function checkJobStatus() {
    if (!currentJobId) return;

    try {
        const response = await fetch(`${API_BASE}/api/jobs/${currentJobId}`);

        if (!response.ok) {
            throw new Error('Status-Abfrage fehlgeschlagen');
        }

        const job = await response.json();

        switch (job.status) {
            case 'pending':
                updateProcessingStatus('Warte auf Verarbeitung...', 33);
                break;

            case 'processing':
                updateProcessingStatus('PDF wird verarbeitet...', 66);
                break;

            case 'completed':
                stopPolling();
                showComplete(job);
                break;

            case 'failed':
                stopPolling();
                showError(job.error_message || 'Verarbeitung fehlgeschlagen');
                break;
        }

    } catch (error) {
        console.error('Status check error:', error);
        stopPolling();
        showError(error.message);
    }
}

function updateProcessingStatus(message, progress) {
    document.getElementById('processingStatus').textContent = message;
    document.getElementById('progressFill').style.width = progress + '%';
}

// State Management
function showState(state) {
    // Hide all states
    uploadState.classList.add('hidden');
    processingState.classList.add('hidden');
    completeState.classList.add('hidden');
    errorState.classList.add('hidden');

    // Show requested state
    switch(state) {
        case 'upload':
            uploadState.classList.remove('hidden');
            break;
        case 'processing':
            processingState.classList.remove('hidden');
            break;
        case 'complete':
            completeState.classList.remove('hidden');
            break;
        case 'error':
            errorState.classList.remove('hidden');
            break;
    }

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showComplete(job) {
    const bankName = formatBankName(job.bank || 'auto');

    document.getElementById('detectedBank').textContent = bankName;
    document.getElementById('completeInfo').textContent =
        `Ihre Datei wurde erfolgreich konvertiert (${job.output_format || 'xlsx'})`;

    const downloadBtn = document.getElementById('downloadButton');
    downloadBtn.href = `${API_BASE}/api/download/${currentJobId}`;
    downloadBtn.download = `kontoauszug_${currentJobId.slice(0, 8)}.${job.output_format || 'xlsx'}`;

    showState('complete');
}

function showError(message) {
    document.getElementById('errorMessage').textContent = message;
    showState('error');
}

function formatBankName(bank) {
    const bankNames = {
        'sparkasse': 'Sparkasse',
        'ing': 'ING',
        'deutsche_bank': 'Deutsche Bank',
        'auto': 'Automatisch erkannt'
    };
    return bankNames[bank.toLowerCase()] || bank;
}

// Actions
async function deleteAndReset() {
    if (!currentJobId) {
        resetToUpload();
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/download/${currentJobId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            console.log('Job deleted successfully');
        }
    } catch (error) {
        console.error('Delete error:', error);
    }

    resetToUpload();
}

function resetToUpload() {
    // Stop any polling
    stopPolling();

    // Reset state
    selectedFile = null;
    currentJobId = null;
    fileInput.value = '';

    // Reset file info
    document.getElementById('fileInfo').classList.add('hidden');
    uploadZone.style.display = 'block';

    // Reset button
    uploadButton.disabled = true;
    uploadButton.classList.add('opacity-50', 'cursor-not-allowed');
    uploadButton.classList.remove('hover:scale-105');

    // Reset progress
    document.getElementById('progressFill').style.width = '0%';

    // Show upload state
    showState('upload');
}
