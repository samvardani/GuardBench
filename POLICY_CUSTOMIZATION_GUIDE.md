# Policy Customization Guide

## Overview

SeaRei's **Policy Customization System** empowers organizations to tailor content moderation to their specific needs. Unlike generic APIs, our platform provides granular control over what content is flagged, how strictly it's enforced, and which rules apply to your use case.

## Key Features

### 🎨 Visual Policy Editor
- **Web-based UI** at `/policy-editor.html`
- Drag-and-drop interface for non-technical users
- Real-time policy testing
- Import/export configurations

### 🎚️ Adjustable Thresholds
- **Per-model confidence levels**: Rules, ML, Transformer
- **Preset profiles**: Education (strict), Social Media (balanced), Forums (permissive)
- **Category-specific tuning**: Different thresholds for violence vs. spam

### ⚙️ Custom Rules Engine
- **Add your own regex patterns** for domain-specific terms
- **Industry-specific blocklists**: Education, Healthcare, Finance
- **Flexible actions**: Flag, Block, or Send to Review

### 🚫 Dynamic Blocklist
- **Maintain custom blocked terms** (e.g., competitor names, internal jargon)
- **Case-sensitive options**
- **Bulk import/export** via CSV or JSON

## Quick Start

### 1. Access the Policy Editor

```bash
# Start the API
uvicorn src.service.api:app --port 8001

# Open in browser
open http://localhost:8001/policy-editor.html
```

### 2. Configure Your Policy

**Categories Tab:**
- Enable/disable content categories (Violence, Self-Harm, Sexual, Harassment, Illegal, Spam)

**Thresholds Tab:**
- Adjust confidence levels for each detection method
- Apply preset profiles (Strict, Balanced, Permissive)

**Custom Rules Tab:**
- Add domain-specific regex patterns
- Example: Block competitor mentions, internal codenames

**Blocklist Tab:**
- Add specific terms to always block
- Import existing blocklists

**Advanced Tab:**
- Configure detection behavior (obfuscation, context-awareness)
- Set up webhooks for real-time notifications

### 3. Test Your Policy

Use the built-in testing interface:

```
Input: "This is a test message with potentially unsafe content"
Output: ✅ SAFE (Score: 15%, Method: ensemble, Latency: 2.5ms)
```

### 4. Save & Deploy

```bash
# Save via UI or API
curl -X POST http://localhost:8001/policy/save \
  -H "Content-Type: application/json" \
  -d @my-policy.json

# Activate policy
curl -X POST http://localhost:8001/policy/activate/{policy_id}
```

## API Reference

### Save Policy

```http
POST /policy/save
Content-Type: application/json

{
  "version": "2.1.0",
  "categories": {
    "violence": true,
    "self-harm": true,
    "sexual": true,
    "harassment": true,
    "illegal": true,
    "spam": false
  },
  "thresholds": {
    "rules": 0.50,
    "ml": 0.60,
    "transformer": 0.70,
    "ensemble": 0.50
  },
  "custom_rules": [
    {
      "id": 1,
      "name": "Competitor mentions",
      "category": "custom",
      "pattern": "\\b(competitor1|competitor2)\\b",
      "confidence": 0.9,
      "action": "flag"
    }
  ],
  "blocklist": [
    {
      "id": 1,
      "term": "blocked-term",
      "case_sensitive": false
    }
  ],
  "advanced": {
    "obfuscation": true,
    "context": true,
    "multilang": true,
    "routing": "intelligent",
    "return_categories": true,
    "return_explanation": true,
    "webhook_url": "https://your-domain.com/webhook"
  }
}
```

**Response:**
```json
{
  "success": true,
  "policy_id": "abc123def456",
  "checksum": "abc123def456",
  "saved_at": "2025-01-13T15:30:00Z",
  "message": "Policy saved successfully"
}
```

### Load Active Policy

```http
GET /policy/load
```

**Response:**
```json
{
  "version": "2.1.0",
  "categories": { ... },
  "thresholds": { ... },
  "custom_rules": [ ... ],
  "blocklist": [ ... ],
  "advanced": { ... }
}
```

### List All Policies

```http
GET /policy/list
```

**Response:**
```json
[
  {
    "policy_id": "abc123def456",
    "name": "Education Policy",
    "description": "Strict filtering for K-12",
    "created_at": "2025-01-10T10:00:00Z",
    "updated_at": "2025-01-13T15:30:00Z",
    "active": true,
    "checksum": "abc123def456"
  }
]
```

### Activate Policy

```http
POST /policy/activate/{policy_id}
```

**Response:**
```json
{
  "success": true,
  "policy_id": "abc123def456",
  "activated_at": "2025-01-13T15:35:00Z",
  "message": "Policy activated successfully"
}
```

### Get Presets

```http
GET /policy/presets
```

**Response:**
```json
{
  "education": {
    "name": "Education (K-12)",
    "description": "Strict filtering for educational environments",
    "config": { ... }
  },
  "social_media": { ... },
  "forum": { ... },
  "enterprise": { ... }
}
```

### Validate Policy

```http
POST /policy/validate
Content-Type: application/json

{
  "version": "2.1.0",
  "categories": { ... },
  "thresholds": { ... }
}
```

**Response:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": ["Very low ensemble threshold may cause high false positive rate"],
  "stats": {
    "enabled_categories": 5,
    "custom_rules": 3,
    "blocklist_size": 10
  }
}
```

### Test Policy

```http
POST /policy/test
Content-Type: application/json

{
  "config": { ... },
  "text": "Sample text to test"
}
```

**Response:**
```json
{
  "prediction": "pass",
  "score": 0.15,
  "method": "policy_test",
  "latency_ms": 2.5,
  "explanation": "Tested with custom policy. Enabled categories: violence, harassment",
  "policy_applied": {
    "enabled_categories": ["violence", "harassment"],
    "thresholds": { ... },
    "custom_rules_matched": 0,
    "blocklist_matched": false
  }
}
```

## Use Cases

### 1. Education (K-12)

**Challenge:** Strict content filtering for minors, including slang and coded language.

**Solution:**
```json
{
  "thresholds": {
    "ensemble": 0.30
  },
  "categories": {
    "violence": true,
    "self-harm": true,
    "sexual": true,
    "harassment": true,
    "illegal": true,
    "spam": true
  },
  "advanced": {
    "obfuscation": true
  }
}
```

### 2. Healthcare Platform

**Challenge:** Allow medical terminology while blocking inappropriate content.

**Solution:**
```json
{
  "custom_rules": [
    {
      "name": "Medical terms whitelist",
      "pattern": "\\b(surgery|medication|diagnosis)\\b",
      "action": "pass"
    }
  ],
  "advanced": {
    "context": true
  }
}
```

### 3. Gaming Community

**Challenge:** Moderate toxic behavior while allowing competitive banter.

**Solution:**
```json
{
  "thresholds": {
    "ensemble": 0.60
  },
  "categories": {
    "violence": false,
    "harassment": true
  },
  "blocklist": [
    { "term": "racist-slur-1" },
    { "term": "racist-slur-2" }
  ]
}
```

### 4. Enterprise Workspace

**Challenge:** Professional environment with compliance logging.

**Solution:**
```json
{
  "thresholds": {
    "ensemble": 0.40
  },
  "advanced": {
    "log_requests": true,
    "log_flagged": true,
    "webhook_url": "https://compliance.company.com/webhook"
  }
}
```

## Best Practices

### 1. Start with Presets
- Use predefined profiles as a baseline
- Gradually customize based on real-world feedback

### 2. Test Extensively
- Use the built-in testing interface
- Run against historical data before deploying

### 3. Monitor Performance
- Track false positive/negative rates
- Adjust thresholds based on metrics

### 4. Version Control
- Export policies as JSON
- Store in version control (Git)
- Document changes in commit messages

### 5. Gradual Rollout
- Test new policies on a subset of traffic
- Use A/B testing to compare configurations

### 6. Regular Updates
- Review and update blocklists monthly
- Add new custom rules as needed
- Adjust thresholds based on feedback

## Integration Examples

### Python SDK

```python
from searei import SeaReiClient

# Initialize with custom policy
client = SeaReiClient(
    api_key="your_key",
    policy_id="abc123def456"
)

# Or load policy dynamically
policy = client.load_policy("abc123def456")
result = client.score("text to analyze", policy=policy)
```

### Node.js SDK

```javascript
const SeaRei = require('searei-sdk');

const client = new SeaRei({
  apiKey: 'your_key',
  policyId: 'abc123def456'
});

const result = await client.score('text to analyze');
```

### Direct API Call

```bash
curl -X POST http://localhost:8001/score \
  -H "X-API-Key: your_key" \
  -H "X-Policy-ID: abc123def456" \
  -H "Content-Type: application/json" \
  -d '{"text":"text to analyze"}'
```

## Troubleshooting

### Policy Not Saving

**Issue:** Policy save fails with validation error

**Solution:**
1. Check regex patterns for syntax errors
2. Ensure thresholds are between 0.0 and 1.0
3. Verify at least one category is enabled

### High False Positive Rate

**Issue:** Too much safe content being flagged

**Solution:**
1. Increase ensemble threshold (e.g., 0.50 → 0.60)
2. Disable overly strict categories
3. Add safe terms to custom whitelist rules

### Missing Unsafe Content

**Issue:** Unsafe content not being detected

**Solution:**
1. Decrease ensemble threshold (e.g., 0.50 → 0.40)
2. Enable more categories
3. Add specific patterns to custom rules
4. Enable obfuscation detection

## FAQ

**Q: Can I have multiple active policies?**
A: No, only one policy can be active at a time. Use policy versioning for A/B testing.

**Q: How do custom rules interact with built-in patterns?**
A: Custom rules are evaluated alongside built-in patterns. Results are combined using the ensemble threshold.

**Q: Can I disable the ML/Transformer models?**
A: Yes, set routing strategy to "rules-only" in advanced settings.

**Q: Are policies tenant-specific?**
A: Yes, each API key can have its own policy configuration.

**Q: How often should I update my policy?**
A: Review monthly, update blocklists weekly, adjust thresholds as needed based on metrics.

## Support

- **Documentation:** https://docs.searei.ai/policy-customization
- **API Reference:** http://localhost:8001/docs#/policy
- **Examples:** https://github.com/searei/examples/policy
- **Support:** support@searei.ai

---

**Version:** 2.1.0  
**Last Updated:** January 13, 2025  
**Status:** Production Ready
