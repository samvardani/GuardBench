# Virtual Staging Platform - Complete Guide

## 🎯 Quick Access

**Frontend URL:** `http://localhost:8001/staging/`

## 📋 Complete Setup Instructions

### 1. Start the API Server

```bash
cd /Users/samvardani/Projects/safety-eval-mini
PYTHONPATH=src uvicorn service.api:app --host 0.0.0.0 --port 8001 --reload
```

**Important:** Keep this terminal window open. The server must be running.

### 2. Create Test Users

Open a **new terminal** and run:

```bash
cd /Users/samvardani/Projects/safety-eval-mini
PYTHONPATH=src python setup_staging_users.py
```

This creates:
- **Client:** `client@example.com` / `ClientPass123!`
- **Staff:** `staff@example.com` / `StaffPass123!`
- **Admin:** `admin@example.com` / `AdminPass123!`

### 3. Access the Frontend

Open your browser and go to:

**http://localhost:8001/staging/**

Login with any of the credentials above.

---

## 🎨 Full Page Design Features

### Login Page
- **Gradient Background:** Purple to blue gradient
- **Centered Card:** White card with shadow
- **Form Fields:** Email and password with icons
- **Error Handling:** Red error messages with icons
- **Loading States:** Spinner during login
- **Responsive:** Works on mobile and desktop

### Dashboard (After Login)

#### Navigation Bar
- **Logo:** "Virtual Staging" with home icon
- **Tabs:** Overview, Jobs, Properties, Admin (role-based)
- **Badges:** Count indicators on tabs
- **User Info:** Email and role display
- **Logout Button:** Top right

#### Overview Tab
- **Stats Cards (3):**
  - Total Jobs (purple icon)
  - Properties (blue icon)  
  - Completed Jobs (green icon)
- **Recent Jobs Table:**
  - Last 5 jobs
  - Status badges (color-coded)
  - Job ID, Status, Created Date, Priority
- **Quick Actions:** Buttons to create new property/job

#### Jobs Tab
- **Full Job Listing:**
  - Table view with all jobs
  - Status badges with icons:
    - 🔵 Scheduled (blue)
    - 🔄 In Progress (blue)
    - 🟡 Photos Ready (yellow)
    - ✅ Completed (green)
    - ❌ Cancelled (red)
  - Columns: Job ID, Status, Scheduled Date, Priority, Created
- **Empty State:** Helpful message when no jobs
- **Create Button:** "New Job" button at top

#### Properties Tab
- **Property Listing:**
  - Table view with all properties
  - Address with location icon
  - City, State, Status, Created Date
- **Empty State:** Message to add first property
- **Create Button:** "New Property" button at top

#### Admin Tab (Admin/Manager Only)
- **Analytics Dashboard:**
  - Total Jobs
  - Jobs This Month
  - Total Revenue (formatted as currency)
  - Active Clients Count
- **Stats Cards:** 4-column grid layout

### Design Elements
- ✅ Modern, clean UI with Tailwind CSS
- ✅ Purple/blue color scheme
- ✅ Font Awesome icons throughout
- ✅ Hover effects on cards and rows
- ✅ Responsive tables (scrollable on mobile)
- ✅ Loading spinners
- ✅ Empty states with icons
- ✅ Error handling with messages
- ✅ Status badges with colors and icons
- ✅ Professional typography

---

## 🔌 WordPress Integration

### Method 1: WordPress Plugin (Easiest)

1. **Copy plugin folder:**
   ```bash
   cp -r wp-content/plugins/virtual-staging-platform /path/to/your/wordpress/wp-content/plugins/
   ```

2. **Activate in WordPress:**
   - Go to WordPress Admin → Plugins
   - Find "Virtual Staging Platform"
   - Click "Activate"

3. **Configure:**
   - Go to **Settings → Staging Platform**
   - Enter API Base URL: `http://localhost:8001` (or your production URL)
   - Set default height: `800` (or your preference)
   - Click **Save Settings**

4. **Use Shortcode:**
   Add to any page or post:
   ```
   [virtual_staging]
   ```
   
   Or with custom height:
   ```
   [virtual_staging height="1000px"]
   ```

5. **Use Widget:**
   - Go to **Appearance → Widgets**
   - Find "Virtual Staging Platform"
   - Drag to sidebar/widget area
   - Configure and save

6. **Use Page Template:**
   - Create new page
   - Select "Virtual Staging Platform" template
   - Publish

### Method 2: Direct iframe (Quick Test)

Add this HTML block to any WordPress page:

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

---

## 🐛 Troubleshooting

### Problem: Can't access http://localhost:8001/staging/

**Solutions:**
1. ✅ Make sure server is running (check terminal)
2. ✅ Verify port 8001 is not in use: `lsof -i :8001`
3. ✅ Check file exists: `ls dashboard/staging/index.html`
4. ✅ Restart server: Stop (Ctrl+C) and restart
5. ✅ Check server logs for errors

### Problem: Login fails with 401

**Solutions:**
1. ✅ Run user setup script: `PYTHONPATH=src python setup_staging_users.py`
2. ✅ Verify credentials are correct
3. ✅ Check tenant exists in database
4. ✅ Check server logs for authentication errors

### Problem: WordPress iframe is blank

**Solutions:**
1. ✅ Check API URL in WordPress settings
2. ✅ Verify API server is running
3. ✅ Check browser console (F12) for errors
4. ✅ Test API URL directly in browser
5. ✅ Check CORS settings (if WordPress on different domain)

### Problem: React/Babel errors in console

**Solutions:**
1. ✅ Check CDN links are loading (Network tab)
2. ✅ Verify `@babel/standalone` loads before script
3. ✅ Hard refresh browser (Ctrl+Shift+R)
4. ✅ Check for JavaScript errors in console

### Problem: API calls return 401/403

**Solutions:**
1. ✅ Check token is saved: `localStorage.getItem('staging-auth')`
2. ✅ Verify Authorization header in Network tab
3. ✅ Try logging out and back in
4. ✅ Check user role has required permissions

---

## 📁 File Structure

```
dashboard/staging/
├── index.html          # Main HTML file with React app
└── app.jsx            # React application code

wp-content/plugins/virtual-staging-platform/
├── virtual-staging-platform.php  # WordPress plugin
└── templates/
    └── page-staging.php          # Page template

src/service/
├── staging_api.py      # Main API endpoints
├── staging_db.py       # Database operations
├── staging_models.py   # Pydantic models
├── staging_upload.py   # Image upload endpoints
├── staging_payments.py  # Stripe integration
├── staging_admin.py     # Admin endpoints
└── staging_notifications.py  # Email/SMS notifications
```

---

## 🚀 Production Deployment

### 1. Update Environment Variables

```bash
export BASE_URL=https://api.yourdomain.com
export CORS_ALLOW_ORIGINS=https://yourwordpresssite.com
export STRIPE_SECRET_KEY=sk_live_...
export STRIPE_WEBHOOK_SECRET=whsec_...
```

### 2. Update WordPress Settings

- Change API Base URL to production URL
- Test connection

### 3. Use HTTPS

Both WordPress and API must use HTTPS in production.

---

## 📞 Support

- **Full Documentation:** See `STAGING_PLATFORM_SETUP.md`
- **Quick Start:** See `QUICK_START_STAGING.md`
- **API Docs:** http://localhost:8001/docs
- **Health Check:** http://localhost:8001/healthz

---

## ✅ Checklist

Before using:
- [ ] Server is running on port 8001
- [ ] Test users are created
- [ ] Can access http://localhost:8001/staging/
- [ ] Can log in successfully
- [ ] Dashboard loads correctly

For WordPress:
- [ ] Plugin is installed and activated
- [ ] API URL is configured
- [ ] Shortcode works on test page
- [ ] Iframe loads correctly

---

**Ready to go!** Start the server and visit http://localhost:8001/staging/




