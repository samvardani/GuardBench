// SeaRei Browser Extension - Background Service Worker

console.log('SeaRei Safety Scanner: Background service worker initialized');

// Extension installation
chrome.runtime.onInstalled.addListener(() => {
    console.log('SeaRei Safety Scanner installed');
    
    // Set default settings
    chrome.storage.local.set({
        apiUrl: 'http://localhost:8001',
        autoScan: false,
        stats: { scanned: 0, flagged: 0 }
    });
    
    // Create context menu
    chrome.contextMenus.create({
        id: 'searei-scan-selection',
        title: 'Scan with SeaRei',
        contexts: ['selection']
    });
});

// Context menu click handler
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
    if (info.menuItemId === 'searei-scan-selection' && info.selectionText) {
        await scanText(info.selectionText, tab.id);
    }
});

// Scan text function
async function scanText(text, tabId) {
    try {
        // Get API URL from storage
        const config = await chrome.storage.local.get(['apiUrl']);
        const apiUrl = config.apiUrl || 'http://localhost:8001';
        
        // Call SeaRei API
        const response = await fetch(`${apiUrl}/score`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text.substring(0, 5000) })
        });
        
        const data = await response.json();
        
        // Update stats
        const stats = await chrome.storage.local.get(['stats']);
        const currentStats = stats.stats || { scanned: 0, flagged: 0 };
        currentStats.scanned++;
        if (data.prediction === 'flag') {
            currentStats.flagged++;
        }
        chrome.storage.local.set({ stats: currentStats });
        
        // Show notification
        const notificationOptions = {
            type: 'basic',
            iconUrl: 'icons/icon128.png',
            title: data.prediction === 'flag' ? '⚠️ Unsafe Content' : '✅ Content Safe',
            message: data.prediction === 'flag' 
                ? `Risk Score: ${(data.score * 100).toFixed(1)}%` 
                : `Confidence: ${(100 - data.score * 100).toFixed(1)}%`,
            priority: data.prediction === 'flag' ? 2 : 0
        };
        
        chrome.notifications.create('searei-scan-result', notificationOptions);
        
    } catch (error) {
        console.error('SeaRei scan error:', error);
        if (chrome.notifications && chrome.notifications.create) {
            chrome.notifications.create('searei-error', {
                type: 'basic',
                iconUrl: 'icons/icon128.png',
                title: '❌ Scan Error',
                message: 'Make sure SeaRei API is running (check Options for API URL)'
            });
        }
    }
}

// Message handler for communication with popup/content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request && request.action === 'scanText') {
        const tabId = sender && sender.tab ? sender.tab.id : undefined;
        scanText(request.text, tabId).then(() => {
            sendResponse({ success: true });
        });
        return true; // Keep message channel open
    }
});

// Keyboard shortcut handler (if defined in manifest)
if (chrome.commands && chrome.commands.onCommand) {
    chrome.commands.onCommand.addListener((command) => {
        if (command === 'scan-page') {
            chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
                const tab = tabs && tabs.length ? tabs[0] : undefined;
                if (tab && tab.id) {
                    chrome.tabs.sendMessage(tab.id, { action: 'getPageText' }, (response) => {
                        if (response && response.text) {
                            scanText(response.text, tab.id);
                        }
                    });
                }
            });
        }
    });
}

