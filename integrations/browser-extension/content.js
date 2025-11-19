// SeaRei Browser Extension - Content Script
// Runs on all web pages to enable real-time scanning

console.log('SeaRei Safety Scanner: Content script loaded');

// Listen for messages from popup or background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'getPageText') {
        // Extract all visible text from the page
        const pageText = document.body.innerText || document.body.textContent;
        sendResponse({ text: pageText.trim() });
    }
    
    if (request.action === 'highlightUnsafe') {
        // Optional: Highlight unsafe content on the page
        highlightUnsafeContent(request.patterns);
        sendResponse({ success: true });
    }
    
    return true; // Keep message channel open for async response
});

// Optional: Auto-scan on page load if enabled
chrome.storage.local.get(['autoScan'], (result) => {
    if (result.autoScan) {
        setTimeout(() => {
            scanCurrentPage();
        }, 1000); // Wait 1 second for page to fully load
    }
});

// Function to scan current page
async function scanCurrentPage() {
    const pageText = document.body.innerText || document.body.textContent;
    
    if (!pageText || pageText.length < 10) {
        return;
    }
    
    try {
        // Get API URL from storage
        const config = await chrome.storage.local.get(['apiUrl']);
        const apiUrl = config.apiUrl || 'http://localhost:8001';
        
        // Call SeaRei API
        const response = await fetch(`${apiUrl}/score`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: pageText.substring(0, 5000) })
        });
        
        const data = await response.json();
        
        // Show notification if unsafe content detected
        if (data.prediction === 'flag') {
            showNotification('⚠️ Unsafe content detected on this page', data.score);
        }
    } catch (error) {
        console.error('SeaRei scan error:', error);
    }
}

// Show in-page notification
function showNotification(message, score) {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
        padding: 16px 24px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 999999;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-size: 14px;
        font-weight: 600;
        animation: slideIn 0.3s ease;
    `;
    notification.innerHTML = `
        <div>${message}</div>
        <div style="font-size: 12px; margin-top: 4px; opacity: 0.9;">
            Risk Score: ${(score * 100).toFixed(1)}%
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// Optional: Highlight unsafe patterns (for advanced users)
function highlightUnsafeContent(patterns) {
    if (!patterns || patterns.length === 0) return;
    
    const walker = document.createTreeWalker(
        document.body,
        NodeFilter.SHOW_TEXT,
        null,
        false
    );
    
    const textNodes = [];
    while (walker.nextNode()) {
        textNodes.push(walker.currentNode);
    }
    
    textNodes.forEach(node => {
        patterns.forEach(pattern => {
            const regex = new RegExp(pattern, 'gi');
            if (regex.test(node.textContent)) {
                const span = document.createElement('span');
                span.style.cssText = 'background-color: rgba(239, 68, 68, 0.3); border-bottom: 2px solid #ef4444;';
                span.textContent = node.textContent;
                node.parentNode.replaceChild(span, node);
            }
        });
    });
}

// Add CSS animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(400px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(400px); opacity: 0; }
    }
`;
document.head.appendChild(style);












