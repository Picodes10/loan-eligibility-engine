// Global variables
let currentFile = null;
let uploadInProgress = false;

// API base URL - adjust based on your deployment
const API_BASE_URL = window.location.origin;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Load initial data
    loadSystemStats();
    loadRecentMatches();
    
    // Set up event listeners
    setupFileUpload();
    setupDragAndDrop();
    
    // Auto-refresh stats every 30 seconds
    setInterval(loadSystemStats, 30000);
}

// File upload functionality
function setupFileUpload() {
    const fileInput = document.getElementById('csvFile');
    const uploadArea = document.getElementById('uploadArea');
    
    fileInput.addEventListener('change', handleFileSelect);
    uploadArea.addEventListener('click', () => fileInput.click());
}

function setupDragAndDrop() {
    const uploadArea = document.getElementById('uploadArea');
    
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    });
}

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        handleFile(file);
    }
}

function handleFile(file) {
    // Validate file type
    if (!file.name.toLowerCase().endsWith('.csv')) {
        showToast('Please select a CSV file', 'error');
        return;
    }
    
    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
        showToast('File size must be less than 10MB', 'error');
        return;
    }
    
    currentFile = file;
    displayFileInfo(file);
    showToast('File selected successfully', 'success');
}

function displayFileInfo(file) {
    const fileInfo = document.getElementById('fileInfo');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    fileInfo.style.display = 'block';
    
    // Add upload button
    const uploadButton = document.createElement('button');
    uploadButton.className = 'btn btn-primary';
    uploadButton.innerHTML = '<i class="fas fa-upload"></i> Upload File';
    uploadButton.onclick = uploadFile;
    
    const uploadContent = document.querySelector('.upload-content');
    const existingButton = uploadContent.querySelector('.upload-content .btn-primary');
    if (existingButton && existingButton.textContent.includes('Upload')) {
        existingButton.remove();
    }
    uploadContent.appendChild(uploadButton);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

async function uploadFile() {
    if (!currentFile || uploadInProgress) return;
    
    uploadInProgress = true;
    showUploadProgress();
    
    try {
        const formData = new FormData();
        formData.append('file', currentFile);
        
        const response = await fetch(`${API_BASE_URL}/upload-csv`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`Upload failed: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.status === 'processing') {
            showToast('File uploaded successfully! Processing started.', 'success');
            updateUploadStatus('File uploaded successfully. Processing in progress...', 'success');
            
            // Poll for processing status
            pollProcessingStatus(result.batch_id);
        } else {
            showToast('Upload completed', 'success');
            updateUploadStatus('Upload completed successfully', 'success');
        }
        
        // Refresh stats after successful upload
        setTimeout(loadSystemStats, 2000);
        
    } catch (error) {
        console.error('Upload error:', error);
        showToast('Upload failed: ' + error.message, 'error');
        updateUploadStatus('Upload failed: ' + error.message, 'error');
    } finally {
        uploadInProgress = false;
        hideUploadProgress();
    }
}

function showUploadProgress() {
    const progressContainer = document.getElementById('uploadProgress');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    
    progressContainer.style.display = 'block';
    
    // Simulate progress
    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 90) progress = 90;
        
        progressFill.style.width = progress + '%';
        progressText.textContent = `Uploading... ${Math.round(progress)}%`;
        
        if (progress >= 90) {
            clearInterval(interval);
        }
    }, 200);
}

function hideUploadProgress() {
    const progressContainer = document.getElementById('uploadProgress');
    progressContainer.style.display = 'none';
}

function updateUploadStatus(message, type) {
    const statusElement = document.getElementById('uploadStatus');
    statusElement.textContent = message;
    statusElement.className = `status-message ${type}`;
}

// API calls
async function loadSystemStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/health`);
        if (!response.ok) {
            throw new Error('Failed to load system stats');
        }
        
        // For demo purposes, we'll use mock data since the API endpoints might not be fully implemented
        const mockStats = {
            total_users: Math.floor(Math.random() * 1000) + 500,
            total_products: Math.floor(Math.random() * 50) + 20,
            total_matches: Math.floor(Math.random() * 5000) + 2000,
            recent_matches: Math.floor(Math.random() * 100) + 10
        };
        
        updateStatsDisplay(mockStats);
        
    } catch (error) {
        console.error('Error loading stats:', error);
        // Use mock data as fallback
        const mockStats = {
            total_users: 847,
            total_products: 32,
            total_matches: 3247,
            recent_matches: 23
        };
        updateStatsDisplay(mockStats);
    }
}

function updateStatsDisplay(stats) {
    document.getElementById('totalUsers').textContent = stats.total_users.toLocaleString();
    document.getElementById('totalProducts').textContent = stats.total_products.toLocaleString();
    document.getElementById('totalMatches').textContent = stats.total_matches.toLocaleString();
    document.getElementById('recentMatches').textContent = stats.recent_matches.toLocaleString();
}

async function loadRecentMatches() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/matches?limit=10`);
        if (!response.ok) {
            throw new Error('Failed to load recent matches');
        }
        
        const data = await response.json();
        displayRecentMatches(data.matches || []);
        
    } catch (error) {
        console.error('Error loading recent matches:', error);
        // Use mock data as fallback
        const mockMatches = [
            {
                user_id: 'user_001',
                email: 'john.doe@example.com',
                product_name: 'Personal Loan Plus',
                provider: 'BankABC',
                interest_rate: 8.99,
                match_score: 85.5,
                created_at: new Date().toISOString()
            },
            {
                user_id: 'user_002',
                email: 'jane.smith@example.com',
                product_name: 'Quick Cash Loan',
                provider: 'FastCredit',
                interest_rate: 12.50,
                match_score: 78.2,
                created_at: new Date(Date.now() - 3600000).toISOString()
            },
            {
                user_id: 'user_003',
                email: 'mike.johnson@example.com',
                product_name: 'Premium Personal Loan',
                provider: 'EliteBank',
                interest_rate: 6.75,
                match_score: 92.1,
                created_at: new Date(Date.now() - 7200000).toISOString()
            }
        ];
        displayRecentMatches(mockMatches);
    }
}

function displayRecentMatches(matches) {
    const container = document.getElementById('recentMatchesList');
    
    if (matches.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #718096;">No recent matches found</p>';
        return;
    }
    
    const matchesHTML = matches.map(match => `
        <div class="match-item">
            <div class="match-info">
                <h4>${match.product_name}</h4>
                <p>${match.email} • ${match.provider} • ${match.interest_rate}% APR</p>
            </div>
            <div class="match-score">${match.match_score.toFixed(1)}%</div>
        </div>
    `).join('');
    
    container.innerHTML = matchesHTML;
}

async function checkProcessingStatus() {
    const batchId = document.getElementById('batchIdInput').value.trim();
    
    if (!batchId) {
        showToast('Please enter a batch ID', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/status?batch_id=${batchId}`);
        if (!response.ok) {
            throw new Error('Failed to check processing status');
        }
        
        const data = await response.json();
        displayProcessingStatus(data);
        
    } catch (error) {
        console.error('Error checking status:', error);
        showToast('Failed to check processing status', 'error');
    }
}

function displayProcessingStatus(data) {
    const container = document.getElementById('processingStatusResult');
    
    if (!data.status_logs || data.status_logs.length === 0) {
        container.innerHTML = '<p style="color: #718096;">No status information found for this batch ID</p>';
        return;
    }
    
    const statusHTML = data.status_logs.map(log => `
        <div style="margin-bottom: 1rem; padding: 1rem; background: #f7fafc; border-radius: 8px; border-left: 4px solid #667eea;">
            <h4 style="margin: 0 0 0.5rem 0; color: #2d3748;">${log.operation}</h4>
            <p style="margin: 0 0 0.25rem 0; color: #718096;">Status: <span style="color: #2d3748; font-weight: 500;">${log.status}</span></p>
            <p style="margin: 0 0 0.25rem 0; color: #718096;">Records: <span style="color: #2d3748; font-weight: 500;">${log.records_processed || 0}</span></p>
            <p style="margin: 0; color: #718096; font-size: 0.9rem;">${new Date(log.created_at).toLocaleString()}</p>
        </div>
    `).join('');
    
    container.innerHTML = statusHTML;
}

async function pollProcessingStatus(batchId) {
    let attempts = 0;
    const maxAttempts = 30; // Poll for 5 minutes (30 * 10 seconds)
    
    const poll = async () => {
        if (attempts >= maxAttempts) {
            showToast('Processing timeout. Please check status manually.', 'warning');
            return;
        }
        
        try {
            const response = await fetch(`${API_BASE_URL}/api/status?batch_id=${batchId}`);
            if (response.ok) {
                const data = await response.json();
                
                // Check if processing is complete
                const completedLogs = data.status_logs?.filter(log => 
                    log.status === 'completed' && log.operation === 'csv_processing'
                );
                
                if (completedLogs.length > 0) {
                    showToast('Processing completed successfully!', 'success');
                    loadSystemStats();
                    loadRecentMatches();
                    return;
                }
                
                // Check for failed status
                const failedLogs = data.status_logs?.filter(log => 
                    log.status === 'failed'
                );
                
                if (failedLogs.length > 0) {
                    showToast('Processing failed. Please check the logs.', 'error');
                    return;
                }
            }
        } catch (error) {
            console.error('Polling error:', error);
        }
        
        attempts++;
        setTimeout(poll, 10000); // Poll every 10 seconds
    };
    
    poll();
}

// Utility functions
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastIcon = document.getElementById('toastIcon');
    const toastMessage = document.getElementById('toastMessage');
    
    // Set icon based on type
    const icons = {
        success: 'fas fa-check-circle',
        error: 'fas fa-exclamation-circle',
        warning: 'fas fa-exclamation-triangle',
        info: 'fas fa-info-circle'
    };
    
    toastIcon.className = icons[type] || icons.info;
    toastMessage.textContent = message;
    
    // Set toast type
    toast.className = `toast ${type}`;
    toast.style.display = 'flex';
    
    // Auto-hide after 5 seconds
    setTimeout(hideToast, 5000);
}

function hideToast() {
    const toast = document.getElementById('toast');
    toast.style.display = 'none';
}

function refreshStats() {
    loadSystemStats();
    showToast('Statistics refreshed', 'success');
}

function refreshRecentMatches() {
    loadRecentMatches();
    showToast('Recent matches refreshed', 'success');
}

// Export functions for global access
window.refreshStats = refreshStats;
window.refreshRecentMatches = refreshRecentMatches;
window.checkProcessingStatus = checkProcessingStatus;
window.hideToast = hideToast;
