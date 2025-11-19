// SeaRei Browser Extension - Popup Script

const API_URL = 'http://localhost:8001';
let stats = { scanned: 0, flagged: 0 };

// Load stats from storage
chrome.storage.local.get(['stats'], (result) => {
    if (result.stats) {
        stats = result.stats;
        updateStatsDisplay();
    }
});

// Load auto-scan preference
chrome.storage.local.get(['autoScan'], (result) => {
    document.getElementById('autoScan').checked = result.autoScan || false;
});

// Save auto-scan preference
document.getElementById('autoScan').addEventListener('change', (e) => {
    chrome.storage.local.set({ autoScan: e.target.checked });
});

// Scan button click
document.getElementById('scanBtn').addEventListener('click', async () => {
    const btn = document.getElementById('scanBtn');
    const resultDiv = document.getElementById('result');
    
    btn.disabled = true;
    btn.textContent = '⏳ Scanning...';
    resultDiv.innerHTML = '';
    
    try {
        // Get current tab
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        
        // Execute content script to get page text
        const [result] = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            function: getPageText
        });
        
        const pageText = result.result;
        
        if (!pageText || pageText.length < 10) {
            resultDiv.innerHTML = '<div class="result safe">✅ No significant text found on page</div>';
            return;
        }
        
        // Call SeaRei API
        const response = await fetch(`${API_URL}/score`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: pageText.substring(0, 5000) }) // Limit to 5000 chars
        });
        
        const data = await response.json();
        
        // Update stats
        stats.scanned++;
        if (data.prediction === 'flag') {
            stats.flagged++;
        }
        chrome.storage.local.set({ stats });
        updateStatsDisplay();
        
        // Display result
        if (data.prediction === 'flag') {
            resultDiv.innerHTML = `
                <div class="result unsafe">
                    <strong>⚠️ Unsafe Content Detected</strong><br>
                    Score: ${(data.score * 100).toFixed(1)}%<br>
                    Method: ${data.method || 'ensemble'}
                </div>
            `;
        } else {
            resultDiv.innerHTML = `
                <div class="result safe">
                    <strong>✅ Content appears safe</strong><br>
                    Confidence: ${(100 - data.score * 100).toFixed(1)}%<br>
                    Latency: ${data.latency_ms || 'N/A'}ms
                </div>
            `;
        }
    } catch (error) {
        resultDiv.innerHTML = `
            <div class="result unsafe">
                <strong>❌ Error</strong><br>
                ${error.message}<br>
                <small>Make sure SeaRei API is running at ${API_URL}</small>
            </div>
        `;
    } finally {
        btn.disabled = false;
        btn.textContent = '🔍 Scan Current Page';
    }
});

// Settings link
document.getElementById('settingsLink').addEventListener('click', (e) => {
    e.preventDefault();
    chrome.runtime.openOptionsPage();
});

// Function to extract text from page
function getPageText() {
    // Get all visible text from the page
    const text = document.body.innerText || document.body.textContent;
    return text.trim();
}

// Update stats display
function updateStatsDisplay() {
    document.getElementById('scannedCount').textContent = stats.scanned;
    document.getElementById('flaggedCount').textContent = stats.flagged;
}
