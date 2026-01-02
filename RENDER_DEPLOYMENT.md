# 🚀 Render Deployment Guide - AI SQL Assistant

Complete guide for deploying FastAPI backend and Streamlit frontend on Render (Free Tier).

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Quick Deploy (5 Minutes)](#quick-deploy)
4. [Manual Setup](#manual-setup)
5. [Environment Variables](#environment-variables)
6. [Troubleshooting](#troubleshooting)
7. [Cost & Limitations](#cost--limitations)

---

## ✅ Prerequisites

- [x] GitHub account with this repository
- [x] Render account (free): https://render.com/register
- [x] Groq API key: https://console.groq.com

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────┐
│  Frontend (Streamlit)                           │
│  • aisql-frontend.onrender.com                  │
│  • Port: $PORT (auto-assigned by Render)        │
│  • Calls backend via BACKEND_URL env var        │
└──────────────────┬──────────────────────────────┘
                   │ HTTPS API Calls
┌──────────────────▼──────────────────────────────┐
│  Backend (FastAPI)                              │
│  • aisql-backend.onrender.com                   │
│  • Port: $PORT (auto-assigned by Render)        │
│  • CORS configured for frontend URL             │
│  • Persistent disk for ChromaDB (1GB)           │
└─────────────────────────────────────────────────┘
```

**Key Points:**
- **Separate Services**: Backend and frontend deployed independently
- **Auto-Discovery**: Render auto-injects service URLs via environment variables
- **Free Tier**: Both services on free plan (cold starts after 15 min inactivity)
- **Persistent Storage**: Backend has 1GB disk for ChromaDB data

---

## 🚀 Quick Deploy (Recommended)

### Option A: Using Render Blueprint (Automated)

**Step 1: Push to GitHub**
```powershell
git add .
git commit -m "Add Render configuration"
git push origin main
```

**Step 2: Deploy on Render**
1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Blueprint"**
3. Connect your GitHub repository
4. Select **"AI_SQL_Assistant"** repository
5. Render will detect `render.yaml` and show 2 services:
   - `aisql-backend` (FastAPI)
   - `aisql-frontend` (Streamlit)
6. Click **"Apply"**

**Step 3: Configure Secrets**
1. Go to **"aisql-backend"** service → **"Environment"**
2. Add secret environment variable:
   - Key: `GROQ_API_KEY`
   - Value: `your_groq_api_key_here`
3. Click **"Save Changes"**

**Step 4: Wait for Deployment** (~10-15 minutes first time)
- Backend will build first
- Frontend will build after backend is ready
- Watch logs in Render dashboard

**Step 5: Access Your App!**
```
Frontend URL: https://aisql-frontend.onrender.com
Backend API: https://aisql-backend.onrender.com
API Docs: https://aisql-backend.onrender.com/docs
```

---

## 🔧 Manual Setup (Alternative)

If you prefer manual setup without blueprint:

### Deploy Backend

**Step 1: Create Backend Service**
1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Connect GitHub repository
4. Configure:
   - **Name**: `aisql-backend`
   - **Region**: Oregon (US West)
   - **Branch**: `main`
   - **Root Directory**: Leave empty
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```bash
     pip install --upgrade pip && pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     uvicorn backend.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Plan**: `Free`

**Step 2: Add Backend Environment Variables**
| Key | Value | Secret |
|-----|-------|--------|
| `PYTHON_VERSION` | `3.11.0` | No |
| `GROQ_API_KEY` | `your_groq_api_key` | Yes |
| `ENVIRONMENT` | `production` | No |
| `ENABLE_TINYLLAMA` | `false` | No |
| `AUTO_RETRY_ON_ERROR` | `true` | No |
| `LOG_LEVEL` | `INFO` | No |

**Step 3: Add Persistent Disk to Backend**
1. In backend service, go to **"Disks"** tab
2. Click **"Add Disk"**
3. Configure:
   - **Name**: `chromadb-storage`
   - **Mount Path**: `/opt/render/project/src/chromadb_data`
   - **Size**: `1 GB` (free tier limit)
4. Click **"Create"**
5. Service will redeploy automatically

**Step 4: Note Backend URL**
Once deployed, copy the URL (e.g., `https://aisql-backend-xyz.onrender.com`)

---

### Deploy Frontend

**Step 1: Create Frontend Service**
1. Click **"New +"** → **"Web Service"**
2. Connect same GitHub repository
3. Configure:
   - **Name**: `aisql-frontend`
   - **Region**: Oregon (US West)
   - **Branch**: `main`
   - **Root Directory**: Leave empty
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```bash
     pip install --upgrade pip && pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     streamlit run frontend/app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false
     ```
   - **Plan**: `Free`

**Step 2: Add Frontend Environment Variables**
| Key | Value | Secret |
|-----|-------|--------|
| `PYTHON_VERSION` | `3.11.0` | No |
| `BACKEND_URL` | `https://aisql-backend-xyz.onrender.com` | No |

Replace `aisql-backend-xyz.onrender.com` with your actual backend URL from Step 4 above.

**Step 3: Update Backend CORS**
1. Go back to **backend service** → **"Environment"**
2. Add variable:
   - Key: `FRONTEND_URL`
   - Value: `https://aisql-frontend-abc.onrender.com`
3. Replace with your actual frontend URL
4. Click **"Save Changes"** (backend will redeploy)

---

## 🔐 Environment Variables Reference

### Backend (`aisql-backend`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | Auto-set | - | Render auto-assigns port (do not set manually) |
| `GROQ_API_KEY` | ⚠️ **Required** | - | Your Groq API key from console.groq.com |
| `FRONTEND_URL` | ⚠️ **Required** | - | Frontend service URL for CORS |
| `PYTHON_VERSION` | Recommended | `3.11.0` | Python runtime version |
| `ENVIRONMENT` | Optional | `development` | Set to `production` for Render |
| `LOG_LEVEL` | Optional | `INFO` | Logging level (DEBUG/INFO/WARNING/ERROR) |
| `ENABLE_TINYLLAMA` | Optional | `false` | Disable local model on Render (saves memory) |
| `AUTO_RETRY_ON_ERROR` | Optional | `true` | Enable SQL auto-correction |

### Frontend (`aisql-frontend`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | Auto-set | - | Render auto-assigns port (do not set manually) |
| `BACKEND_URL` | ⚠️ **Required** | - | Backend service URL (e.g., https://aisql-backend.onrender.com) |
| `PYTHON_VERSION` | Recommended | `3.11.0` | Python runtime version |

---

## 🐛 Troubleshooting

### Issue 1: "502 Bad Gateway" or "Service Unavailable"

**Cause**: Cold start (free tier spins down after 15 min inactivity)

**Solution**: Wait 30-60 seconds for service to wake up. First request after cold start takes longer.

**Optimization**:
- Use paid plan ($7/month) for always-on service
- Or ping your service every 10 minutes to keep it warm:
  ```bash
  # Health check endpoint
  curl https://aisql-backend.onrender.com/health
  ```

---

### Issue 2: "Cannot connect to backend"

**Symptoms**: Frontend loads but shows connection errors

**Diagnosis**:
1. Check backend is running: Visit `https://aisql-backend-xyz.onrender.com/health`
2. Should return: `{"status": "healthy"}`

**Solutions**:
- **Check BACKEND_URL**: Frontend environment variable must match backend URL exactly
- **Check CORS**: Backend must have `FRONTEND_URL` set correctly
- **Check logs**: Backend → "Logs" tab for errors
- **Verify HTTPS**: Both services must use `https://` URLs

---

### Issue 3: "File upload fails with 403"

**Cause**: Render free tier has limited disk write permissions

**Solution**: 
- Backend has persistent disk mounted at `/opt/render/project/src/chromadb_data`
- Temp files go to `/tmp` (ephemeral, cleared on restart)
- For production file uploads, use external storage:
  - AWS S3
  - Cloudinary
  - Render Disk (persistent, already configured for ChromaDB)

**Current behavior**: File uploads work but files are lost on cold start (free tier limitation)

---

### Issue 4: "Out of memory" or service crashes

**Cause**: Free tier has 512MB RAM limit

**Solutions**:
1. **Disable TinyLlama**: Already done via `ENABLE_TINYLLAMA=false`
2. **Reduce ChromaDB cache**: Edit backend if needed
3. **Upgrade to paid plan**: $7/month for 2GB RAM
4. **Optimize imports**: Remove unused heavy libraries

---

### Issue 5: "Build failed"

**Common causes**:
- Missing `requirements.txt`
- Python version mismatch
- Dependency conflicts

**Solutions**:
1. Check build logs in Render dashboard
2. Verify `requirements.txt` has all dependencies
3. Pin versions:
   ```txt
   fastapi==0.104.0
   uvicorn[standard]==0.24.0
   streamlit==1.28.0
   ```
4. Test build locally:
   ```powershell
   pip install -r requirements.txt
   ```

---

### Issue 6: "ChromaDB data lost after restart"

**Cause**: Free tier restarts on inactivity, ephemeral storage cleared

**Solution**: Persistent disk is configured for backend (`/chromadb_data`)
- Data persists across restarts
- **Limitation**: Disk is cleared if service is deleted
- **Backup**: Export ChromaDB data periodically

---

### Issue 7: Database connection fails (localhost)

**Symptom**: "Cannot connect to localhost:5432"

**Explanation**: Render containers cannot access `localhost` databases

**Solutions**:
- **External databases only**: Use managed database services:
  - Render PostgreSQL (free 90 days, then $7/month)
  - AWS RDS free tier
  - ElephantSQL (PostgreSQL free tier)
  - PlanetScale (MySQL free tier)
- **SQLite**: Works via file upload (stored on persistent disk)

---

## 💰 Cost & Limitations

### Free Tier Specifications

**Backend Service (Free)**
- **RAM**: 512 MB
- **CPU**: Shared
- **Disk**: 1 GB persistent storage (configured)
- **Bandwidth**: 100 GB/month
- **Cold starts**: Spins down after 15 min inactivity
- **Wake-up time**: 30-60 seconds

**Frontend Service (Free)**
- **RAM**: 512 MB
- **CPU**: Shared
- **Cold starts**: Spins down after 15 min inactivity
- **Wake-up time**: 30-60 seconds

**Total Cost**: **$0/month** (both services)

---

### Paid Plans (Optional Upgrades)

**Starter Plan ($7/month per service)**
- **RAM**: 2 GB (4x more)
- **Always on**: No cold starts
- **Faster**: Dedicated CPU
- **Custom domains**: Included

**For production use**: Recommend upgrading both services = $14/month

---

### Free Tier Limitations

❌ **Cold Starts**: 15-minute inactivity timeout  
❌ **Memory**: 512MB (tight for ML workloads)  
❌ **Build time**: Can be slow (10-15 min first build)  
❌ **Custom domains**: Not available  
❌ **SSL**: Render provides, but uses `.onrender.com` domain  

✅ **What Works Well**:  
✅ Auto-deployment on git push  
✅ Free SSL/HTTPS  
✅ Health check monitoring  
✅ Log persistence (7 days)  
✅ Environment variable secrets  
✅ Persistent disk (1GB for backend)  

---

## 📊 Performance Optimizations

### Backend Optimizations (Already Implemented)

```python
# backend/main.py
uvicorn.run(
    app,
    host="0.0.0.0",
    port=PORT,
    timeout_keep_alive=30,      # Keep connections alive longer
    limit_concurrency=50,        # Prevent memory overload
    limit_max_requests=1000,     # Restart worker after 1K requests
)
```

### Cold Start Mitigation

**Option 1: External Ping Service (Free)**
Use UptimeRobot or similar:
1. Sign up at https://uptimerobot.com (free)
2. Add HTTP(s) monitor:
   - URL: `https://aisql-backend.onrender.com/health`
   - Interval: Every 10 minutes
3. Keeps service warm 24/7

**Option 2: GitHub Actions Cron (Free)**
Create `.github/workflows/keep-warm.yml`:
```yaml
name: Keep Render Warm
on:
  schedule:
    - cron: '*/10 * * * *'  # Every 10 minutes
jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - name: Ping backend
        run: curl https://aisql-backend.onrender.com/health
      - name: Ping frontend
        run: curl https://aisql-frontend.onrender.com
```

---

## 🔄 CI/CD (Auto-Deploy on Push)

Already configured! Render automatically:
1. Detects git push to `main` branch
2. Pulls latest code
3. Runs build command
4. Runs start command
5. Performs health check
6. Routes traffic to new deployment

**To trigger deployment**:
```powershell
git add .
git commit -m "Update feature"
git push origin main
# Render auto-deploys in ~5 minutes
```

---

## ✅ Post-Deployment Checklist

After successful deployment:

- [ ] Backend health check works: `https://aisql-backend.onrender.com/health`
- [ ] Frontend loads: `https://aisql-frontend.onrender.com`
- [ ] Can enter Groq API key in frontend
- [ ] Can connect to external database or upload SQLite file
- [ ] SQL generation works (test with simple question)
- [ ] Results display correctly
- [ ] Explanations generate
- [ ] RAG examples can be added
- [ ] Performance metrics accessible: `https://aisql-backend.onrender.com/metrics`
- [ ] Error logs available in Render dashboard
- [ ] Environment variables configured correctly

---

## 📝 Important URLs

After deployment, bookmark these:

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend** | `https://aisql-frontend.onrender.com` | Main app UI |
| **Backend API** | `https://aisql-backend.onrender.com` | API endpoint |
| **API Docs** | `https://aisql-backend.onrender.com/docs` | Interactive API docs |
| **Health Check** | `https://aisql-backend.onrender.com/health` | Backend status |
| **Metrics** | `https://aisql-backend.onrender.com/metrics` | Performance stats |
| **Render Dashboard** | `https://dashboard.render.com` | Manage services |

---

## 🎉 Success!

Your AI SQL Assistant is now deployed on Render!

**Next steps**:
1. Share frontend URL with users
2. Monitor usage in Render dashboard
3. Set up UptimeRobot to prevent cold starts
4. Consider upgrading to paid plan for production use

**Need help?**
- Check logs in Render dashboard
- Review troubleshooting section above
- Open GitHub issue

**Happy querying! 🚀**
