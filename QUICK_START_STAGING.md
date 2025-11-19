# Quick Start - Virtual Staging Platform

## 🚀 Get Started in 3 Steps

### Step 1: Start the Server

```bash
cd /Users/samvardani/Projects/safety-eval-mini
PYTHONPATH=src uvicorn service.api:app --host 0.0.0.0 --port 8001 --reload
```

**Keep this terminal open!** The server must be running to use the platform.

### Step 2: Create Test Users

In a **new terminal window**, run:

```bash
cd /Users/samvardani/Projects/safety-eval-mini
PYTHONPATH=src python setup_staging_users.py
```

This creates:
- Client user: `client@example.com` / `ClientPass123!`
- Staff user: `staff@example.com` / `StaffPass123!`
- Admin user: `admin@example.com` / `AdminPass123!`

### Step 3: Open in Browser

Go to: **http://localhost:8001/staging/**

Login with any of the test credentials above.

---

## 📱 What You'll See

### Login Page
- Beautiful gradient background
- Professional login form
- Error handling

### Dashboard (After Login)
- **Overview Tab:** Stats and recent jobs
- **Jobs Tab:** All your staging jobs
- **Properties Tab:** Your property listings
- **Admin Tab:** Analytics (admin/manager only)

---

## 🔧 WordPress Setup

### Quick Install

1. **Copy plugin to WordPress:**
   ```bash
   cp -r wp-content/plugins/virtual-staging-platform /path/to/wordpress/wp-content/plugins/
   ```

2. **Activate in WordPress:**
   - Go to WordPress Admin → Plugins
   - Find "Virtual Staging Platform"
   - Click "Activate"

3. **Configure:**
   - Go to Settings → Staging Platform
   - Enter API URL: `http://localhost:8001` (or your production URL)
   - Save

4. **Use Shortcode:**
   Add `[virtual_staging]` to any page or post!

---

## 🐛 Troubleshooting

### Can't access /staging/

**Fix:** Make sure the server is running (Step 1). Check:
```bash
curl http://localhost:8001/healthz
```
Should return: `{"status":"ok"}`

### Login fails

**Fix:** Run the user setup script (Step 2) to create users.

### WordPress iframe blank

**Fix:** 
1. Check API URL in WordPress settings
2. Make sure API server is running
3. Check browser console (F12) for errors

---

## 📚 Full Documentation

See `STAGING_PLATFORM_SETUP.md` for complete instructions.

---

## 🎨 Design Features

- ✅ Modern, professional UI
- ✅ Purple/blue gradient theme
- ✅ Font Awesome icons
- ✅ Responsive design
- ✅ Status badges
- ✅ Loading states
- ✅ Error handling
- ✅ Empty states

---

## 🔗 Important URLs

- **Frontend:** http://localhost:8001/staging/
- **API Docs:** http://localhost:8001/docs
- **Health Check:** http://localhost:8001/healthz

---

**Need help?** Check `STAGING_PLATFORM_SETUP.md` for detailed troubleshooting.




