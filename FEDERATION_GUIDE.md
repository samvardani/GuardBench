# AEGIS Federation Network Guide

**Gossip Protocol for Privacy-Preserving Antibody Sharing**

## Overview

The AEGIS Federation Network enables multiple SeaRei deployments to share threat intelligence (antibodies) without compromising privacy. Only regex patterns and metadata are shared—never raw text or user data.

## Key Features

### 1. **Privacy-Preserving** 🔒
- Only shares regex patterns + metadata
- No raw text, user IDs, or sensitive data
- Anonymized source tracking (node IDs only)
- GDPR/CCPA compliant by design

### 2. **Reputation System** ⭐
- Community voting (upvote/downvote)
- Accuracy tracking (false positive/negative rates)
- Auto-rejection of low-quality patterns
- Weighted scoring (accuracy 70% + votes 30%)

### 3. **Gossip Protocol** 📡
- Decentralized pattern propagation
- Auto-sync validated antibodies
- 24-hour distribution target
- Resilient to node failures

### 4. **Centralized MVP** 🚀
- REST API for easy integration
- POST `/federation/intel-exchange` for submissions
- GET `/federation/antibodies` for retrieval
- Full CRUD operations

---

## Quick Start

### 1. Start the API

```bash
uvicorn src.service.api:app --reload --port 8001
```

### 2. Submit an Antibody

```bash
curl -X POST http://localhost:8001/federation/intel-exchange \
  -H "Content-Type: application/json" \
  -d '{
    "pattern": "k[i1!]ll\\s+y[o0]u",
    "confidence": 0.85,
    "category": "violence",
    "seen_count": 5,
    "false_positive_count": 0
  }'
```

### 3. Get Validated Antibodies

```bash
curl "http://localhost:8001/federation/antibodies?min_reputation=0.6&limit=10"
```

### 4. Vote on Antibodies

```bash
# Upvote (worked well)
curl -X POST http://localhost:8001/federation/upvote \
  -H "Content-Type: application/json" \
  -d '{"antibody_id": "a1b2c3d4e5f6g7h8"}'

# Downvote (false positive)
curl -X POST http://localhost:8001/federation/downvote \
  -H "Content-Type: application/json" \
  -d '{"antibody_id": "a1b2c3d4e5f6g7h8", "reason": "false_positive"}'
```

---

## API Endpoints

### Submit Antibody
```
POST /federation/intel-exchange
```

**Request:**
```json
{
  "pattern": "regex_pattern",
  "confidence": 0.85,
  "category": "violence",
  "seen_count": 1,
  "false_positive_count": 0,
  "false_negative_count": 0
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "created",
    "antibody_id": "a1b2c3d4e5f6g7h8",
    "reputation": 0.850
  }
}
```

### Get Antibodies
```
GET /federation/antibodies?category=violence&min_reputation=0.6&limit=100
```

**Response:**
```json
{
  "success": true,
  "count": 10,
  "antibodies": [
    {
      "antibody_id": "a1b2c3d4e5f6g7h8",
      "pattern": "k[i1!]ll\\s+y[o0]u",
      "confidence": 0.85,
      "category": "violence",
      "reputation_score": 0.920,
      "upvotes": 12,
      "downvotes": 1,
      "seen_count": 50,
      "source_node": "node_abc123"
    }
  ]
}
```

### Upvote/Downvote
```
POST /federation/upvote
POST /federation/downvote
```

**Request:**
```json
{
  "antibody_id": "a1b2c3d4e5f6g7h8",
  "reason": "false_positive"  // for downvote only
}
```

### Sync with Node (Gossip Protocol)
```
POST /federation/sync
```

**Request:**
```json
{
  "node_id": "node_xyz789",
  "antibodies": [
    {
      "pattern": "...",
      "confidence": 0.85,
      ...
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "imported": 5,
    "updated": 2,
    "rejected": 1,
    "message": "Synced 7 antibodies from node_xyz789"
  }
}
```

### Export Antibodies
```
GET /federation/export?min_reputation=0.6
```

**Response:**
```json
{
  "success": true,
  "data": {
    "node_id": "local_node",
    "timestamp": "2025-01-13T12:00:00Z",
    "antibodies": [...]
  }
}
```

### Statistics
```
GET /federation/statistics
```

**Response:**
```json
{
  "success": true,
  "statistics": {
    "total_nodes": 5,
    "total_antibodies": 150,
    "active_antibodies": 120,
    "expired_antibodies": 30,
    "avg_reputation": 0.780,
    "categories": {
      "violence": 45,
      "harassment": 30,
      "illegal": 25
    }
  }
}
```

---

## CLI Usage

### Python CLI

```bash
# Submit antibody
python src/aegis/federation.py submit "k[i1!]ll\\s+y[o0]u" violence 0.85

# List antibodies
python src/aegis/federation.py list violence

# Upvote
python src/aegis/federation.py upvote a1b2c3d4e5f6g7h8

# Downvote
python src/aegis/federation.py downvote a1b2c3d4e5f6g7h8 false_positive

# Statistics
python src/aegis/federation.py stats

# Export
python src/aegis/federation.py export > antibodies.json

# Prune expired/low-reputation
python src/aegis/federation.py prune
```

---

## Demo Script

```bash
# Run comprehensive demo
python examples/federation_demo.py
```

**Demo includes:**
1. Basic antibody submission
2. Reputation system (voting)
3. Retrieving validated antibodies
4. Gossip protocol simulation
5. Federation statistics
6. Privacy features showcase

---

## Integration Examples

### Python

```python
import requests

API_BASE = "http://localhost:8001"

# Submit antibody
response = requests.post(
    f"{API_BASE}/federation/intel-exchange",
    json={
        "pattern": r"k[i1!]ll\s+y[o0]u",
        "confidence": 0.85,
        "category": "violence"
    }
)

result = response.json()
antibody_id = result['data']['antibody_id']

# Upvote if it works well
requests.post(
    f"{API_BASE}/federation/upvote",
    json={"antibody_id": antibody_id}
)

# Get validated antibodies
response = requests.get(
    f"{API_BASE}/federation/antibodies",
    params={"min_reputation": 0.7}
)

antibodies = response.json()['antibodies']
```

### cURL

```bash
# Submit
curl -X POST http://localhost:8001/federation/intel-exchange \
  -H "Content-Type: application/json" \
  -d '{"pattern": "test\\s+pattern", "confidence": 0.8, "category": "test"}'

# Get
curl "http://localhost:8001/federation/antibodies?min_reputation=0.6"

# Vote
curl -X POST http://localhost:8001/federation/upvote \
  -d '{"antibody_id": "abc123"}'
```

---

## Reputation Scoring

### Formula

```
reputation = (accuracy * 0.7) + (vote_score * 0.3)

where:
  accuracy = 1 - (false_positives / total_seen)
  vote_score = upvotes / (upvotes + downvotes)
```

### Penalties

- **High FP Rate** (>10%): Reputation × 0.5
- **Low Reputation** (<0.3 with 10+ seen): Auto-pruned
- **Expired** (>30 days): Automatically removed

### Thresholds

- **Minimum for Distribution:** 0.6 (configurable)
- **Auto-Prune Threshold:** 0.3
- **Max Age:** 30 days

---

## Security Considerations

### What's Shared ✅
- Regex patterns (no raw text)
- Confidence scores
- Category labels
- Accuracy metrics (FP/FN counts)
- Anonymized node IDs

### What's NOT Shared ❌
- Raw user-generated content
- User IDs or personal data
- IP addresses or URLs
- Internal system details
- Business logic or rules

### Privacy by Design
1. **Pattern-Only Sharing:** Only regex patterns are transmitted
2. **Anonymization:** Node IDs are hashed, no identifying info
3. **No User Data:** Zero user content leaves your deployment
4. **Reputation Gates:** Low-quality patterns are rejected
5. **Audit Trail:** All submissions/votes are logged locally

---

## Deployment Patterns

### Pattern 1: Single Organization (Multi-Region)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   US-East   │────▶│   US-West   │────▶│     EU      │
│  (Primary)  │◀────│  (Replica)  │◀────│  (Replica)  │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       └───────────────────┴───────────────────┘
              Sync every 6 hours
```

### Pattern 2: Federation of Organizations

```
┌─────────────┐
│   Org A     │
│ (Social)    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────┐
│   Central Intelligence Hub      │
│   (Aggregate & Validate)        │
└─────────────────────────────────┘
       │              │
       ▼              ▼
┌─────────────┐  ┌─────────────┐
│   Org B     │  │   Org C     │
│  (Gaming)   │  │   (Forum)   │
└─────────────┘  └─────────────┘
```

### Pattern 3: Fully Decentralized (Future)

```
┌────┐     ┌────┐     ┌────┐
│ N1 │────▶│ N2 │────▶│ N3 │
└─┬──┘     └─┬──┘     └─┬──┘
  │          │          │
  └──────────┼──────────┘
             ▼
          ┌────┐
          │ N4 │  ← Gossip to random peers
          └────┘
```

---

## Performance

### Latency
- Submit antibody: <10ms
- Get antibodies: <20ms
- Sync 100 antibodies: <100ms

### Storage
- ~1KB per antibody
- 10K antibodies = ~10MB
- Prune monthly to maintain

### Scalability
- Handles 1K+ nodes
- 100K+ antibodies
- 1M+ votes

---

## Maintenance

### Daily
```bash
# Check statistics
curl http://localhost:8001/federation/statistics
```

### Weekly
```bash
# Prune expired/low-reputation
curl -X POST http://localhost:8001/federation/prune
```

### Monthly
```bash
# Backup federation database
cp data/federation.yaml backups/federation_$(date +%Y%m%d).yaml
```

---

## Troubleshooting

### Issue: Antibodies not syncing
**Solution:** Check node connectivity and reputation thresholds

```bash
# Verify export works
curl http://localhost:8001/federation/export

# Check reputation distribution
curl http://localhost:8001/federation/statistics
```

### Issue: High false positive rate
**Solution:** Downvote problematic antibodies

```bash
curl -X POST http://localhost:8001/federation/downvote \
  -d '{"antibody_id": "...", "reason": "false_positive"}'
```

### Issue: Low sync success rate
**Solution:** Lower reputation threshold temporarily

```bash
# Get with lower threshold
curl "http://localhost:8001/federation/antibodies?min_reputation=0.5"
```

---

## Roadmap

### Phase 1: Centralized MVP ✅ (CURRENT)
- REST API for intel exchange
- Reputation system with voting
- Manual sync via API calls
- Basic gossip protocol

### Phase 2: Semi-Automated (Q2 2025)
- Scheduled auto-sync (cron/systemd)
- Webhook notifications
- Multi-region support
- Enhanced reputation algorithms

### Phase 3: Fully Decentralized (Q3 2025)
- P2P gossip protocol
- DHT for antibody discovery
- Blockchain-based reputation (optional)
- Zero-trust architecture

### Phase 4: Advanced Features (Q4 2025+)
- ML-based pattern generation
- Adversarial testing framework
- Cross-modal antibodies (text + image patterns)
- Federated learning for model updates

---

## FAQ

**Q: Is my data safe?**  
A: Yes. Only regex patterns are shared, never raw text or user data.

**Q: Can I opt-out of specific antibodies?**  
A: Yes. Downvote them, and they'll be excluded from your deployment.

**Q: How do I trust other nodes?**  
A: Reputation system ensures only high-quality patterns propagate.

**Q: What if a node submits spam?**  
A: Low-reputation patterns are auto-rejected and pruned.

**Q: Can I run a private federation?**  
A: Yes. Just don't sync with external nodes.

**Q: How do I report a bug?**  
A: Open an issue on GitHub or contact support.

---

## Support

- **Documentation:** `/docs` (FastAPI auto-docs)
- **API Health:** `GET /federation/health`
- **Demo Script:** `python examples/federation_demo.py`
- **CLI Help:** `python src/aegis/federation.py`

---

**Built with privacy, security, and community in mind. 🛡️**












