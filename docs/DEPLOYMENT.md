# 🚀 Deployment

Live deployment links and status for Visionex project.

## Current Deployment Status

| Component | Platform | Status | Link |
|-----------|----------|--------|------|
| **Frontend** | Vercel | 🔄 Pending | [Frontend App](https://visionex-frontend.vercel.app) |
| **Backend API** | Hugging Face Spaces | 🟢 Building | [HF Spaces Backend](https://huggingface.co/spaces/ShaibinkB/visionex-backend) |
| **Documentation** | GitHub Pages | ✅ Live | [Project Docs](https://shaibinkb16.github.io/Visionex/) |

---

## 🔗 API Endpoints

### Backend API (HF Spaces)
```
Base URL: https://huggingface.co/spaces/ShaibinkB/visionex-backend
```

**Available Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/extract` | Upload image/PDF for extraction |
| `GET` | `/documents` | List all extracted documents |
| `GET` | `/documents/{id}` | Get specific document |
| `POST` | `/query` | Ask question about document |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Interactive API documentation |

### Example Usage

```bash
# Extract from image
curl -X POST "https://huggingface.co/spaces/ShaibinkB/visionex-backend/extract" \
  -F "file=@receipt.jpg"

# Get documents
curl "https://huggingface.co/spaces/ShaibinkB/visionex-backend/documents"

# Health check
curl "https://huggingface.co/spaces/ShaibinkB/visionex-backend/health"
```

---

## 🎯 Frontend

**Vercel Deployment:**
- URL: `https://visionex-frontend.vercel.app`
- Repository: [shaibinkb16/Visionex](https://github.com/shaibinkb16/Visionex)
- Branch: `main`

**Configuration:**
```javascript
// src/services/api.js
const API_BASE_URL = "https://huggingface.co/spaces/ShaibinkB/visionex-backend";
```

---

## 🧠 Backend API

**Hugging Face Spaces:**
- URL: `https://huggingface.co/spaces/ShaibinkB/visionex-backend`
- Repository: [ShaibinkB/visionex-backend](https://huggingface.co/spaces/ShaibinkB/visionex-backend)
- SDK: Docker
- Hardware: CPU Basic (2 vCPU + 16 GB RAM) — Free Tier

**Features:**
- 📄 OCR (EasyOCR)
- 🧠 NER (LayoutLMv3 ONNX)
- 💬 LLM Fallback (Groq + Gemini)
- 📦 MongoDB Storage
- ⚡ Rate Limiting
- 🌐 CORS Support

**Model Caching:**
- First request: ~1-2 minutes (auto-downloads from HF Hub)
- Subsequent requests: Instant (uses cache)

---

## 🔐 Environment Configuration

### Backend Secrets (HF Spaces)

Set in **Settings → Repository Secrets**:

```env
MONGODB_URI=mongodb://your-connection-string
GROQ_API_KEY=gsk_your_groq_key
GEMINI_API_KEY=your_google_key
HF_MODEL_ID=your_hf_model_id
CONFIDENCE_THRESHOLD=0.75
CORS_ORIGIN=https://visionex-frontend.vercel.app
ENV=production
```

### Frontend Environment (Vercel)

Set in **Settings → Environment Variables**:

```env
VITE_API_BASE_URL=https://huggingface.co/spaces/ShaibinkB/visionex-backend
```

---

## 📊 Architecture

```
┌─────────────────────────────┐
│   Frontend (Vercel)         │
│   - React + Vite            │
│   - Modern UI/UX            │
└──────────────┬──────────────┘
               │ HTTPS
               ▼
┌─────────────────────────────┐
│   Backend API (HF Spaces)   │
│   - FastAPI                 │
│   - Docker Container        │
│                             │
│  ┌─────────────────────┐    │
│  │ OCR (EasyOCR)       │    │
│  │ NER (LayoutLMv3)    │    │
│  │ LLM (Groq/Gemini)   │    │
│  └─────────────────────┘    │
└──────────────┬──────────────┘
               │
               ▼
        ┌─────────────┐
        │  MongoDB    │
        │  Database   │
        └─────────────┘
```

---

## 🛠️ Deployment Instructions

### Frontend (Vercel)

1. **Connect GitHub**
   - Go to [Vercel Dashboard](https://vercel.com)
   - Import `shaibinkb16/Visionex` repository
   - Root Directory: `frontend`
   - Framework: Vite

2. **Set Environment**
   ```env
   VITE_API_BASE_URL=https://huggingface.co/spaces/ShaibinkB/visionex-backend
   ```

3. **Deploy**
   - Auto-deploys on push to `main`

### Backend (HF Spaces)

1. **Create Space**
   - Go to [HF Spaces](https://huggingface.co/spaces)
   - Create new Space with Docker SDK
   - Connect to `ShaibinkB/visionex-backend` repo

2. **Add Secrets**
   - Settings → Repository Secrets
   - Add all environment variables

3. **Deploy**
   - Auto-builds and deploys on push

---

## 🔍 Monitoring & Logs

### Backend Logs
```bash
# View HF Spaces build logs
# Go to: https://huggingface.co/spaces/ShaibinkB/visionex-backend/logs
```

### Frontend Logs
```bash
# View Vercel deployment logs
# Go to: https://vercel.com/shaibinkb16/visionex/deployments
```

---

## 📱 Testing the API

### Using cURL

```bash
# Test extraction
curl -X POST "https://huggingface.co/spaces/ShaibinkB/visionex-backend/extract" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test_image.jpg"

# Get all documents
curl "https://huggingface.co/spaces/ShaibinkB/visionex-backend/documents"

# Health check
curl "https://huggingface.co/spaces/ShaibinkB/visionex-backend/health"
```

### Using API Docs

Visit: `https://huggingface.co/spaces/ShaibinkB/visionex-backend/docs`

Interactive Swagger UI for testing all endpoints.

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| API timeout | First request downloads models (wait 1-2 min) |
| CORS error | Check `CORS_ORIGIN` in backend secrets |
| Model not found | Verify `HF_MODEL_ID` in secrets |
| 503 Service Unavailable | HF Space still building, check logs |

---

## 📞 Support

- **GitHub Issues**: [Create issue](https://github.com/shaibinkb16/Visionex/issues)
- **HF Spaces**: [Community tab](https://huggingface.co/spaces/ShaibinkB/visionex-backend/community)

---

**Last Updated:** March 29, 2026  
**Status:** 🟢 Production Ready
