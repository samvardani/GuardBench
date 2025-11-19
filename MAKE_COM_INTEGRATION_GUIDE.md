# How to Use SeaRei with Make.com (Integromat)

## Overview

Make.com (formerly Integromat) is a no-code automation platform. This guide shows you how to integrate SeaRei AI safety moderation into your Make.com workflows.

## Quick Start (5 Minutes)

### Step 1: Get Your SeaRei API Running

```bash
# Start the SeaRei API
cd /Users/samvardani/Projects/safety-eval-mini
uvicorn src.service.api:app --port 8001

# Verify it's running
curl http://localhost:8001/healthz
```

### Step 2: Create a Make.com Account

1. Go to [make.com](https://www.make.com/)
2. Sign up for a free account
3. Click "Create a new scenario"

### Step 3: Build Your First Automation

## Example Scenarios

### Scenario 1: Google Forms → SeaRei → Email Alert

**Use Case**: Automatically moderate form submissions and alert admin if unsafe content is detected.

#### Setup Steps:

1. **Add Google Forms Trigger**
   - Search for "Google Forms"
   - Select "Watch Responses"
   - Connect your Google account
   - Select your form

2. **Add HTTP Module** (SeaRei API Call)
   - Search for "HTTP"
   - Select "Make a request"
   - Configure:
     ```
     URL: http://localhost:8001/score
     Method: POST
     Headers:
       Content-Type: application/json
     Body:
       {
         "text": "{{1.question1}} {{1.question2}}"
       }
     ```

3. **Add Router** (Decision Logic)
   - Add "Router" module
   - Create two routes:
     - **Route 1 (Safe)**: Filter: `{{2.prediction}}` equals `pass`
     - **Route 2 (Unsafe)**: Filter: `{{2.prediction}}` equals `flag`

4. **Add Email Module** (Alert on Unsafe)
   - On Route 2, add "Email" → "Send an email"
   - Configure:
     ```
     To: admin@yourcompany.com
     Subject: ⚠️ Unsafe Form Submission Detected
     Content: 
       Risk Score: {{2.score}}
       Method: {{2.method}}
       Response: {{1.question1}}
     ```

5. **Add Google Sheets** (Log Everything)
   - Add "Google Sheets" → "Add a Row"
   - Map fields:
     ```
     Timestamp: {{now}}
     Response: {{1.question1}}
     Safety Result: {{2.prediction}}
     Score: {{2.score}}
     ```

6. **Activate & Test**
   - Click "Run once" to test
   - Submit a test form
   - Verify automation works

---

### Scenario 2: Typeform → SeaRei → Airtable

**Use Case**: Filter survey responses and store only flagged content for review.

#### Setup:

1. **Trigger**: Typeform → New Entry
2. **Action**: HTTP Request to SeaRei
   ```json
   {
     "text": "{{response_text}}"
   }
   ```
3. **Filter**: Only continue if `prediction = flag`
4. **Action**: Airtable → Create Record
   - Table: "Flagged Responses"
   - Fields: Response, Score, Timestamp

---

### Scenario 3: Webhook → SeaRei → Slack Notification

**Use Case**: Monitor comments from your website/app and notify Slack channel.

#### Setup:

1. **Trigger**: Webhooks → Custom Webhook
   - Copy webhook URL
   - Add to your app: `POST /webhook` with `{"text": "comment"}`

2. **Action**: HTTP → SeaRei API
   ```json
   {
     "text": "{{1.text}}"
   }
   ```

3. **Filter**: `{{2.prediction}}` equals `flag`

4. **Action**: Slack → Send Message
   ```
   Channel: #moderation
   Message: 
     ⚠️ Unsafe content detected!
     Text: {{1.text}}
     Score: {{formatNumber({{2.score}} * 100; 1)}}%
   ```

---

### Scenario 4: Gmail → SeaRei → Auto-Archive

**Use Case**: Automatically filter and archive emails with unsafe content.

#### Setup:

1. **Trigger**: Gmail → Watch Emails
   - Label: "Inbox"
   - Filter: (optional) from specific senders

2. **Action**: HTTP → SeaRei
   ```json
   {
     "text": "{{1.subject}} {{1.textPlain}}"
   }
   ```

3. **Router with 2 Routes**:
   - **Safe**: Add label "Approved"
   - **Unsafe**: Add label "Flagged", Move to "Spam"

---

## Advanced Configuration

### Using Custom Policies

If you've created custom policies in SeaRei, pass the policy ID:

```json
{
  "text": "{{input_text}}",
  "policy_id": "abc123def456"
}
```

### Batch Processing

To scan multiple items at once:

1. **Iterator Module**:
   - Add "Iterator" after your trigger
   - Array: `{{trigger.items}}`

2. **HTTP Request (in loop)**:
   ```json
   {
     "text": "{{item.text}}"
   }
   ```

3. **Aggregator**:
   - Collect all results
   - Create summary report

### Error Handling

Add error handler to HTTP module:

1. Right-click HTTP module → "Add error handler"
2. Select "Resume" or "Ignore"
3. Add fallback action (e.g., log to Google Sheets)

---

## Complete Setup: Google Forms Moderation

### Full Workflow

```
[Google Forms: Watch Responses]
           ↓
[HTTP: POST to SeaRei API]
           ↓
      [Router]
       ↙     ↘
   [Safe]   [Unsafe]
     ↓         ↓
 [Sheet:   [Email:
  Log]     Alert]
     ↓         ↓
        [Sheet:
      Log All]
```

### Step-by-Step Configuration

#### 1. Google Forms Trigger

```
Module: Google Forms → Watch Responses
Connection: [Your Google Account]
Form: [Select your form]
Limit: 10 responses
```

#### 2. SeaRei API Call

```
Module: HTTP → Make a request
URL: http://YOUR_SERVER_IP:8001/score
Method: POST

Headers:
  Content-Type: application/json

Body (JSON):
{
  "text": "{{1.textField1}} {{1.textField2}}"
}

Parse response: Yes
```

**Important**: Replace `localhost` with your actual server IP if Make.com needs to access it remotely!

#### 3. Router

```
Module: Flow Control → Router
```

#### 4. Route 1: Safe Content

**Filter**: 
```
Field: 2.prediction
Operator: Equal to
Value: pass
```

**Action**: Google Sheets → Add a Row
```
Spreadsheet: Moderation Log
Sheet: Approved
Values:
  Timestamp: {{formatDate(now; "YYYY-MM-DD HH:mm:ss")}}
  Response: {{1.textField1}}
  Score: {{formatNumber({{2.score}} * 100; 1)}}%
  Status: ✅ Safe
```

#### 5. Route 2: Unsafe Content

**Filter**:
```
Field: 2.prediction
Operator: Equal to  
Value: flag
```

**Action 1**: Email → Send an email
```
To: admin@company.com
Subject: ⚠️ Unsafe Form Submission

Body:
=================================
UNSAFE CONTENT DETECTED
=================================

Risk Score: {{formatNumber({{2.score}} * 100; 1)}}%
Detection Method: {{2.method}}
Latency: {{2.latency_ms}}ms

Response Text:
{{1.textField1}}

Timestamp: {{formatDate(now; "YYYY-MM-DD HH:mm:ss")}}
=================================
```

**Action 2**: Google Sheets → Add a Row
```
Spreadsheet: Moderation Log
Sheet: Flagged
Values:
  Timestamp: {{formatDate(now; "YYYY-MM-DD HH:mm:ss")}}
  Response: {{1.textField1}}
  Score: {{formatNumber({{2.score}} * 100; 1)}}%
  Status: ⚠️ Flagged
  Method: {{2.method}}
```

---

## Exposing Local API to Make.com

Since Make.com is cloud-based, it can't access `localhost`. Here are 3 solutions:

### Option 1: ngrok (Quick & Easy)

```bash
# Install ngrok
brew install ngrok  # or download from ngrok.com

# Expose your API
ngrok http 8001

# Copy the public URL (e.g., https://abc123.ngrok.io)
# Use this in Make.com instead of localhost
```

### Option 2: Deploy to Cloud

Deploy SeaRei to a cloud provider:

```bash
# Example: Deploy to Heroku
heroku create my-searei-api
git push heroku main

# Use: https://my-searei-api.herokuapp.com/score
```

See `DEPLOYMENT_GUIDE.md` for AWS/GCP/Azure instructions.

### Option 3: Cloudflare Tunnel

```bash
# Install cloudflared
brew install cloudflare/cloudflare/cloudflared

# Create tunnel
cloudflared tunnel --url http://localhost:8001

# Use the generated URL in Make.com
```

---

## Example Make.com Scenarios

### 1. Comment Moderation

**Trigger**: Webhook (from your blog/app)  
**Action**: SeaRei scan → If unsafe, post to Slack  
**Result**: Real-time comment moderation

### 2. Customer Support Ticket Filtering

**Trigger**: Zendesk New Ticket  
**Action**: SeaRei scan → Route to appropriate queue  
**Result**: Priority routing for sensitive tickets

### 3. Social Media Monitoring

**Trigger**: Twitter New Mention  
**Action**: SeaRei scan → Flag harmful mentions  
**Result**: Protect brand reputation

### 4. Content Approval Workflow

**Trigger**: Google Docs New Document  
**Action**: SeaRei scan → If safe, publish to WordPress  
**Result**: Automated content publishing

---

## Testing Your Integration

### 1. Test with Safe Content

Submit this text:
```
"Thank you for your help! This product is amazing."
```

Expected Result:
- `prediction`: "pass"
- `score`: < 0.3
- Should route to "Safe" path

### 2. Test with Unsafe Content

Submit this text:
```
"I hate everyone and want to hurt people"
```

Expected Result:
- `prediction`: "flag"
- `score`: > 0.7
- Should route to "Unsafe" path
- Should trigger email alert

### 3. Test Error Handling

Stop the SeaRei API and trigger the scenario.

Expected Result:
- HTTP module should show error
- Error handler should activate
- Fallback action should execute

---

## Pricing & Limits

### Make.com Tiers

- **Free**: 1,000 operations/month
- **Core**: $9/mo - 10,000 operations
- **Pro**: $16/mo - 10,000 operations + premium apps

### SeaRei API Costs

- **Free Tier**: 1,000 requests/month
- **Starter**: $49/mo - 10,000 requests
- **Pro**: $199/mo - 100,000 requests

### Optimization Tips

1. **Batch requests** when possible (lower operation count)
2. **Use filters early** (avoid unnecessary API calls)
3. **Cache results** in Google Sheets (prevent duplicate scans)

---

## Troubleshooting

### Issue: "Connection Failed"

**Cause**: Make.com can't reach your API

**Solution**:
1. Use ngrok/cloudflare tunnel (see above)
2. Or deploy API to cloud
3. Check firewall rules

### Issue: "Invalid Response"

**Cause**: SeaRei API returned unexpected format

**Solution**:
1. Check API is running: `curl http://your-api/healthz`
2. Verify JSON format in HTTP module
3. Enable "Parse response" in HTTP module

### Issue: "Rate Limit Exceeded"

**Cause**: Too many requests to SeaRei

**Solution**:
1. Upgrade SeaRei tier
2. Add delay module between requests
3. Use batch endpoint if available

---

## Example JSON for Make.com

### HTTP Request Body (Simple)

```json
{
  "text": "{{trigger.message}}"
}
```

### HTTP Request Body (With Policy)

```json
{
  "text": "{{trigger.message}}",
  "policy_id": "education-strict"
}
```

### HTTP Request Body (Batch)

```json
{
  "texts": [
    "{{item1.text}}",
    "{{item2.text}}",
    "{{item3.text}}"
  ]
}
```

---

## Next Steps

1. ✅ Set up your first scenario (Google Forms example)
2. ✅ Test with safe and unsafe content
3. ✅ Expose API publicly (ngrok or deploy)
4. ✅ Add error handling
5. ✅ Monitor usage and optimize

## Resources

- **Make.com Docs**: https://www.make.com/en/help/
- **SeaRei API Docs**: `http://localhost:8001/docs`
- **ngrok**: https://ngrok.com/docs
- **Examples**: See `integrations/make-examples/`

---

**Happy Automating! 🚀**

For support, see `INTEGRATIONS_COMPLETE.md` or contact support@searei.ai












