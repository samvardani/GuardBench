# SEAREI Backend API

**Multi-purpose backend API** for SEAREI Virtual Staging and AI Safety Evaluation Platform.

This backend can be deployed standalone or integrated into other platforms (WordPress, Shopify, custom apps, etc.).

---

## 🏗️ Architecture

### Core Services

**1. FastAPI Application** (`src/service/api.py`)
- Main API server with FastAPI
- Multi-tenant authentication
- Role-based access control (RBAC)
- CORS middleware
- Rate limiting
- Provenance tracking

**2. Virtual Staging API** (`src/service/staging_*.py`)
- **staging_api.py** - Core staging endpoints
- **staging_payments.py** - Stripe integration for payments
- **staging_upload.py** - File upload handling
- **staging_admin.py** - Admin operations
- **staging_db.py** - Database operations
- **staging_models.py** - Data models
- **staging_notifications.py** - Email/notification system

**3. AI Safety Service** (`src/service/`)
- Guard evaluation endpoints
- Batch processing
- Federation endpoints
- Policy management

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone <your-repo-url>
cd safety-eval-mini

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy config template
cp config.example.yaml config.yaml
# Edit config.yaml with your settings
```

### Configuration

Edit `config.yaml`:

```yaml
# API Settings
api:
  host: "0.0.0.0"
  port: 8001
  cors_allow_origins: "http://localhost:3000,https://yourdomain.com"

# Stripe (for virtual staging payments)
stripe:
  secret_key: "sk_test_..."  # From Stripe Dashboard
  publishable_key: "pk_test_..."  # From Stripe Dashboard
  webhook_secret: "whsec_..."  # From Stripe Webhooks

# Database
database:
  path: "data/staging.db"  # SQLite database

# Email (for notifications)
email:
  smtp_host: "smtp.gmail.com"
  smtp_port: 587
  smtp_user: "your-email@gmail.com"
  smtp_password: "your-app-password"
  from_email: "noreply@searei.com"
```

### Run Server

```bash
# Development
PYTHONPATH=src uvicorn service.api:app --host 0.0.0.0 --port 8001 --reload

# Production
PYTHONPATH=src uvicorn service.api:app --host 0.0.0.0 --port 8001 --workers 4
```

---

## 📡 API Endpoints

### Virtual Staging Endpoints

**Stripe Checkout**
```
POST /api/v1/payments/checkout-session
Body: {
  "project_id": "b2f5df8b-d7fc-4f21-8b7c-b900f9e490c0",
  "package": "essential|professional|enterprise",
  "rooms": 1,
  "success_url": "https://yoursite.com/success",
  "cancel_url": "https://yoursite.com/cancel"
}
Response: {
  "checkout_url": "https://checkout.stripe.com/...",
  "session_id": "cs_...",
  "publishable_key": "pk_..."
}
```

**Stripe Webhook**
```
POST /api/v1/webhooks/stripe
Headers: {
  "Stripe-Signature": "..."
}
Body: Stripe webhook event JSON
```

**Waitlist**
```
POST /api/v1/waitlist/vancouver
Body: {
  "name": "...",
  "email": "...",
  "phone": "...",
  "brokerage": "...",
  "timeframe": "...",
  "property_type": "...",
  "message": "..."
}
```

**File Upload**
```
POST /api/v1/staging/upload
Headers: {
  "Authorization": "Bearer <token>"
}
Body: multipart/form-data with files
```

**Job Management**
```
GET /api/v1/staging/jobs
GET /api/v1/staging/jobs/{job_id}
POST /api/v1/staging/jobs
PATCH /api/v1/staging/jobs/{job_id}
```

### AI Safety Endpoints

**Health Check**
```
GET /healthz
Response: {
  "status": "ok",
  "version": "2024.10",
  "policy_version": "v1.0"
}
```

**Score Text**
```
POST /score
Body: {
  "text": "...",
  "category": "violence",
  "language": "en"
}
```

**Batch Evaluation**
```
POST /batch
Body: {
  "items": [...]
}
```

---

## 🔌 Integration Examples

### WordPress Integration

```php
// In your WordPress theme or plugin
function searei_create_checkout($package, $rooms) {
    $response = wp_remote_post('https://api.searei.com/api/v1/payments/checkout-session', [
        'headers' => ['Content-Type' => 'application/json'],
        'body' => json_encode([
            'project_id' => 'b2f5df8b-d7fc-4f21-8b7c-b900f9e490c0',
            'package' => $package,
            'rooms' => $rooms,
            'success_url' => home_url('/success'),
            'cancel_url' => home_url('/pricing')
        ])
    ]);
    
    $data = json_decode(wp_remote_retrieve_body($response), true);
    return $data['checkout_url'];
}
```

### React/Next.js Integration

```javascript
// Create checkout session
const createCheckout = async (packageType, roomCount) => {
  const response = await fetch('https://api.searei.com/api/v1/payments/checkout-session', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_id: 'b2f5df8b-d7fc-4f21-8b7c-b900f9e490c0',
      package: packageType,
      rooms: roomCount,
      success_url: `${window.location.origin}/success`,
      cancel_url: `${window.location.origin}/pricing`
    })
  });
  
  const data = await response.json();
  window.location.href = data.checkout_url;
};
```

### Shopify Integration

```liquid
<!-- In Shopify theme -->
<script>
  async function buyStaging(package, rooms) {
    const response = await fetch('https://api.searei.com/api/v1/payments/checkout-session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: 'b2f5df8b-d7fc-4f21-8b7c-b900f9e490c0',
        package: package,
        rooms: rooms,
        success_url: '{{ shop.url }}/pages/thank-you',
        cancel_url: '{{ shop.url }}/pages/pricing'
      })
    });
    
    const data = await response.json();
    window.location.href = data.checkout_url;
  }
</script>
```

---

## 🗄️ Database Schema

### Virtual Staging Tables

**jobs**
- `id` - UUID primary key
- `customer_email` - Customer email
- `package` - Package type (essential/professional/enterprise)
- `room_count` - Number of rooms
- `status` - Job status (pending/in_progress/completed/cancelled)
- `stripe_payment_id` - Stripe payment intent ID
- `created_at` - Timestamp
- `updated_at` - Timestamp

**uploads**
- `id` - UUID primary key
- `job_id` - Foreign key to jobs
- `filename` - Original filename
- `file_path` - Storage path
- `file_hash` - SHA256 hash for compliance
- `uploaded_at` - Timestamp

**deliveries**
- `id` - UUID primary key
- `job_id` - Foreign key to jobs
- `file_path` - Delivery file path
- `download_url` - Temporary download URL
- `delivered_at` - Timestamp

---

## 🔐 Security

### Environment Variables

Set these in production:

```bash
export SESSION_SECRET="$(openssl rand -hex 32)"
export STRIPE_SECRET_KEY="sk_live_..."
export STRIPE_WEBHOOK_SECRET="whsec_..."
export DATABASE_PATH="/var/lib/searei/staging.db"
export CORS_ALLOW_ORIGINS="https://searei.com,https://www.searei.com"
```

### Rate Limiting

Configured in `config.yaml`:

```yaml
rate_limiting:
  enabled: true
  requests_per_minute: 60
  requests_per_hour: 1000
```

### CORS

Configure allowed origins in `config.yaml`:

```yaml
api:
  cors_allow_origins: "https://searei.com,https://app.searei.com"
```

---

## 🐳 Docker Deployment

```bash
# Build image
docker build -t searei-backend:latest .

# Run container
docker run -d \
  --name searei-api \
  -p 8001:8001 \
  -e SESSION_SECRET="$(openssl rand -hex 32)" \
  -e STRIPE_SECRET_KEY="sk_live_..." \
  -v $(pwd)/data:/app/data \
  searei-backend:latest

# Or use docker-compose
docker-compose up -d
```

---

## 📦 Project Structure

```
safety-eval-mini/
├── src/
│   ├── service/
│   │   ├── api.py              # Main FastAPI app
│   │   ├── staging_api.py      # Staging endpoints
│   │   ├── staging_payments.py # Stripe integration
│   │   ├── staging_upload.py   # File uploads
│   │   ├── staging_admin.py    # Admin operations
│   │   ├── staging_db.py        # Database operations
│   │   ├── staging_models.py    # Data models
│   │   └── staging_notifications.py # Email/SMS
│   ├── store/
│   │   ├── staging_schema.py    # Database schema
│   │   └── init_db.py          # DB initialization
│   └── ...
├── config.example.yaml         # Config template
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker image
├── docker-compose.yml          # Docker Compose
└── README.md                   # Main documentation
```

---

## 🔄 Stripe Webhook Setup

1. **Create Webhook in Stripe Dashboard**
   - URL: `https://api.searei.com/api/v1/webhooks/stripe`
   - Events: `checkout.session.completed`, `payment_intent.succeeded`

2. **Get Webhook Secret**
   - Copy the webhook signing secret from Stripe
   - Add to `config.yaml` or environment variable

3. **Test Webhook**
   ```bash
   stripe listen --forward-to localhost:8001/api/v1/webhooks/stripe
   ```

---

## 📝 Environment-Specific Deployment

### Development
```bash
export ENV=development
export CORS_ALLOW_ORIGINS="http://localhost:3000,http://localhost:8000"
uvicorn service.api:app --reload
```

### Staging
```bash
export ENV=staging
export CORS_ALLOW_ORIGINS="https://staging.searei.com"
uvicorn service.api:app --workers 2
```

### Production
```bash
export ENV=production
export CORS_ALLOW_ORIGINS="https://searei.com,https://www.searei.com"
uvicorn service.api:app --workers 4 --host 0.0.0.0 --port 8001
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_staging_payments.py

# Run with coverage
pytest --cov=src --cov-report=html
```

---

## 📚 Additional Documentation

- **API Documentation**: See `docs/SERVICE.md`
- **Deployment Guide**: See `DEPLOYMENT_GUIDE.md`
- **Stripe Integration**: See `src/service/staging_payments.py`
- **Database Schema**: See `src/store/staging_schema.py`

---

## 🔗 Related Repositories

- **Marketing Site**: `/Users/samvardani/Projects/searei-marketing/`
- **Frontend Dashboard**: `dashboard/` directory in this repo

---

## 📞 Support

For issues or questions:
- Email: hello@searei.com
- Documentation: See `README.md` and `docs/` directory

---

**Last Updated**: January 2025  
**Version**: 2.1.0  
**License**: See `LICENSE` file

