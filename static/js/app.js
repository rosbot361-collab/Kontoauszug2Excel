// Kontoauszug2Excel Frontend
const API_BASE = window.location.origin;

// DOM-Elemente
const fileInput = document.getElementById('file-input');
const dropzone = document.getElementById('dropzone');
const uploadBtn = document.getElementById('upload-btn');
const bankSelect = document.getElementById('bank-select');
const formatSelect = document.getElementById('format-select');

const uploadSection = document.getElementById('upload-section');
const progressSection = document.getElementById('progress-section');
const resultSection = document.getElementById('result-section');
const errorSection = document.getElementById('error-section');

const progressBar = document.getElementById('progress-bar');
const progressText = document.getElementById('progress-text');
const resultText = document.getElementById('result-text');
const errorText = document.getElementById('error-text');

const downloadBtn = document.getElementById('download-btn');
const deleteBtn = document.getElementById('delete-btn');
const newUploadBtn = document.getElementById('new-upload-btn');
const retryBtn = document.getElementById('retry-btn');

let selectedFile = null;
let currentJobId = null;
let pollInterval = null;

// Event-Listener
dropzone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', handleFileSelect);
uploadBtn.addEventListener('click', handleUpload);
deleteBtn.addEventListener('click', handleDelete);
newUploadBtn.addEventListener('click', resetUI);
retryBtn.addEventListener('click', resetUI);

// Drag & Drop
dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
});

dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('dragover');
});

dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
});

// Datei-Auswahl
function handleFileSelect(e) {
    handleFile(e.target.files[0]);
}

function handleFile(file) {
    if (!file) return;

    if (!file.name.endsWith('.pdf')) {
        showError('Bitte nur PDF-Dateien hochladen.');
        return;
    }

    if (file.size > 10 * 1024 * 1024) {
        showError('Datei zu groß. Max. 10 MB erlaubt.');
        return;
    }

    selectedFile = file;
    dropzone.querySelector('p').textContent = `✅ ${file.name}`;
    uploadBtn.disabled = false;
}

// Upload
async function handleUpload() {
    if (!selectedFile) return;

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('bank', bankSelect.value);
    formData.append('output_format', formatSelect.value);

    showProgress();

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

        progressText.textContent = 'PDF wird verarbeitet...';
        startPolling();

    } catch (error) {
        showError(error.message);
    }
}

// Job-Status abfragen
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
                progressText.textContent = 'Warte auf Verarbeitung...';
                progressBar.style.width = '33%';
                break;

            case 'processing':
                progressText.textContent = 'PDF wird analysiert...';
                progressBar.style.width = '66%';
                break;

            case 'completed':
                stopPolling();
                showResult(job);
                break;

            case 'failed':
                stopPolling();
                showError(job.error_message || 'Verarbeitung fehlgeschlagen');
                break;
        }

    } catch (error) {
        stopPolling();
        showError(error.message);
    }
}

// Polling starten/stoppen
function startPolling() {
    pollInterval = setInterval(checkJobStatus, 2000); // Alle 2 Sekunden
    checkJobStatus(); // Erste Abfrage sofort
}

function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

// Ergebnis anzeigen
function showResult(job) {
    uploadSection.style.display = 'none';
    progressSection.style.display = 'none';
    errorSection.style.display = 'none';
    resultSection.style.display = 'block';

    const bank = job.bank || 'unbekannte Bank';
    resultText.textContent = `Kontoauszug erfolgreich konvertiert! (${bank})`;

    downloadBtn.href = `${API_BASE}/api/download/${currentJobId}`;
    downloadBtn.download = `kontoauszug_${currentJobId.slice(0, 8)}.${job.output_format}`;
}

// Fehler anzeigen
function showError(message) {
    uploadSection.style.display = 'none';
    progressSection.style.display = 'none';
    resultSection.style.display = 'none';
    errorSection.style.display = 'block';

    errorText.textContent = message;
}

// Progress anzeigen
function showProgress() {
    uploadSection.style.display = 'none';
    errorSection.style.display = 'none';
    resultSection.style.display = 'none';
    progressSection.style.display = 'block';

    progressBar.style.width = '10%';
    progressText.textContent = 'Upload läuft...';
}

// Daten löschen
async function handleDelete() {
    if (!currentJobId) return;

    try {
        const response = await fetch(`${API_BASE}/api/download/${currentJobId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            alert('✅ Alle Daten wurden erfolgreich gelöscht.');
            resetUI();
        }

    } catch (error) {
        alert('Fehler beim Löschen: ' + error.message);
    }
}

// UI zurücksetzen
function resetUI() {
    uploadSection.style.display = 'block';
    progressSection.style.display = 'none';
    resultSection.style.display = 'none';
    errorSection.style.display = 'none';

    selectedFile = null;
    currentJobId = null;
    fileInput.value = '';
    dropzone.querySelector('p').textContent = 'Datei hier ablegen oder klicken zum Auswählen';
    uploadBtn.disabled = true;

    stopPolling();
}
