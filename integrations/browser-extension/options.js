// SeaRei Browser Extension - Options/Settings Script

// Load saved settings
document.addEventListener('DOMContentLoaded', async () => {
    const settings = await chrome.storage.local.get([
        'apiUrl',
        'autoScan',
        'showNotifications',
        'highlightContent'
    ]);
    
    document.getElementById('apiUrl').value = settings.apiUrl || 'http://localhost:8001';
    document.getElementById('autoScan').checked = settings.autoScan || false;
    document.getElementById('showNotifications').checked = settings.showNotifications !== false; // Default true
    document.getElementById('highlightContent').checked = settings.highlightContent || false;
});

// Save settings
document.getElementById('saveBtn').addEventListener('click', async () => {
    const apiUrl = document.getElementById('apiUrl').value.trim();
    const autoScan = document.getElementById('autoScan').checked;
    const showNotifications = document.getElementById('showNotifications').checked;
    const highlightContent = document.getElementById('highlightContent').checked;
    
    // Validate API URL
    if (!apiUrl) {
        showStatus('Please enter an API URL', 'error');
        return;
    }
    
    // Save to storage
    await chrome.storage.local.set({
        apiUrl,
        autoScan,
        showNotifications,
        highlightContent
    });
    
    showStatus('✅ Settings saved successfully!', 'success');
});

// Show status message
function showStatus(message, type) {
    const statusDiv = document.getElementById('status');
    statusDiv.textContent = message;
    statusDiv.className = `status ${type}`;
    
    if (type === 'success') {
        setTimeout(() => {
            statusDiv.className = 'status';
        }, 3000);
    }
}

// Test API connection
async function testApiConnection(url) {
    try {
        const response = await fetch(`${url}/healthz`);
        return response.ok;
    } catch (error) {
        return false;
    }
}

// Add real-time API URL validation
document.getElementById('apiUrl').addEventListener('blur', async (e) => {
    const url = e.target.value.trim();
    if (url) {
        const isConnected = await testApiConnection(url);
        if (isConnected) {
            e.target.style.borderColor = '#22c55e';
        } else {
            e.target.style.borderColor = '#ef4444';
            showStatus('⚠️ Cannot connect to API. Make sure it\'s running.', 'error');
        }
    }
});












