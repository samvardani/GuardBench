#!/usr/bin/env python3
"""
Pilot App 2: Comment Filter with Moderation Queue
Demonstrates batch processing and moderation workflow
"""

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import List, Dict, Optional
import requests
from datetime import datetime
import json
from pathlib import Path

app = FastAPI(title="SeaRei Comment Filter Demo")

# Configuration
SEAREI_API_URL = "http://localhost:8001"
DB_FILE = Path(__file__).parent / "comments.json"

# In-memory database (would be SQL in production)
class CommentDB:
    def __init__(self):
        self.load()
    
    def load(self):
        if DB_FILE.exists():
            with open(DB_FILE, 'r') as f:
                self.comments = json.load(f)
        else:
            self.comments = []
    
    def save(self):
        with open(DB_FILE, 'w') as f:
            json.dump(self.comments, f, indent=2)
    
    def add(self, comment: Dict):
        comment['id'] = len(self.comments) + 1
        comment['created_at'] = datetime.now().isoformat()
        self.comments.append(comment)
        self.save()
    
    def get_all(self):
        return sorted(self.comments, key=lambda x: x['created_at'], reverse=True)
    
    def get_pending(self):
        return [c for c in self.comments if c['status'] == 'pending']
    
    def get_by_id(self, comment_id: int):
        return next((c for c in self.comments if c['id'] == comment_id), None)
    
    def update_status(self, comment_id: int, status: str, moderator_note: str = ""):
        comment = self.get_by_id(comment_id)
        if comment:
            comment['status'] = status
            comment['moderator_note'] = moderator_note
            comment['reviewed_at'] = datetime.now().isoformat()
            self.save()
    
    def get_stats(self):
        total = len(self.comments)
        approved = sum(1 for c in self.comments if c['status'] == 'approved')
        rejected = sum(1 for c in self.comments if c['status'] == 'rejected')
        pending = sum(1 for c in self.comments if c['status'] == 'pending')
        auto_approved = sum(1 for c in self.comments if c.get('auto_approved', False))
        
        return {
            'total': total,
            'approved': approved,
            'rejected': rejected,
            'pending': pending,
            'auto_approved': auto_approved,
            'auto_approval_rate': (auto_approved / total * 100) if total > 0 else 0
        }

db = CommentDB()


def check_safety(text: str) -> Dict:
    """Check comment safety using SeaRei API"""
    try:
        response = requests.post(
            f"{SEAREI_API_URL}/score",
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


@app.get("/", response_class=HTMLResponse)
async def index():
    """Main page"""
    stats = db.get_stats()
    return HTMLResponse(f"""
<!DOCTYPE html>
<html>
<head>
    <title>SeaRei Comment Filter Demo</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50">
    <div class="container mx-auto px-4 py-8 max-w-6xl">
        <!-- Header -->
        <div class="mb-8">
            <h1 class="text-4xl font-bold text-gray-800 mb-2">🛡️ SeaRei Comment Filter Demo</h1>
            <p class="text-gray-600">Automated moderation with human-in-the-loop workflow</p>
        </div>

        <!-- Stats Dashboard -->
        <div class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
            <div class="bg-white p-4 rounded-lg shadow">
                <div class="text-2xl font-bold text-gray-800">{stats['total']}</div>
                <div class="text-sm text-gray-600">Total Comments</div>
            </div>
            <div class="bg-green-50 p-4 rounded-lg shadow">
                <div class="text-2xl font-bold text-green-700">{stats['approved']}</div>
                <div class="text-sm text-gray-600">Approved</div>
            </div>
            <div class="bg-red-50 p-4 rounded-lg shadow">
                <div class="text-2xl font-bold text-red-700">{stats['rejected']}</div>
                <div class="text-sm text-gray-600">Rejected</div>
            </div>
            <div class="bg-yellow-50 p-4 rounded-lg shadow">
                <div class="text-2xl font-bold text-yellow-700">{stats['pending']}</div>
                <div class="text-sm text-gray-600">Pending Review</div>
            </div>
            <div class="bg-blue-50 p-4 rounded-lg shadow">
                <div class="text-2xl font-bold text-blue-700">{stats['auto_approval_rate']:.1f}%</div>
                <div class="text-sm text-gray-600">Auto-Approval</div>
            </div>
        </div>

        <!-- Navigation -->
        <div class="flex gap-4 mb-8">
            <a href="/" class="px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold">Submit Comment</a>
            <a href="/moderation" class="px-6 py-3 bg-gray-700 text-white rounded-lg font-semibold">Moderation Queue</a>
            <a href="/approved" class="px-6 py-3 bg-green-600 text-white rounded-lg font-semibold">Approved Comments</a>
        </div>

        <!-- Comment Submission Form -->
        <div class="bg-white p-8 rounded-lg shadow-lg">
            <h2 class="text-2xl font-bold text-gray-800 mb-4">Submit a Comment</h2>
            <form method="POST" action="/submit">
                <div class="mb-4">
                    <label class="block text-sm font-semibold text-gray-700 mb-2">Name:</label>
                    <input type="text" name="author" required 
                           class="w-full p-3 border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none"
                           placeholder="Your name...">
                </div>
                <div class="mb-4">
                    <label class="block text-sm font-semibold text-gray-700 mb-2">Comment:</label>
                    <textarea name="text" required rows="4"
                              class="w-full p-3 border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none"
                              placeholder="Share your thoughts..."></textarea>
                </div>
                <button type="submit" 
                        class="px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700">
                    Post Comment
                </button>
            </form>

            <!-- Test Buttons -->
            <div class="mt-6 pt-6 border-t border-gray-200">
                <div class="text-sm font-semibold text-gray-700 mb-3">Quick Test Comments:</div>
                <div class="grid grid-cols-2 gap-2">
                    <button onclick="fillForm('Alice', 'Great article! Thanks for sharing.')" 
                            class="px-4 py-2 bg-green-100 text-green-700 rounded text-sm hover:bg-green-200">
                        ✅ Safe Comment
                    </button>
                    <button onclick="fillForm('Bob', 'I will kill you for this')" 
                            class="px-4 py-2 bg-red-100 text-red-700 rounded text-sm hover:bg-red-200">
                        ⚠️ Violent Threat
                    </button>
                    <button onclick="fillForm('Charlie', 'You are so stupid and worthless')" 
                            class="px-4 py-2 bg-orange-100 text-orange-700 rounded text-sm hover:bg-orange-200">
                        😡 Harassment
                    </button>
                    <button onclick="fillForm('Dave', 'This is m0d3r4t3ly 0k4y c0nt3nt')" 
                            class="px-4 py-2 bg-yellow-100 text-yellow-700 rounded text-sm hover:bg-yellow-200">
                        🎭 Obfuscated
                    </button>
                </div>
            </div>
        </div>
    </div>

    <script>
        function fillForm(author, text) {{
            document.querySelector('input[name="author"]').value = author;
            document.querySelector('textarea[name="text"]').value = text;
        }}
    </script>
</body>
</html>
    """)


@app.post("/submit")
async def submit_comment(author: str = Form(...), text: str = Form(...)):
    """Submit a new comment for moderation"""
    
    # Check safety
    safety_result = check_safety(text)
    
    # Determine auto-approval
    if safety_result['prediction'] == 'pass' and safety_result['score'] < 0.3:
        status = 'approved'
        auto_approved = True
    elif safety_result['prediction'] == 'flag' and safety_result['score'] > 0.8:
        status = 'rejected'
        auto_approved = False
    else:
        status = 'pending'
        auto_approved = False
    
    # Save comment
    comment = {
        'author': author,
        'text': text,
        'status': status,
        'safety_result': safety_result,
        'auto_approved': auto_approved,
        'moderator_note': ''
    }
    
    db.add(comment)
    
    # Redirect based on status
    if status == 'approved':
        return RedirectResponse(url="/approved?message=Comment+approved+automatically", status_code=303)
    elif status == 'rejected':
        return RedirectResponse(url="/?message=Comment+rejected+due+to+policy+violation", status_code=303)
    else:
        return RedirectResponse(url="/moderation?message=Comment+pending+review", status_code=303)


@app.get("/moderation", response_class=HTMLResponse)
async def moderation_queue():
    """Moderation queue for pending comments"""
    pending_comments = db.get_pending()
    
    comments_html = ""
    for comment in pending_comments:
        safety = comment['safety_result']
        score_color = "red" if safety['score'] > 0.6 else "yellow" if safety['score'] > 0.3 else "green"
        
        comments_html += f"""
        <div class="bg-white p-6 rounded-lg shadow mb-4">
            <div class="flex justify-between items-start mb-4">
                <div>
                    <div class="font-semibold text-lg text-gray-800">{comment['author']}</div>
                    <div class="text-sm text-gray-500">{comment['created_at'][:19]}</div>
                </div>
                <div class="text-right">
                    <div class="text-sm text-gray-600">Safety Score</div>
                    <div class="text-2xl font-bold text-{score_color}-600">{safety['score']:.0%}</div>
                </div>
            </div>
            
            <div class="mb-4 p-4 bg-gray-50 rounded border-2 border-gray-200">
                <div class="text-gray-800">{comment['text']}</div>
            </div>
            
            <div class="grid grid-cols-2 gap-4 mb-4 text-sm">
                <div class="p-3 bg-gray-100 rounded">
                    <strong>Prediction:</strong> {safety['prediction']}
                </div>
                <div class="p-3 bg-gray-100 rounded">
                    <strong>Category:</strong> {safety.get('category', 'N/A')}
                </div>
                <div class="p-3 bg-gray-100 rounded col-span-2">
                    <strong>Rationale:</strong> {safety.get('rationale', 'N/A')}
                </div>
                <div class="p-3 bg-gray-100 rounded">
                    <strong>Method:</strong> {safety.get('method', 'N/A')}
                </div>
                <div class="p-3 bg-gray-100 rounded">
                    <strong>Latency:</strong> {safety.get('latency_ms', 'N/A')}ms
                </div>
            </div>
            
            <form method="POST" action="/moderate/{comment['id']}" class="flex gap-2">
                <input type="text" name="note" placeholder="Moderator note (optional)" 
                       class="flex-1 p-2 border-2 border-gray-300 rounded">
                <button type="submit" name="action" value="approve" 
                        class="px-6 py-2 bg-green-600 text-white rounded font-semibold hover:bg-green-700">
                    ✅ Approve
                </button>
                <button type="submit" name="action" value="reject" 
                        class="px-6 py-2 bg-red-600 text-white rounded font-semibold hover:bg-red-700">
                    ❌ Reject
                </button>
            </form>
        </div>
        """
    
    if not comments_html:
        comments_html = '<div class="text-center text-gray-500 py-12">No pending comments</div>'
    
    return HTMLResponse(f"""
<!DOCTYPE html>
<html>
<head>
    <title>Moderation Queue - SeaRei Demo</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50">
    <div class="container mx-auto px-4 py-8 max-w-4xl">
        <div class="mb-8">
            <h1 class="text-3xl font-bold text-gray-800 mb-2">Moderation Queue</h1>
            <p class="text-gray-600">{len(pending_comments)} comments awaiting review</p>
        </div>
        
        <div class="mb-4">
            <a href="/" class="text-blue-600 hover:underline">← Back to Submit</a>
        </div>
        
        {comments_html}
    </div>
</body>
</html>
    """)


@app.post("/moderate/{comment_id}")
async def moderate_comment(comment_id: int, action: str = Form(...), note: str = Form("")):
    """Moderate a comment"""
    status = 'approved' if action == 'approve' else 'rejected'
    db.update_status(comment_id, status, note)
    
    return RedirectResponse(url="/moderation?message=Comment+moderated", status_code=303)


@app.get("/approved", response_class=HTMLResponse)
async def approved_comments():
    """View approved comments"""
    approved = [c for c in db.get_all() if c['status'] == 'approved']
    
    comments_html = ""
    for comment in approved:
        auto_badge = "🤖 Auto" if comment.get('auto_approved') else "👤 Manual"
        
        comments_html += f"""
        <div class="bg-white p-6 rounded-lg shadow mb-4">
            <div class="flex justify-between items-start mb-2">
                <div class="font-semibold text-gray-800">{comment['author']}</div>
                <span class="text-xs px-2 py-1 bg-green-100 text-green-700 rounded">{auto_badge}</span>
            </div>
            <div class="text-gray-700 mb-2">{comment['text']}</div>
            <div class="text-xs text-gray-500">
                {comment['created_at'][:19]} • 
                Safety: {comment['safety_result']['score']:.0%}
            </div>
        </div>
        """
    
    if not comments_html:
        comments_html = '<div class="text-center text-gray-500 py-12">No approved comments yet</div>'
    
    return HTMLResponse(f"""
<!DOCTYPE html>
<html>
<head>
    <title>Approved Comments - SeaRei Demo</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50">
    <div class="container mx-auto px-4 py-8 max-w-4xl">
        <div class="mb-8">
            <h1 class="text-3xl font-bold text-gray-800 mb-2">Approved Comments</h1>
            <p class="text-gray-600">{len(approved)} comments published</p>
        </div>
        
        <div class="mb-4">
            <a href="/" class="text-blue-600 hover:underline">← Back to Submit</a>
        </div>
        
        {comments_html}
    </div>
</body>
</html>
    """)


if __name__ == "__main__":
    import uvicorn
    print("\n🚀 Starting Comment Filter Demo...")
    print("📍 Open: http://localhost:8002")
    print("⚠️  Make sure SeaRei API is running on port 8001\n")
    uvicorn.run(app, host="0.0.0.0", port=8002)












