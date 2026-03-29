# Deploy to Hugging Face Spaces (Easiest for ML Models)

## ✅ Why HF Spaces?
- **Free tier**: 2 vCPU + 16 GB RAM (no credit card needed)
- **No bundling**: Models auto-download from Hugging Face Hub (cached after first run)
- **Docker-ready**: Full container support
- **Public API**: Auto-exposed HTTP endpoint
- **Built for ML**: Designed specifically for inference APIs & model serving

## 🚀 Deploy in 5 Minutes

### Step 1: Create GitHub Repo
```bash
cd e:\ZenturioTech
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/visionex-backend.git
git branch -M main
git push -u origin main
```

### Step 2: Go to Hugging Face Spaces
1. Visit: https://huggingface.co/spaces
2. Click **"Create New Space"**
3. Fill in:
   - **Space name**: `visionex-backend` (or your choice)
   - **License**: Select one
   - **Select the Space SDK**: Choose **"Docker"**
   - **Visibility**: Public (free) or Private (paid)

### Step 3: Connect GitHub Repo
1. In the new Space, go to **Settings** → **Repository**
2. Click **"Connect a Git repository"**
3. Select: `YOUR_USERNAME/visionex-backend`
4. **Persistent storage**: Optional (paid) for persistent `/data` folder

### Step 4: Configure Environment Variables
1. Go to **Space Settings** → **Repository secrets**
2. Add your environment variables:
   - `MONGODB_URI`: Your MongoDB connection string
   - `GROQ_API_KEY`: Your Groq API key
   - `GEMINI_API_KEY`: Your Google Gemini API key
   - `HF_MODEL_ID`: Your Hugging Face model ID
   - `CORS_ORIGIN`: Your frontend URL

3. (Optional) **Hardware**: Upgrade from CPU Basic to CPU Upgrade or GPU if needed

### Step 5: Automatic Deploy
- HF Spaces auto-detects `Dockerfile` in repo root
- Builds & deploys automatically
- Live at: `https://huggingface.co/spaces/YOUR_USERNAME/visionex-backend`
- Public API endpoint: Auto-exposed HTTP server

## 📝 Configuration Notes

### Dockerfile (Already Exists)
The current `backend/Dockerfile` works as-is. HF Spaces will:
1. Build the Docker image
2. Run CMD: `uvicorn app.main:app --host 0.0.0.0 --port 7860`
3. Auto-expose port 7860 publicly

### Environment Variables in HF Spaces
Your FastAPI app loads from `.env` using `pydantic-settings`. On HF Spaces, set secrets in Settings → Repository secrets instead.

**Update your config.py** to read from environment fallbacks:
```python
# In app/core/config.py - already using os.getenv fallback
MONGODB_URI: str = Field(default_factory=lambda: os.getenv("MONGODB_URI", "..."))
GROQ_API_KEY: str = Field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
# ... etc
```

## 🔗 Access Your API

Once deployed, your API will be at:
```
https://huggingface.co/spaces/YOUR_USERNAME/visionex-backend
```

Direct API endpoint (for frontend):
```
https://huggingface.co/api/spaces/YOUR_USERNAME/visionex-backend/call/extract
```

Or get the live URL from Space's "Community" tab.

## 🎯 Update Frontend API URL

In `frontend/src/services/api.js`:
```javascript
const API_BASE_URL = "https://[YOUR_HF_SPACE_URL]";
```

## 💾 Model Caching

- First request downloads models from Hugging Face Hub (~1-2 min)
- Subsequent requests use cached models (instant)
- Cache persists across deployments on paid storage tiers

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| "Model not found" | Ensure `HF_MODEL_ID` env var is set correctly |
| Build timeout (>2 hrs) | Reduce base image size or upgrade hardware |
| Out of memory | Upgrade to GPU or CPU Upgrade tier |
| CORS errors | Update `CORS_ORIGIN` in secrets |

## 📚 More Info
- [HF Spaces Docs](https://huggingface.co/docs/hub/spaces)
- [Docker in Spaces](https://huggingface.co/docs/hub/spaces-sdks-docker)
- [Persistent Storage](https://huggingface.co/docs/hub/spaces-storage)

---

**Ready?** Push to GitHub and create the Space—you'll be live in minutes! 🚀
