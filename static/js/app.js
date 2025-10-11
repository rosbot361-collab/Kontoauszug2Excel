// KontoExport - Single Page Application
const API_BASE = window.location.origin;

// Global State
let selectedFile = null;
let currentJobId = null;
let pollInterval = null;

// DOM Elements
let fileInput, uploadZone, uploadButton, bankSelect, formatSelect;
let uploadState, processingState, reviewState, completeState, errorState;
let reviewData = [];

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
    reviewState = document.getElementById('reviewState');
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

    // Review State Buttons
    const confirmDownloadBtn = document.getElementById('confirmDownloadBtn');
    if (confirmDownloadBtn) {
        confirmDownloadBtn.addEventListener('click', handleConfirmDownload);
    }

    const deleteReviewBtn = document.getElementById('deleteReviewBtn');
    if (deleteReviewBtn) {
        deleteReviewBtn.addEventListener('click', async () => {
            if (confirm('Möchten Sie die Daten wirklich löschen?')) {
                try {
                    await fetch(`${API_BASE}/api/jobs/${currentJobId}`, { method: 'DELETE' });
                    resetToUpload();
                } catch (error) {
                    console.error('Delete error:', error);
                    resetToUpload();
                }
            }
        });
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
    console.log('Processing file:', file.name);

    // Validate file type
    if (!file.name.toLowerCase().endsWith('.pdf')) {
        console.error('Invalid file type:', file.name);
        showError('Bitte nur PDF-Dateien hochladen.');
        return;
    }

    // Validate file size (10 MB)
    if (file.size > 10 * 1024 * 1024) {
        console.error('File too large:', file.size);
        showError('Datei zu groß. Maximale Größe: 10 MB');
        return;
    }

    console.log('File validation passed');
    selectedFile = file;
    displayFileInfo(file);
    enableUploadButton();
    console.log('Upload button should be enabled now');
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
    console.log('🚀 Starting upload...');

    if (!selectedFile) {
        console.error('No file selected!');
        return;
    }

    console.log('Selected file:', selectedFile.name);
    console.log('Bank:', bankSelect.value);
    console.log('Format:', formatSelect.value);

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('bank', bankSelect.value);
    formData.append('output_format', formatSelect.value);

    // Switch to processing state
    showState('processing');
    updateProcessingStatus('Upload läuft...', 10);

    try {
        console.log('Sending upload request to:', `${API_BASE}/api/upload`);
        const response = await fetch(`${API_BASE}/api/upload`, {
            method: 'POST',
            body: formData
        });

        console.log('Upload response status:', response.status);

        if (!response.ok) {
            const error = await response.json();
            console.error('Upload failed:', error);
            throw new Error(error.detail || 'Upload fehlgeschlagen');
        }

        const job = await response.json();
        console.log('Job created:', job);
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
                console.log('Job completed! Showing review state...');
                stopPolling();
                await showReview(job);
                console.log('Review state should be visible now');
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
    console.log('🔄 Switching to state:', state);

    // Hide all states
    uploadState.classList.add('hidden');
    processingState.classList.add('hidden');
    reviewState.classList.add('hidden');
    completeState.classList.add('hidden');
    errorState.classList.add('hidden');

    // Show requested state
    switch(state) {
        case 'upload':
            uploadState.classList.remove('hidden');
            console.log('✅ Upload state is now visible');
            break;
        case 'processing':
            processingState.classList.remove('hidden');
            console.log('✅ Processing state is now visible');
            break;
        case 'review':
            reviewState.classList.remove('hidden');
            console.log('✅ Review state is now visible');
            break;
        case 'complete':
            completeState.classList.remove('hidden');
            console.log('✅ Complete state is now visible');
            break;
        case 'error':
            errorState.classList.remove('hidden');
            console.log('✅ Error state is now visible');
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

// Review State Functions
let reviewHeaders = [];

async function showReview(job) {
    console.log('Showing review state for job:', job);

    try {
        // Try to download and parse the Excel file directly
        console.log('Downloading Excel file from:', `${API_BASE}/api/download/${currentJobId}`);
        const response = await fetch(`${API_BASE}/api/download/${currentJobId}`);

        if (!response.ok) {
            console.error('Download failed:', response.status);
            reviewHeaders = ['Datum', 'Beschreibung', 'Referenz', 'Soll', 'Haben', 'Saldo'];
            reviewData = createMockPreviewData();
        } else {
            // Get the file as array buffer
            const arrayBuffer = await response.arrayBuffer();
            console.log('Excel file downloaded, size:', arrayBuffer.byteLength);

            // Parse with XLSX library
            const workbook = XLSX.read(arrayBuffer, { type: 'array' });
            const firstSheet = workbook.Sheets[workbook.SheetNames[0]];

            // Get data WITHOUT headers (use header: 1 to get raw array)
            const rawData = XLSX.utils.sheet_to_json(firstSheet, { header: 1 });

            console.log('Raw Excel data:', rawData);
            console.log('First row (headers):', rawData[0]);

            if (rawData.length < 2) {
                console.error('Excel file is empty or has no data rows');
                reviewHeaders = ['Datum', 'Beschreibung', 'Referenz', 'Soll', 'Haben', 'Saldo'];
                reviewData = createMockPreviewData();
            } else {
                // First row is headers
                reviewHeaders = rawData[0].map(h => String(h || ''));
                console.log('Headers:', reviewHeaders);

                // Convert remaining rows to objects
                reviewData = rawData.slice(1).map(row => {
                    const obj = {};
                    reviewHeaders.forEach((header, index) => {
                        obj[header] = String(row[index] || '');
                    });
                    return obj;
                });

                console.log('Converted to review format:', reviewData.length, 'transactions');
                console.log('Sample transaction:', reviewData[0]);
            }
        }

        // Update stats
        document.getElementById('transactionCount').textContent = reviewData.length;
        document.getElementById('reviewDetectedBank').textContent = formatBankName(job.bank || 'auto');

        // Render table
        renderReviewTable();

        // Show review state
        showState('review');

    } catch (error) {
        console.error('Error loading preview:', error);
        // Create mock data on error
        reviewHeaders = ['Datum', 'Beschreibung', 'Referenz', 'Soll', 'Haben', 'Saldo'];
        reviewData = createMockPreviewData();

        // Still show review state
        document.getElementById('transactionCount').textContent = reviewData.length;
        document.getElementById('reviewDetectedBank').textContent = formatBankName(job.bank || 'auto');
        renderReviewTable();
        showState('review');
    }
}

function createMockPreviewData() {
    // Create some mock data for testing
    return [
        { date: '2024-01-15', description: 'Beispiel Transaktion 1', reference: 'REF001', debit: '100.00', credit: '', balance: '900.00' },
        { date: '2024-01-16', description: 'Beispiel Transaktion 2', reference: 'REF002', debit: '', credit: '50.00', balance: '950.00' },
        { date: '2024-01-17', description: 'Beispiel Transaktion 3', reference: 'REF003', debit: '200.00', credit: '', balance: '750.00' }
    ];
}

function renderReviewTable() {
    // Render headers
    const thead = document.getElementById('dataTableHeader');
    thead.innerHTML = '';

    reviewHeaders.forEach((header, index) => {
        const th = document.createElement('th');
        th.className = 'px-3 py-3 text-left font-semibold border-b-2 border-border whitespace-nowrap';
        th.textContent = header;
        // Make numeric columns right-aligned
        if (header.toLowerCase().includes('soll') ||
            header.toLowerCase().includes('haben') ||
            header.toLowerCase().includes('saldo') ||
            header.toLowerCase().includes('debit') ||
            header.toLowerCase().includes('credit') ||
            header.toLowerCase().includes('balance')) {
            th.className += ' text-right';
        }
        thead.appendChild(th);
    });

    // Render body
    const tbody = document.getElementById('dataTableBody');
    tbody.innerHTML = '';

    reviewData.forEach((row, rowIndex) => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-gray-50 transition-colors border-b border-gray-200';

        reviewHeaders.forEach((header, colIndex) => {
            const td = document.createElement('td');
            td.className = 'px-3 py-2 border-r border-gray-200';

            // Create Excel-like input
            const input = document.createElement('input');
            input.type = 'text';
            input.value = row[header] || '';
            input.className = 'w-full px-2 py-1 border border-transparent hover:border-blue-300 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 rounded';

            // Make numeric columns right-aligned
            if (header.toLowerCase().includes('soll') ||
                header.toLowerCase().includes('haben') ||
                header.toLowerCase().includes('saldo') ||
                header.toLowerCase().includes('debit') ||
                header.toLowerCase().includes('credit') ||
                header.toLowerCase().includes('balance')) {
                input.className += ' text-right';
            }

            // Set minimum width for better readability
            input.style.minWidth = '100px';

            input.dataset.row = rowIndex;
            input.dataset.field = header;

            input.addEventListener('change', handleCellEdit);
            input.addEventListener('focus', function() {
                this.select(); // Select all text on focus (Excel-like behavior)
                updateCellPreview(this.value, header); // Update preview when cell is focused
            });
            input.addEventListener('input', function() {
                updateCellPreview(this.value, header); // Update preview while typing
            });

            td.appendChild(input);
            tr.appendChild(td);
        });

        tbody.appendChild(tr);
    });
}

function updateCellPreview(content, columnName) {
    const preview = document.getElementById('cellPreview');
    if (preview) {
        if (content && content.trim()) {
            preview.innerHTML = `<span class="text-gray-800">${content}</span>`;
        } else {
            preview.innerHTML = '<span class="text-gray-400 italic">Klicken Sie auf eine Zelle, um den vollständigen Inhalt hier zu sehen...</span>';
        }
    }
}

function handleCellEdit(event) {
    const rowIndex = parseInt(event.target.dataset.row);
    const field = event.target.dataset.field;
    const value = event.target.value;

    if (reviewData[rowIndex]) {
        reviewData[rowIndex][field] = value;
        console.log(`Updated row ${rowIndex}, field ${field}:`, value);
    }
}

async function handleConfirmDownload() {
    console.log('Confirming download with edited data:', reviewData);

    try {
        // Send edited data back to backend
        const response = await fetch(`${API_BASE}/api/update/${currentJobId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ transactions: reviewData })
        });

        if (!response.ok) {
            throw new Error('Failed to update data');
        }

        // Now download the updated file
        const downloadBtn = document.getElementById('downloadButton');
        downloadBtn.href = `${API_BASE}/api/download/${currentJobId}`;
        downloadBtn.download = `kontoauszug_${currentJobId.slice(0, 8)}.xlsx`;

        // Show complete state
        const job = await response.json();
        showComplete(job);

    } catch (error) {
        console.error('Error confirming download:', error);
        showError('Fehler beim Aktualisieren der Daten');
    }
}
