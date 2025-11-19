# 5-Minute Integration Guide

Get started with SeaRei AI Safety API in less than 5 minutes!

## Prerequisites

- SeaRei API running (self-hosted or cloud)
- API key (if using authentication)

## Quick Start by Language

### Python (2 minutes)

**1. Install:**
```bash
pip install requests  # Or use the searei SDK when published
```

**2. Copy-paste code:**
```python
import requests

API_URL = "http://localhost:8001"
API_KEY = "your_api_key"  # Optional for self-hosted

def check_content(text):
    response = requests.post(
        f"{API_URL}/score",
        json={"text": text},
        headers={"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
    )
    return response.json()

# Test it
result = check_content("I will kill you")
print(f"Prediction: {result['prediction']}")
print(f"Score: {result['score']}")
print(f"Category: {result.get('category', 'N/A')}")

if result['prediction'] == 'flag':
    print("⚠️ Content flagged!")
else:
    print("✅ Content is safe")
```

**3. Run:**
```bash
python your_script.py
```

**Done!** ✅

---

### Node.js (2 minutes)

**1. Install:**
```bash
npm install axios  # Or use the searei SDK when published
```

**2. Copy-paste code:**
```javascript
const axios = require('axios');

const API_URL = 'http://localhost:8001';
const API_KEY = 'your_api_key';  // Optional for self-hosted

async function checkContent(text) {
    const response = await axios.post(
        `${API_URL}/score`,
        { text },
        API_KEY ? { headers: { Authorization: `Bearer ${API_KEY}` } } : {}
    );
    return response.data;
}

// Test it
(async () => {
    const result = await checkContent('I will kill you');
    console.log(`Prediction: ${result.prediction}`);
    console.log(`Score: ${result.score}`);
    console.log(`Category: ${result.category || 'N/A'}`);
    
    if (result.prediction === 'flag') {
        console.log('⚠️ Content flagged!');
    } else {
        console.log('✅ Content is safe');
    }
})();
```

**3. Run:**
```bash
node your_script.js
```

**Done!** ✅

---

### Go (3 minutes)

**1. Initialize module:**
```bash
go mod init myapp
```

**2. Copy-paste code:**
```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "net/http"
)

const API_URL = "http://localhost:8001"
const API_KEY = "your_api_key"  // Optional for self-hosted

type ScoreRequest struct {
    Text string `json:"text"`
}

type ScoreResponse struct {
    Prediction string  `json:"prediction"`
    Score      float64 `json:"score"`
    Category   string  `json:"category,omitempty"`
}

func checkContent(text string) (*ScoreResponse, error) {
    payload, _ := json.Marshal(ScoreRequest{Text: text})
    req, _ := http.NewRequest("POST", API_URL+"/score", bytes.NewBuffer(payload))
    req.Header.Set("Content-Type", "application/json")
    if API_KEY != "" {
        req.Header.Set("Authorization", "Bearer "+API_KEY)
    }

    client := &http.Client{}
    resp, err := client.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()

    var result ScoreResponse
    json.NewDecoder(resp.Body).Decode(&result)
    return &result, nil
}

func main() {
    result, err := checkContent("I will kill you")
    if err != nil {
        panic(err)
    }

    fmt.Printf("Prediction: %s\n", result.Prediction)
    fmt.Printf("Score: %.2f\n", result.Score)
    fmt.Printf("Category: %s\n", result.Category)

    if result.Prediction == "flag" {
        fmt.Println("⚠️ Content flagged!")
    } else {
        fmt.Println("✅ Content is safe")
    }
}
```

**3. Run:**
```bash
go run main.go
```

**Done!** ✅

---

### cURL (30 seconds!)

```bash
curl -X POST http://localhost:8001/score \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key" \
  -d '{"text": "I will kill you"}'
```

**Output:**
```json
{
  "prediction": "flag",
  "score": 0.95,
  "category": "violence",
  "rationale": "Contains explicit violent threat",
  "method": "ensemble_transformer",
  "latency_ms": 4
}
```

---

## Common Use Cases

### 1. User-Generated Content (Comments, Posts)

```python
# Before saving to database
user_comment = request.form['comment']
result = check_content(user_comment)

if result['prediction'] == 'flag':
    return "Your comment violates our guidelines", 400
else:
    save_comment(user_comment)
    return "Comment posted successfully", 200
```

### 2. Chat/Messaging Applications

```javascript
// Real-time message filtering
socket.on('message', async (message) => {
    const result = await checkContent(message.text);
    
    if (result.prediction === 'flag') {
        socket.emit('message_blocked', {
            reason: result.category,
            rationale: result.rationale
        });
    } else {
        broadcast(message);
    }
});
```

### 3. Content Moderation Queue

```python
# Batch processing for moderation queue
texts = [post['content'] for post in pending_posts]

response = requests.post(
    f"{API_URL}/score-batch",
    json={"rows": [{"text": t} for t in texts]}
)
results = response.json()['results']

# Flag high-risk content for manual review
for i, result in enumerate(results):
    if result['prediction'] == 'flag' and result['score'] > 0.8:
        flag_for_review(pending_posts[i], result)
```

### 4. API Gateway Middleware

```go
// Express.js middleware
app.use(async (req, res, next) => {
    if (req.body && req.body.message) {
        const result = await checkContent(req.body.message);
        if (result.prediction === 'flag') {
            return res.status(400).json({
                error: 'Content policy violation',
                category: result.category
            });
        }
    }
    next();
});
```

---

## Configuration Options

### Request Parameters

```json
{
  "text": "Content to check",
  "category": "violence",    // Optional: filter by category
  "language": "en"           // Optional: specify language
}
```

### Response Fields

```json
{
  "prediction": "flag",          // "flag" or "pass"
  "score": 0.95,                 // Confidence (0.0-1.0)
  "category": "violence",        // Violation category
  "rationale": "Explicit threat", // Human-readable explanation
  "method": "ensemble",          // Detection method used
  "latency_ms": 4,               // Processing time
  "policy_version": "1.2.0",     // Policy version
  "policy_checksum": "abc123"    // Policy checksum
}
```

---

## Error Handling

### HTTP Status Codes

- `200 OK`: Success
- `400 Bad Request`: Invalid input
- `401 Unauthorized`: Invalid/missing API key
- `413 Content Too Large`: Text exceeds max length
- `422 Unprocessable Entity`: Validation error
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

### Example Error Response

```json
{
  "detail": "Text length exceeds maximum (10000 characters)"
}
```

### Handling in Code

```python
try:
    response = requests.post(f"{API_URL}/score", json={"text": text})
    response.raise_for_status()
    result = response.json()
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 429:
        print("Rate limit exceeded, retry later")
    elif e.response.status_code == 401:
        print("Invalid API key")
    else:
        print(f"API error: {e}")
```

---

## Performance Tips

1. **Use Batch Endpoint** for multiple texts:
   ```python
   # Instead of:
   for text in texts:
       check_content(text)  # N requests
   
   # Do this:
   check_batch(texts)  # 1 request
   ```

2. **Set Timeouts**:
   ```python
   response = requests.post(url, json=data, timeout=5)  # 5 second timeout
   ```

3. **Cache Results** for identical content:
   ```python
   import hashlib
   
   text_hash = hashlib.sha256(text.encode()).hexdigest()
   if text_hash in cache:
       return cache[text_hash]
   ```

4. **Async Processing** for high-volume:
   ```python
   # Queue for background processing
   redis_queue.enqueue(check_content, text)
   ```

---

## Next Steps

- ✅ **Integration complete!**
- 📚 [Read full API docs](https://docs.searei.ai)
- 🎮 [Try the web playground](http://localhost:8001/playground.html)
- 📦 [Install official SDKs](https://github.com/searei) (Python, Node.js, Go)
- 🚀 [Deploy to production](./DEPLOYMENT_ROADMAP.md)

---

## Troubleshooting

### "Connection refused"
- Check if API is running: `curl http://localhost:8001/healthz`
- Verify port and URL

### "Unauthorized"
- Check API key is correct
- Ensure `Authorization` header format: `Bearer your_api_key`

### "Timeout"
- Increase timeout setting
- Check API server load
- Consider async processing for long texts

### Still stuck?
- **Email:** support@searei.ai
- **GitHub:** https://github.com/searei/safety-eval-mini/issues

---

**🎉 Congratulations! You've integrated SeaRei AI Safety in under 5 minutes!**












