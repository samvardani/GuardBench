# Virtual Staging Platform - Complete Setup Guide

## Table of Contents
1. [Quick Start](#quick-start)
2. [Frontend Access](#frontend-access)
3. [WordPress Integration](#wordpress-integration)
4. [Full Page Design Overview](#full-page-design-overview)
5. [Troubleshooting](#troubleshooting)

## Quick Start

### 1. Start the API Server

```bash
# Navigate to project directory
cd /Users/samvardani/Projects/safety-eval-mini

# Activate virtual environment (if using one)
source .venv/bin/activate  # or: source venv/bin/activate

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Start the server
PYTHONPATH=src uvicorn service.api:app --host 0.0.0.0 --port 8001 --reload
```

The server will start on `http://localhost:8001`

**Important:** Keep this terminal window open while using the platform.

### 2. Create Test Users

Open a Python shell or create a script:

```python
from service.db import create_tenant, create_user

# Create tenant
tenant = create_tenant("Staging Company", slug="staging-co")
print(f"Tenant created: {tenant['name']} (ID: {tenant['tenant_id']})")

# Create client user
client = create_user(
    tenant["tenant_id"],
    "client@example.com",
    "ClientPass123!",
    role="client"
)
print(f"Client created: {client['email']}")

# Create staff user
staff = create_user(
    tenant["tenant_id"],
    "staff@example.com",
    "StaffPass123!",
    role="staff"
)
print(f"Staff created: {staff['email']}")

# Create admin user
admin = create_user(
    tenant["tenant_id"],
    "admin@example.com",
    "AdminPass123!",
    role="admin"
)
print(f"Admin created: {admin['email']}")
```

Save this as `create_test_users.py` and run:
```bash
PYTHONPATH=src python create_test_users.py
```

### 3. Access the Frontend

Once the server is running, open your browser:

**Main URL:** `http://localhost:8001/staging/index.html`

Or simply: `http://localhost:8001/staging/`

### 4. Login

Use the credentials you created:
- **Client:** `client@example.com` / `ClientPass123!`
- **Staff:** `staff@example.com` / `StaffPass123!`
- **Admin:** `admin@example.com` / `AdminPass123!`

## Frontend Access

### URLs Available:

- **Staging Platform:** `http://localhost:8001/staging/`
- **Dashboard (existing):** `http://localhost:8001/dashboard/`
- **API Docs:** `http://localhost:8001/docs`
- **Health Check:** `http://localhost:8001/healthz`

### What You'll See:

1. **Login Page:**
   - Professional gradient background
   - Email and password fields
   - Error handling
   - Loading states

2. **Dashboard (After Login):**
   - **Overview Tab:** Stats cards, recent jobs
   - **Jobs Tab:** Full job listing with status badges
   - **Properties Tab:** Property management
   - **Admin Tab:** Analytics (admin/manager only)

## WordPress Integration

### Option 1: WordPress Plugin (Recommended)

#### Step 1: Install the Plugin

1. Copy the plugin folder to your WordPress installation:
   ```bash
   cp -r wp-content/plugins/virtual-staging-platform /path/to/wordpress/wp-content/plugins/
   ```

2. Go to WordPress Admin → **Plugins**
3. Find "Virtual Staging Platform" and click **Activate**

#### Step 2: Configure Settings

1. Go to **Settings → Staging Platform**
2. Enter your API Base URL:
   - **Local development:** `http://localhost:8001`
   - **Production:** `https://api.yourdomain.com`
3. Set the default iframe height (default: 800px)
4. Click **Save Settings**

#### Step 3: Use the Shortcode

Add to any page or post:

```
[virtual_staging]
```

Or with custom height:

```
[virtual_staging height="1000px"]
```

#### Step 4: Use the Widget

1. Go to **Appearance → Widgets**
2. Find "Virtual Staging Platform" widget
3. Drag it to your sidebar or widget area
4. Configure title and height
5. Click **Save**

#### Step 5: Use Page Template

1. Create a new page in WordPress
2. In the page editor, look for "Page Attributes" → "Template"
3. Select "Virtual Staging Platform"
4. Publish the page

### Option 2: Direct iframe Embed

Add this HTML to any WordPress page (using a Custom HTML block):

```html
<iframe 
    src="http://localhost:8001/staging/" 
    width="100%" 
    height="800px" 
    frameborder="0"
    style="border: 1px solid #e5e7eb; border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);"
    allow="camera; microphone; payment; fullscreen"
></iframe>
```

**Note:** Replace `http://localhost:8001` with your production API URL.

### Option 3: Custom Page Template in Theme

If you want to add it to your theme:

1. Create `page-staging.php` in your active theme directory:

```php
<?php
/**
 * Template Name: Virtual Staging Platform
 */

get_header();
?>

<div id="staging-platform-container" style="width: 100%; min-height: calc(100vh - 200px); padding: 20px;">
    <iframe 
        src="<?php echo esc_url(get_option('vsp_api_base', 'http://localhost:8001')); ?>/staging/" 
        width="100%" 
        height="calc(100vh - 200px)" 
        frameborder="0"
        style="border: 1px solid #e5e7eb; border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);"
        allow="camera; microphone; payment; fullscreen"
    ></iframe>
</div>

<?php
get_footer();
```

2. Create a new page in WordPress
3. Select "Virtual Staging Platform" as the template
4. Publish the page

## Full Page Design Overview

### Login Page Features:
- ✅ Gradient purple background
- ✅ Centered white card with shadow
- ✅ Icon-enhanced form fields
- ✅ Error messages with icons
- ✅ Loading states with spinner
- ✅ Responsive design

### Dashboard Features:

#### Navigation Bar:
- Logo with icon
- Tab navigation (Overview, Jobs, Properties, Admin)
- Badge counters showing item counts
- User email and role display
- Logout button

#### Overview Tab:
- **Stats Cards:**
  - Total Jobs (purple icon)
  - Properties (blue icon)
  - Completed Jobs (green icon)
- **Recent Jobs Table:**
  - Last 5 jobs
  - Status badges (color-coded)
  - Quick actions

#### Jobs Tab:
- Full job listing table
- Status badges with icons:
  - 🟦 Scheduled (blue)
  - 🔄 In Progress (blue)
  - 🟨 Photos Ready (yellow)
  - ✅ Completed (green)
  - ❌ Cancelled (red)
- Job ID, Status, Scheduled Date, Priority, Created Date
- Empty state with helpful message

#### Properties Tab:
- Property listing table
- Address with location icon
- City, State, Status, Created Date
- Empty state with call-to-action

#### Admin Tab (Admin/Manager only):
- Analytics dashboard
- Stats cards:
  - Total Jobs
  - Jobs This Month
  - Total Revenue
  - Active Clients
- Job status breakdown

### Design Elements:
- ✅ Modern, clean UI
- ✅ Purple/blue color scheme
- ✅ Font Awesome icons throughout
- ✅ Hover effects on cards
- ✅ Responsive tables
- ✅ Loading spinners
- ✅ Empty states
- ✅ Error handling
- ✅ Status badges with colors
- ✅ Professional typography

## Troubleshooting

### Issue: "Cannot GET /staging/" or 404 Error

**Solution:**
1. **Check server is running:**
   ```bash
   curl http://localhost:8001/healthz
   ```
   Should return `{"status":"ok"}`

2. **Verify file exists:**
   ```bash
   ls -la dashboard/staging/index.html
   ```

3. **Restart the server:**
   ```bash
   # Stop the server (Ctrl+C)
   # Then restart:
   PYTHONPATH=src uvicorn service.api:app --host 0.0.0.0 --port 8001 --reload
   ```

4. **Check server logs** for any errors

### Issue: "401 Unauthorized" on Login

**Solution:**
1. Make sure you've created users (see Quick Start step 2)
2. Verify email/password are correct
3. Check that the tenant exists
4. Try creating a new user and logging in

### Issue: WordPress iframe not loading

**Solution:**
1. **Check CORS settings:**
   - The API should allow your WordPress domain
   - Check browser console for CORS errors

2. **Verify API URL:**
   - Make sure the API base URL in WordPress settings is correct
   - Test the URL directly in browser: `http://localhost:8001/staging/`

3. **Check iframe permissions:**
   - Make sure `allow` attribute includes needed permissions
   - Check browser console for security errors

4. **Network issues:**
   - If WordPress is on a different domain, ensure API is accessible
   - For production, use HTTPS for both WordPress and API

### Issue: Static files not serving

**Solution:**
The static files are mounted at `/staging`. Make sure:
- The `dashboard/staging` directory exists
- The `dashboard/staging/index.html` file exists
- The server has read permissions
- Check server logs for file access errors

### Issue: React/Babel not working

**Solution:**
1. Check browser console for JavaScript errors
2. Verify CDN links are loading (check Network tab)
3. Make sure `@babel/standalone` is loaded before the script
4. Try hard refresh (Ctrl+Shift+R or Cmd+Shift+R)

### Issue: API calls failing

**Solution:**
1. **Check API is running:**
   ```bash
   curl http://localhost:8001/healthz
   ```

2. **Check authentication:**
   - Verify token is being sent in Authorization header
   - Check browser Network tab for 401/403 errors

3. **Check CORS:**
   - API should allow requests from your frontend origin
   - Check browser console for CORS errors

## Production Deployment

### 1. Update API Base URL

Set environment variable:
```bash
export BASE_URL=https://api.yourdomain.com
```

### 2. Configure CORS

Update `CORS_ALLOW_ORIGINS` to include your WordPress domain:
```bash
export CORS_ALLOW_ORIGINS=https://yourwordpresssite.com,https://www.yourwordpresssite.com
```

### 3. Use HTTPS

Both WordPress and API should use HTTPS in production.

### 4. Set Environment Variables

```bash
# Stripe (for payments)
export STRIPE_SECRET_KEY=sk_live_...
export STRIPE_WEBHOOK_SECRET=whsec_...

# File Storage
export STORAGE_ROOT=/var/www/uploads/staging
export STORAGE_BASE_URL=https://cdn.yourdomain.com/staging

# Email/SMS (for notifications)
export EMAIL_ENABLED=true
export EMAIL_SERVICE_API_KEY=...
export SMS_ENABLED=true
export SMS_SERVICE_API_KEY=...
```

### 5. Update WordPress Settings

In WordPress Admin → Settings → Staging Platform:
- Change API Base URL to your production URL
- Test the connection

## Next Steps

1. **Customize Design:** Edit `dashboard/staging/index.html` and `app.jsx`
2. **Add Features:** Extend React components for:
   - Image upload UI
   - Calendar booking interface
   - Payment checkout flow
   - Job detail pages
3. **Configure Payments:** Set up Stripe keys
4. **Set Up Storage:** Configure cloud storage for images
5. **Deploy:** Follow production deployment steps

## Support

- **API Documentation:** `http://localhost:8001/docs`
- **Test Files:** Check `tests/test_staging_*.py` for examples
- **Server Logs:** Check terminal where server is running
- **Browser Console:** Check for JavaScript errors (F12)

## Quick Reference

### Create Users (Python)
```python
from service.db import create_tenant, create_user
tenant = create_tenant("Company Name", slug="company-slug")
user = create_user(tenant["tenant_id"], "email@example.com", "Password123!", role="client")
```

### Access URLs
- Frontend: `http://localhost:8001/staging/`
- API Docs: `http://localhost:8001/docs`
- Health: `http://localhost:8001/healthz`

### WordPress Shortcode
```
[virtual_staging]
[virtual_staging height="1000px"]
```

### Server Command
```bash
PYTHONPATH=src uvicorn service.api:app --host 0.0.0.0 --port 8001 --reload
```
