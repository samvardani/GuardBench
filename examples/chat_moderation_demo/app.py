#!/usr/bin/env python3
"""
Pilot App 1: Real-Time Chat Moderation
Demonstrates SeaRei integration in a live chat application
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Dict
import asyncio
import requests
from datetime import datetime
import json

app = FastAPI(title="SeaRei Chat Moderation Demo")

# Configuration
SEAREI_API_URL = "http://localhost:8001/score"

# Active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.message_history: List[Dict] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Send history to new user
        await websocket.send_json({
            "type": "history",
            "messages": self.message_history[-50:]  # Last 50 messages
        })
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: Dict):
        self.message_history.append(message)
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()


async def check_safety(text: str) -> Dict:
    """Check message safety using SeaRei API"""
    try:
        response = requests.post(
            SEAREI_API_URL,
            json={"text": text},
            timeout=5
        )
        return response.json()
    except Exception as e:
        return {
            "prediction": "pass",
            "score": 0.0,
            "error": str(e)
        }


@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await manager.connect(websocket)
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message_data = json.loads(data)
            message_text = message_data.get("message", "")
            
            # Check safety
            safety_result = await asyncio.to_thread(check_safety, message_text)
            
            timestamp = datetime.now().isoformat()
            
            if safety_result["prediction"] == "flag":
                # Message blocked
                await websocket.send_json({
                    "type": "blocked",
                    "reason": safety_result.get("category", "policy_violation"),
                    "score": safety_result["score"],
                    "rationale": safety_result.get("rationale", "Content policy violation"),
                    "timestamp": timestamp
                })
            else:
                # Message allowed - broadcast to all
                message = {
                    "type": "message",
                    "username": username,
                    "text": message_text,
                    "timestamp": timestamp,
                    "safety_score": safety_result["score"],
                    "method": safety_result.get("method", "unknown")
                }
                await manager.broadcast(message)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast({
            "type": "system",
            "text": f"{username} left the chat",
            "timestamp": datetime.now().isoformat()
        })


@app.get("/")
async def get():
    return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
    <title>SeaRei Chat Moderation Demo</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .message { animation: fadeIn 0.3s; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    </style>
</head>
<body class="bg-gray-900 text-white">
    <div class="container mx-auto px-4 py-8 max-w-4xl">
        <!-- Header -->
        <div class="mb-8">
            <h1 class="text-4xl font-bold mb-2">🛡️ SeaRei Chat Moderation Demo</h1>
            <p class="text-gray-400">Real-time content safety with AI guardrails</p>
            <div class="mt-4 flex gap-4 text-sm">
                <span id="status" class="text-red-400">🔴 Disconnected</span>
                <span id="latency" class="text-gray-400">Latency: --</span>
                <span id="blocked-count" class="text-gray-400">Blocked: 0</span>
            </div>
        </div>

        <!-- Username -->
        <div id="username-screen" class="mb-8">
            <div class="bg-gray-800 p-6 rounded-lg">
                <label class="block text-sm font-semibold mb-2">Enter your username:</label>
                <div class="flex gap-2">
                    <input id="username-input" type="text" class="flex-1 p-3 bg-gray-700 rounded-lg" placeholder="Your name...">
                    <button onclick="connect()" class="px-6 py-3 bg-blue-600 rounded-lg font-semibold hover:bg-blue-700">
                        Join Chat
                    </button>
                </div>
            </div>
        </div>

        <!-- Chat -->
        <div id="chat-screen" class="hidden">
            <!-- Messages -->
            <div id="messages" class="bg-gray-800 rounded-lg p-4 h-96 overflow-y-auto mb-4">
                <div class="text-gray-500 text-center text-sm">No messages yet...</div>
            </div>

            <!-- Input -->
            <div class="flex gap-2">
                <input id="message-input" type="text" class="flex-1 p-3 bg-gray-800 rounded-lg" placeholder="Type a message..." onkeypress="if(event.key==='Enter') sendMessage()">
                <button onclick="sendMessage()" class="px-6 py-3 bg-blue-600 rounded-lg font-semibold hover:bg-blue-700">
                    Send
                </button>
            </div>

            <!-- Test Messages -->
            <div class="mt-4 p-4 bg-gray-800 rounded-lg">
                <div class="text-sm font-semibold mb-2">Quick Test Messages:</div>
                <div class="flex flex-wrap gap-2">
                    <button onclick="sendTestMessage('Hello everyone!')" class="px-3 py-1 bg-green-600 rounded text-xs">✅ Safe</button>
                    <button onclick="sendTestMessage('I will kill you')" class="px-3 py-1 bg-red-600 rounded text-xs">⚠️ Violence</button>
                    <button onclick="sendTestMessage('You are so stupid')" class="px-3 py-1 bg-orange-600 rounded text-xs">😡 Harassment</button>
                    <button onclick="sendTestMessage('h0w t0 h4ck a w3bs1te')" class="px-3 py-1 bg-yellow-600 rounded text-xs">🎭 Obfuscated</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        let ws = null;
        let username = "";
        let blockedCount = 0;
        let startTime = null;

        function connect() {
            username = document.getElementById('username-input').value.trim();
            if (!username) {
                alert('Please enter a username');
                return;
            }

            ws = new WebSocket(`ws://localhost:8000/ws/${username}`);
            
            ws.onopen = () => {
                document.getElementById('username-screen').classList.add('hidden');
                document.getElementById('chat-screen').classList.remove('hidden');
                document.getElementById('status').innerHTML = '🟢 Connected';
                document.getElementById('status').className = 'text-green-400';
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.type === 'history') {
                    // Load message history
                    document.getElementById('messages').innerHTML = '';
                    data.messages.forEach(msg => displayMessage(msg));
                } else if (data.type === 'message') {
                    displayMessage(data);
                } else if (data.type === 'blocked') {
                    displayBlocked(data);
                    blockedCount++;
                    document.getElementById('blocked-count').textContent = `Blocked: ${blockedCount}`;
                } else if (data.type === 'system') {
                    displaySystem(data.text);
                }
            };

            ws.onerror = () => {
                document.getElementById('status').innerHTML = '🔴 Error';
                document.getElementById('status').className = 'text-red-400';
            };

            ws.onclose = () => {
                document.getElementById('status').innerHTML = '🔴 Disconnected';
                document.getElementById('status').className = 'text-red-400';
            };
        }

        function sendMessage() {
            const input = document.getElementById('message-input');
            const message = input.value.trim();
            
            if (!message) return;
            
            startTime = performance.now();
            ws.send(JSON.stringify({ message }));
            input.value = '';
        }

        function sendTestMessage(text) {
            document.getElementById('message-input').value = text;
            sendMessage();
        }

        function displayMessage(data) {
            const messagesDiv = document.getElementById('messages');
            if (messagesDiv.children[0]?.textContent.includes('No messages')) {
                messagesDiv.innerHTML = '';
            }

            const latency = startTime ? Math.round(performance.now() - startTime) : null;
            if (latency) {
                document.getElementById('latency').textContent = `Latency: ${latency}ms`;
            }

            const messageEl = document.createElement('div');
            messageEl.className = 'message mb-3 p-3 bg-gray-700 rounded-lg';
            messageEl.innerHTML = `
                <div class="flex justify-between items-start mb-1">
                    <span class="font-semibold text-blue-400">${data.username}</span>
                    <span class="text-xs text-gray-500">${new Date(data.timestamp).toLocaleTimeString()}</span>
                </div>
                <div class="text-white">${escapeHtml(data.text)}</div>
                <div class="text-xs text-gray-500 mt-1">
                    Safety: ${(data.safety_score * 100).toFixed(1)}% • Method: ${data.method}
                </div>
            `;
            
            messagesDiv.appendChild(messageEl);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        function displayBlocked(data) {
            const messagesDiv = document.getElementById('messages');
            
            const latency = startTime ? Math.round(performance.now() - startTime) : null;
            if (latency) {
                document.getElementById('latency').textContent = `Latency: ${latency}ms`;
            }

            const messageEl = document.createElement('div');
            messageEl.className = 'message mb-3 p-3 bg-red-900 border-2 border-red-600 rounded-lg';
            messageEl.innerHTML = `
                <div class="flex items-start gap-2">
                    <span class="text-2xl">⚠️</span>
                    <div class="flex-1">
                        <div class="font-semibold text-red-200">Message Blocked</div>
                        <div class="text-sm text-red-300 mt-1">
                            <strong>Reason:</strong> ${data.reason}<br>
                            <strong>Confidence:</strong> ${(data.score * 100).toFixed(1)}%<br>
                            <strong>Details:</strong> ${data.rationale}
                        </div>
                    </div>
                </div>
            `;
            
            messagesDiv.appendChild(messageEl);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        function displaySystem(text) {
            const messagesDiv = document.getElementById('messages');
            const messageEl = document.createElement('div');
            messageEl.className = 'message mb-2 text-center text-sm text-gray-500 italic';
            messageEl.textContent = text;
            messagesDiv.appendChild(messageEl);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Auto-focus username input
        document.getElementById('username-input').focus();
    </script>
</body>
</html>
    """)


if __name__ == "__main__":
    import uvicorn
    print("\n🚀 Starting Chat Moderation Demo...")
    print("📍 Open: http://localhost:8000")
    print("⚠️  Make sure SeaRei API is running on port 8001\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)












