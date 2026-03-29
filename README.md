# Visionex — End-to-End Document Extraction & Grounded QA

A production-ready system for automated receipt extraction with structured field recognition (NER + rule-based + LLM fallback) and natural language question-answering grounded in extracted data.

**Live Demo**: https://frontend-omega-ten-28.vercel.app

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [System Architecture](#system-architecture)
3. [Technology Stack](#technology-stack)
4. [Data Flow & Processes](#data-flow--processes)
5. [API Documentation](#api-documentation)
6. [Setup & Local Development](#setup--local-development)
7. [Production Deployment](#production-deployment)
8. [Model Training & Export](#model-training--export)
9. [Development Guide](#development-guide)
10. [Troubleshooting](#troubleshooting)
11. [Limitations & Future Work](#limitations--future-work)

---

## Quick Start

### Live Deployment

| Service | URL | Status |
|---------|-----|--------|
| **Frontend** | https://frontend-omega-ten-28.vercel.app | ✅ Live |
| **Backend API** | https://shaibinkb16082002-visionex-backend.hf.space | ✅ Live |
| **API Docs** | https://shaibinkb16082002-visionex-backend.hf.space/docs | ✅ Live |
| **Health Check** | https://shaibinkb16082002-visionex-backend.hf.space/health | ✅ Live |

**Try it now**: Visit the frontend link above and upload a receipt image. Extract fields and ask questions about the receipt in natural language.

### Local Development (5 mins)

```bash
# Clone repo
git clone https://github.com/shaibinkb16/Visionex.git
cd Visionex

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate (Windows)
pip install -r requirements.txt
cp .env.example .env  # and fill in your API keys
uvicorn app.main:app --reload --port 8000

# Frontend setup (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and start extracting receipts.

---

## System Architecture

### High-Level Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                         User Browser                                │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  React + Vite Frontend (Vercel)                              │  │
│  │  - Upload form with preview                                  │  │
│  │  - Real-time pipeline visualization                          │  │
│  │  - Document list & chat interface                            │  │
│  │  - Question answering with document picker                   │  │
│  └────────────────────┬─────────────────────────────────────────┘  │
└─────────────────────┼──────────────────────────────────────────────┘
                      │ HTTPS (REST API calls)
                      ▼
┌────────────────────────────────────────────────────────────────────┐
│              FastAPI Backend (HF Spaces Docker)                    │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Input Processing                                            │  │
│  │  - File validation & multipart upload handling               │  │
│  │  - MIME type detection (image/pdf)                           │  │
│  └────────────────────┬─────────────────────────────────────────┘  │
│                       ▼                                             │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  OCR Pipeline (EasyOCR)                                      │  │
│  │  - Converts images/PDFs to text + bounding boxes             │  │
│  │  - Per-word coordinates for layout-aware models              │  │
│  │  - Cache: first run ~10s, subsequent runs instant            │  │
│  └────────────────────┬─────────────────────────────────────────┘  │
│                       ▼                                             │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  NER + Entity Extraction (LayoutLMv3 ONNX)                   │  │
│  │  - Fine-tuned on CORD dataset for receipt fields             │  │
│  │  - Token classification: TOTAL, DATE, VENDOR, RECEIPT_ID     │  │
│  │  - Confidence thresholding (default: 0.75)                   │  │
│  │  - Span aggregation & deduplication                          │  │
│  └────────────────────┬─────────────────────────────────────────┘  │
│                       ▼                                             │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Post-Processing & Rule-Based Extraction                     │  │
│  │  - Vendor: first MENU span matching shop keywords            │  │
│  │  - Total: PRICE span following "total" label or largest      │  │
│  │  - Date: regex patterns for multiple formats (d/m/y, etc)    │  │
│  │  - Receipt ID: alphanumeric patterns after bill/invoice      │  │
│  │  - Fallback: if NER confidence < threshold                   │  │
│  └────────────────────┬─────────────────────────────────────────┘  │
│                       ▼                                             │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  LLM Fallback (Optional: Groq/Gemini)                        │  │
│  │  - Fill only missing fields after NER + rules                │  │
│  │  - Strict JSON schema output                                 │  │
│  │  - Temperature = 0 for reproducibility                       │  │
│  │  - Graceful degradation if API key not set                   │  │
│  └────────────────────┬─────────────────────────────────────────┘  │
│                       ▼                                             │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Storage (MongoDB Atlas)                                     │  │
│  │  - Extracted fields (normalized JSON)                        │  │
│  │  - OCR text & raw file bytes (for preview)                   │  │
│  │  - Pipeline trace & timestamps                               │  │
│  │  - Document metadata (filename, upload date)                 │  │
│  └────────────────────┬─────────────────────────────────────────┘  │
│                       ▼                                             │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Question Answering (Groq + Gemini Fallback)                │  │
│  │  - System prompt: "Answer ONLY from this extracted JSON"      │  │
│  │  - Strict grounding: no hallucinations outside data           │  │
│  │  - Multi-document: user picks doc or uses latest              │  │
│  │  - Graceful degradation if LLM unavailable                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                       ▼                                             │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  API Response                                                │  │
│  │  - Extraction: JSON fields + confidence scores                │  │
│  │  - QA: answer string + traced field source                    │  │
│  │  - Status tracking for long-running operations                │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

### Component Breakdown

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Frontend** | React 18 + Vite | Interactive UI, real-time updates, document picker |
| **Backend** | FastAPI + Uvicorn | REST API, request routing, orchestration |
| **OCR** | EasyOCR | Text extraction + bounding boxes from images/PDFs |
| **NER** | LayoutLMv3 (ONNX) | Layout-aware token classification for structured fields |
| **Rules** | Regex + heuristics | Vendor, total, date, receipt ID parsing fallback |
| **LLM (Extraction)** | Groq Llama 3.3 70B | Fill missing fields via JSON prompt |
| **LLM (QA)** | Groq Llama 3.3 70B | Answer questions grounded in extracted data |
| **LLM (Fallback)** | Google Gemini 2.0 Flash | Secondary LLM if Groq unavailable |
| **Storage** | MongoDB Atlas | Document persistence, extracted fields, raw file bytes |
| **Hosting (Backend)** | HF Spaces (Docker) | Kubernetes-less ML serving, auto-scaling |
| **Hosting (Frontend)** | Vercel | Edge-cached React SPA, auto-deployments |

---

## Technology Stack

### Core Dependencies

**Backend** (`backend/requirements.txt`):
- `fastapi` — web framework
- `uvicorn` — ASGI server
- `pydantic-settings` — environment configuration
- `motor` — async MongoDB driver
- `easyocr` — optical character recognition
- `transformers` — HuggingFace model loading
- `optimum` — ONNX runtime & model optimization
- `onnxruntime` — lightweight inference
- `groq` — Groq API client
- `google-genai` — Google Gemini API client
- `slowapi` — rate limiting
- `python-multipart` — file upload handling
- `Pillow` — image processing
- `numpy` — numerical computing

**Frontend** (`frontend/package.json`):
- `react` 18 — UI library
- `vite` — bundler & dev server
- `axios` — HTTP client
- `tailwindcss` — styling
- Custom components: upload form, chat, document picker

**Inference Models**:
- `ShaibinkB/cord-layoutlmv3-onnx` — ONNX export of LayoutLMv3 fine-tuned on CORD
- `microsoft/layoutlmv3-base` — base model for fine-tuning
- `naver-clova-ix/cord-v1` — training dataset

---

## Data Flow & Processes

### Process 1: Document Upload & Extraction

**Trigger**: User selects image/PDF in frontend

**Flow**:
```
1. Frontend validates file type (image/pdf)
2. Shows local preview (blob)
3. POST /extract with multipart file + optional request_id
   │
4. Backend:
   a) Validate MIME type
   b) Save raw file bytes → temp storage / MongoDB
   c) Load file into PIL/PDF parser
   d) Pass to EasyOCR for text + bbox extraction
   e) Preprocess OCR output (normalize, clean noise)
   │
5. NER Inference:
   a) Load LayoutLMv3 ONNX from HF_MODEL_ID
   b) Prepare inputs: pixel_values + words + boxes
   c) Run inference via ORTModelForCustomTasks
   d) Get logits → softmax → token-level predictions
   e) Filter by confidence threshold (default 0.75)
   f) Aggregate adjacent tokens into spans
   │
6. Post-Processing:
   a) Rule-based extraction (vendor, total, date, receipt_id)
   b) Span deduplication & sorting by confidence
   c) Normalize values (remove currency symbols, parse dates)
   │
7. LLM Fallback (optional, if NER confidence low):
   a) Check if GROQ_API_KEY is set
   b) Call Groq with JSON schema prompt
   c) Fill only missing fields
   │
8. Storage:
   a) Insert document record into MongoDB
   b) Store: extracted (JSON), ocr_text, file_data, metadata
   │
9. Response to frontend:
   a) Return JSON: {
        "_id": "mongo doc id",
        "extracted": {"total_amount": "...", ...},
        "ocr_text": "...",
        "pipeline_trace": [
          "ocr_completed", 
          "ner_inference", 
          "rule_extraction", 
          "groq_fallback",
          "storage"
        ],
        "request_id": "..."
      }
   b) Frontend stores doc in list, shows extracted fields
```

**Key parameters**:
- `CONFIDENCE_THRESHOLD` (default 0.75) — minimum NER confidence to accept a span
- `HF_MODEL_ID` (default `ShaibinkB/cord-layoutlmv3-onnx`) — ONNX model to load
- `GROQ_API_KEY` (optional) — enables LLM fallback

**Error handling**:
- Missing HF_MODEL_ID → skip NER, continue with rules only
- EasyOCR fails → return error with advice
- MongoDB down → return error, continue with in-memory storage fallback (warning)
- Groq API unavailable → skip LLM fallback, use NER+rules only

---

### Process 2: Question Answering

**Trigger**: User types question in chat, optionally selects a document

**Flow**:
```
1. Frontend:
   a) Capture question text
   b) Optionally select document from dropdown
   c) POST /query {
        "question": "What is the total amount?",
        "document_id": "mongo_id_or_null"  # null → use latest
      }
   │
2. Backend:
   a) Validate question input (sanitize, length check)
   b) If document_id provided, fetch from MongoDB
   c) If null, query for latest document by timestamp
   d) Handle no documents case → return friendly message
   │
3. Grounding:
   a) Serialize extracted JSON to pretty string
   b) Construct system prompt:
      "You are a helpful assistant. Answer questions using ONLY 
       the following extracted receipt data:\n{extracted_json}"
   c) Set temperature = 0 for reproducibility
   │
4. LLM Call:
   a) Check if GROQ_API_KEY is set
   b) Call Groq llama-3.3-70b-versatile with:
      - system prompt (grounded context)
      - user message (question)
      - temperature 0
   c) If Groq fails or key missing, try Gemini
   d) If both fail, return friendly error
   │
5. Response:
   a) Extract answer text from LLM response
   b) Return JSON:
      {
        "answer": "The total amount is $48.97.",
        "document_id": "mongo_id",
        "grounded_on": "extracted.total_amount"
      }
   │
6. Frontend displays answer in chat bubble
```

**Guarantees**:
- No hallucination outside document: system prompt explicitly forbids it
- Temperature 0: deterministic responses (same question → same answer)
- Field tracing: backend could log which extracted field was used (for future transparency UI)

**Graceful degradation**:
- Both LLM APIs unavailable → return "QA is unavailable, set API keys"
- No document selected → return "No documents found"
- Empty extracted data → LLM sees empty JSON, returns "No information available"

---

### Process 3: Document Management

**List Documents** (GET /documents?limit=100):
```
Returns metadata (no large blobs):
[
  {
    "_id": "mongo_id_1",
    "filename": "receipt_20260329.jpg",
    "uploaded_at": "2026-03-29T13:05:55Z",
    "extracted": {
      "total_amount": "48.97",
      "vendor_name": "Walmart",
      "date": "2026-03-28",
      "receipt_id": "00012345"
    }
  },
  ...
]
```

**Get Document File** (GET /documents/{id}/file):
```
Returns raw file bytes + content-type header:
- Used by frontend for inline image/PDF preview
- MIME from stored content_type field
- Suitable for display in <img> or <iframe>
```

**Health Check** (GET /health):
```
Returns:
{
  "status": "ok",
  "database": "connected",  # or "unavailable"
  "model_loaded": true,  # or false
  "uptime_seconds": 3600
}
Frontend uses this to show connection status to user.
```

---

## API Documentation

### Base URL

**Production**: `https://shaibinkb16082002-visionex-backend.hf.space`

**Local**: `http://localhost:8000`

### Authentication

No authentication required (public demo). Production should add API key validation.

### Rate Limiting

`10 requests per minute` (per IP) via slowapi. Configurable in `app/main.py`.

### Endpoints

#### 1. Extract Document

```http
POST /extract
Content-Type: multipart/form-data

file: <binary image or PDF>
request_id: <optional string for tracking>
```

**Response** (200 OK):
```json
{
  "_id": "507f1f77bcf86cd799439011",
  "extracted": {
    "total_amount": "48.97",
    "date": "2026-03-28",
    "vendor_name": "Walmart",
    "receipt_id": "00012345"
  },
  "ocr_text": "WALMART STORE 1234\n...",
  "pipeline_trace": [
    "ocr_completed",
    "ner_inference",
    "rule_extraction",
    "storage_complete"
  ],
  "confidence_scores": {
    "amount": 0.95,
    "vendor": 0.88,
    "date": 0.92
  },
  "uploaded_at": "2026-03-29T13:05:55Z",
  "filename": "receipt.jpg"
}
```

**Errors**:
- `400 Bad Request`: Missing file, invalid format
- `413 Payload Too Large`: File > 50 MB
- `503 Service Unavailable`: Database down, models not loaded

---

#### 2. Get Extraction Status

```http
GET /extract/status/{request_id}
```

**Response** (200 OK):
```json
{
  "request_id": "abc123",
  "status": "completed",
  "current_step": "storage_complete",
  "steps_completed": ["ocr", "ner", "rules"],
  "progress_percent": 100,
  "document_id": "507f1f77bcf86cd799439011"
}
```

**Status values**: `queued`, `processing`, `completed`, `failed`

---

#### 3. List Documents

```http
GET /documents?limit=100
```

**Response** (200 OK):
```json
{
  "count": 2,
  "documents": [
    {
      "_id": "507f1f77bcf86cd799439011",
      "filename": "receipt_1.jpg",
      "uploaded_at": "2026-03-29T13:05:55Z",
      "extracted": {
        "total_amount": "48.97",
        "date": "2026-03-28",
        "vendor_name": "Walmart",
        "receipt_id": "00012345"
      }
    },
    ...
  ]
}
```

---

#### 4. Get Document File

```http
GET /documents/{document_id}/file
```

**Response** (200 OK):
- Content-Type: `image/jpeg` or `application/pdf`
- Body: raw file bytes

**Usage**: `<img src="/documents/{id}/file" />` in HTML

---

#### 5. Ask Question (QA)

```http
POST /query
Content-Type: application/json

{
  "question": "What is the total amount and vendor name?",
  "document_id": "507f1f77bcf86cd799439011"
}
```

If `document_id` is omitted, uses the **latest document**.

**Response** (200 OK):
```json
{
  "answer": "The total amount is $48.97 and the vendor is Walmart.",
  "document_id": "507f1f77bcf86cd799439011",
  "model_used": "groq",
  "latency_ms": 1200
}
```

**Errors**:
- `400 Bad Request`: Missing question
- `404 Not Found`: Document not found
- `503 Service Unavailable`: LLM API unavailable, no extraction for document
- `429 Too Many Requests`: Rate limit exceeded

---

#### 6. Health Check

```http
GET /health
```

**Response** (200 OK):
```json
{
  "status": "ok",
  "uptime_seconds": 3600,
  "database": "connected",
  "model_loaded": true,
  "backend_version": "1.0.0"
}
```

**Response** (503 Service Unavailable, if errors):
```json
{
  "status": "degraded",
  "database": "unavailable",
  "model_loaded": false,
  "message": "MongoDB connection failed; extraction disabled"
}
```

---

## Setup & Local Development

### Prerequisites

- **Python** 3.11+ with `venv` or `conda`
- **Node.js** 20+ with `npm`
- **MongoDB** (local or Atlas shared cluster)
- **API Keys** (optional for full functionality):
  - Groq API key (free tier: 30 reqs/min)
  - Google Gemini API key (free tier available)
  - Hugging Face token (for private models, optional)

### Step 1: Clone & Enter Repo

```bash
git clone https://github.com/shaibinkb16/Visionex.git
cd Visionex
```

### Step 2: Backend Setup & Configuration

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  (Windows)

# Install dependencies
pip install -r requirements.txt
```

**Create `backend/.env` file for local development:**

```bash
cp .env.example .env
# Now configure the .env file (see detailed config below)
```

**Complete `backend/.env` configuration for local development:**

```env
# Environment type
ENV=development

# API Keys (get free keys from respective platforms)
# Get GROQ_API_KEY from: https://console.groq.com
GROQ_API_KEY=gsk_YOUR_GROQ_API_KEY_HERE

# Get GEMINI_API_KEY from: https://ai.google.dev
GEMINI_API_KEY=YOUR_GOOGLE_GEMINI_KEY_HERE

# Optional: Hugging Face token for private models
HF_TOKEN=YOUR_HF_TOKEN_HERE

# Database Configuration
# Option 1: Local MongoDB (most common for local development)
MONGODB_URI=mongodb://localhost:27017/doc_extraction

# Option 2: MongoDB Atlas Cloud (if local MongoDB not available)
# MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/doc_extraction?retryWrites=true&w=majority

# Model Configuration
HF_MODEL_ID=ShaibinkB/cord-layoutlmv3-onnx
CONFIDENCE_THRESHOLD=0.75

# CORS - MUST match your frontend URL
# For local frontend on port 5173:
CORS_ORIGIN=http://localhost:5173

# Optional: Different frontend port
# CORS_ORIGIN=http://localhost:3000
```

**Run the backend development server:**

```bash
# Start with auto-reload (watches for file changes)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**If port 8000 is already in use:**
```bash
# Use a different port (e.g., 8001)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
# Then update CORS_ORIGIN to: http://localhost:5173:8001
```

**Backend is now running:**
- 🔗 **API Base URL**: http://localhost:8000
- 📚 **Interactive Docs**: http://localhost:8000/docs (Swagger UI - try API calls here)
- 📄 **OpenAPI Schema**: http://localhost:8000/openapi.json
- ❤️ **Health Check**: http://localhost:8000/health

---

### Step 3: Frontend Setup & Configuration

```bash
cd frontend

# Install dependencies
npm install
```

**Create `frontend/.env` file to point to your backend:**

**Option A: Use local backend (RECOMMENDED for development)**
```bash
cat > .env << 'EOF'
VITE_API_URL=http://localhost:8000
EOF
```

**Option B: Use local backend on different port**
```bash
# If backend runs on port 8001:
cat > .env << 'EOF'
VITE_API_URL=http://localhost:8001
EOF
```

**Option C: Use production backend** (useful for testing production API without running backend locally)
```bash
cat > .env << 'EOF'
VITE_API_URL=https://shaibinkb16082002-visionex-backend.hf.space
EOF
```

**Start the frontend development server:**

```bash
npm run dev
# Frontend will start at http://localhost:5173 (shown in terminal)
```

**If port 5173 is busy, specify a custom port:**
```bash
# Using port 3000 instead
VITE_PORT=3000 npm run dev
# Then update CORS_ORIGIN in backend .env to: http://localhost:3000
```

**Frontend is now running:**
- 🎨 **Application**: http://localhost:5173
- 📡 **Connected Backend**: (whatever URL you set in `VITE_API_URL`)

---

### Step 4: Verify Everything is Connected

**Check backend health:**
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "database": "connected",
  "model_loaded": true
}
```

**Open services in browser:**

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend** | http://localhost:5173 | Upload receipts & ask questions |
| **API Docs** | http://localhost:8000/docs | Interactive API testing (Swagger) |
| **API Schema** | http://localhost:8000/openapi.json | Full OpenAPI specification |
| **Health** | http://localhost:8000/health | Backend status & diagnostics |

---

### Step 5: Run End-to-End Test

1. **Open frontend**: http://localhost:5173
2. **Upload a receipt image**:
   - Click upload area
   - Select receipt image
   - See extracted fields (vendor, total, date, receipt ID)
3. **View pipeline trace**:
   - See processing steps: OCR → NER → Rules → Storage
   - Check which fields came from NER vs rule-based extraction
4. **Ask questions**:
   - Type: "What is the total amount?"
   - Get answer grounded in extracted data
   - Switch to different document, ask again
5. **Try API directly** (optional):
   - Go to http://localhost:8000/docs
   - Try POST /extract with test receipt image
   - Try POST /query with test question
   - See response formats and schemas

---

### Step 6: Troubleshooting Local Setup

**❌ Frontend shows CORS error | Access-Control-Allow-Origin**
```
✅ Solution:
   1. Check backend .env has correct CORS_ORIGIN:
      CORS_ORIGIN=http://localhost:5173
   2. Restart backend (stop and run again)
   3. Clear browser cache (Ctrl+Shift+Delete)
   4. Hard reload frontend (Ctrl+Shift+R)
```

**❌ Frontend can't connect to backend | Network error**
```
✅ Solution:
   1. Verify backend is running:
      curl http://localhost:8000/health
   2. Check frontend .env has correct URL:
      VITE_API_URL=http://localhost:8000
   3. If backend on different port, update VITE_API_URL
   4. Restart frontend: npm run dev
```

**❌ Backend fails to start | ModuleNotFoundError**
```
✅ Solution:
   1. Verify virtual environment is activated:
      source venv/bin/activate  (Linux/macOS)
      or venv\Scripts\activate  (Windows)
   2. Reinstall dependencies:
      pip install -r requirements.txt
   3. Check Python version (need 3.8+):
      python --version
```

**❌ Model fails to load | HF_MODEL_ID not found**
```
✅ Solution:
   1. Verify .env has valid model ID:
      HF_MODEL_ID=ShaibinkB/cord-layoutlmv3-onnx
   2. Check internet connection (first run downloads model ~2GB)
   3. Check HuggingFace token if model is private:
      HF_TOKEN=YOUR_TOKEN
   4. Check hard drive space (need ~5GB for ML models)
```

**❌ MongoDB connection timeout | No route to host**
```
✅ Solution A - Use local MongoDB:
   # Install Docker: https://www.docker.com/products/docker-desktop
   docker run -d -p 27017:27017 -e MONGO_INITDB_ROOT_USERNAME=root -e MONGO_INITDB_ROOT_PASSWORD=root mongo
   
   # Update .env:
   MONGODB_URI=mongodb://localhost:27017/doc_extraction

✅ Solution B - Use MongoDB Atlas:
   1. Sign up: https://www.mongodb.com/cloud/atlas
   2. Create cluster (free tier)
   3. Copy connection string
   4. Update .env:
      MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/doc_extraction?retryWrites=true&w=majority

✅ Check health:
   curl http://localhost:8000/health  # Shows "database": "connected"
```

**❌ Port already in use | Address already in use**
```
✅ Solution - Use different port:
   
   # For backend (default 8000):
   uvicorn app.main:app --reload --port 8001
   
   # Update CORS_ORIGIN in backend .env:
   CORS_ORIGIN=http://localhost:5173
   
   # Update VITE_API_URL in frontend .env:
   VITE_API_URL=http://localhost:8001
   
   # For frontend (default 5173):
   VITE_PORT=3000 npm run dev
   
   # Update CORS_ORIGIN in backend .env:
   CORS_ORIGIN=http://localhost:3000
```

**❌ API Key errors | GROQ_API_KEY invalid | GEMINI_API_KEY missing**
```
✅ Solution:
   1. Get free API keys:
      - Groq: https://console.groq.com (free tier, instant)
      - Gemini: https://ai.google.dev (free tier)
   
   2. Add to .env:
      GROQ_API_KEY=gsk_YOUR_KEY
      GEMINI_API_KEY=YOUR_KEY
   
   3. Restart backend
   
   4. Note: App works without keys (graceful degradation)
      - Missing keys = features degrade, no crashes
```

---

### Step 7: Switch Between Local & Production Backends

**Currently using local backend? Switch to production:**

Edit `frontend/.env`:
```env
# Change from local:
# VITE_API_URL=http://localhost:8000

# To production:
VITE_API_URL=https://shaibinkb16082002-visionex-backend.hf.space
```

Then restart frontend:
```bash
npm run dev
```

**Or: Run local frontend with production backend - quick testing without local backend:**
```bash
# In frontend directory
cat > .env << 'EOF'
VITE_API_URL=https://shaibinkb16082002-visionex-backend.hf.space
EOF

npm run dev
# Frontend at http://localhost:5173 →connects to→ Production backend
```

**Back to local backend?**
```bash
cat > .env << 'EOF'
VITE_API_URL=http://localhost:8000
EOF

npm run dev
```

---

## Production Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed deployment instructions.

### Quick Summary

| Component | Platform | Command | Status |
|-----------|----------|---------|--------|
| **Frontend** | Vercel | `vercel --prod --yes` | Deployed |
| **Backend** | HF Spaces (Docker) | Push to Git → auto-build | Deployed |
| **Database** | MongoDB Atlas | Manual setup | Running |
| **API Keys** | HF Spaces Secrets | Set in Settings | Configured |

### Live URLs

- Frontend: https://frontend-omega-ten-28.vercel.app
- Backend: https://shaibinkb16082002-visionex-backend.hf.space
- Backend Docs: https://shaibinkb16082002-visionex-backend.hf.space/docs

---

## Model Training & Export

### Overview

The system uses **LayoutLMv3** fine-tuned on the **CORD** (receipt) dataset.

### Training

**Option A**: Jupyter Notebook (recommended for quick iteration)

```bash
cd notebooks
# Open CORD.ipynb in Google Colab or Jupyter
# Follow cells to:
# 1. Download CORD v1 subset
# 2. Prepare dataset into BIO token labels
# 3. Train microsoft/layoutlmv3-base with HF Trainer
# 4. Evaluate (P/R/F1 with seqeval)
# 5. Export to ONNX
```

**Option B**: Python script

```bash
cd notebooks
pip install -r requirements-train.txt
python train_cord_layoutlmv3.py \
  --dataset_split 0.8 \
  --num_epochs 3 \
  --batch_size 4 \
  --output_dir ./cord-layoutlmv3-final

# Export to ONNX
python train_cord_layoutlmv3.py \
  --export_onnx \
  --model_dir ./cord-layoutlmv3-final \
  --onnx_dir ./cord-layoutlmv3-onnx
```

### Export to Production

```bash
# Method 1: Push to Hugging Face Hub
huggingface-cli login
# Copy ONNX files to HF repo
cd cord-layoutlmv3-onnx
git lfs install
git add .
git commit -m "Export ONNX model"
git push

# Method 2: Use local path
# Update backend/.env: HF_MODEL_ID=./path/to/local/onnx
```

### Update Backend

1. Update `HF_MODEL_ID` in `backend/.env` or HF Spaces secrets
2. Restart backend (push to HF Spaces or run locally)
3. Backend auto-loads new model on startup

---

## Development Guide

### Project Structure

```
Visionex/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI app, lifespan, routers
│   │   ├── core/
│   │   │   ├── config.py       # Pydantic settings
│   │   │   ├── dependencies.py # MongoDB connection
│   │   ├── api/
│   │   │   ├── extract.py     # POST /extract
│   │   │   ├── query.py       # POST /query
│   │   │   ├── documents.py   # GET /documents, GET /documents/{id}/file
│   │   │   ├── health.py      # GET /health
│   │   ├── services/
│   │   │   ├── extraction.py  # OCR + NER + rules + LLM
│   │   │   ├── qa.py          # Question answering
│   │   │   ├── ocr.py         # EasyOCR wrapper
│   │   │   ├── storage.py     # MongoDB queries
│   │   │   ├── pipeline_status.py
│   │   ├── models/
│   │   │   ├── schemas.py     # Pydantic models
│   │   ├── utils/
│   │   │   ├── sanitize.py    # Input validation
│   │   ├── Dockerfile         # Docker image
│   │   ├── requirements.txt    # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Root component
│   │   ├── components/
│   │   │   ├── UploadForm.jsx
│   │   │   ├── ResultView.jsx
│   │   │   ├── ChatWindow.jsx
│   │   │   ├── PipelineFlow.jsx
│   │   ├── services/
│   │   │   ├── api.js         # Axios client + endpoints
│   │   ├── index.css           # Global styles
│   │   ├── main.jsx            # Entry point
│   │   ├── vite.config.js      # Vite config
│   │   ├── package.json        # Node dependencies
├── notebooks/
│   ├── CORD.ipynb             # Training notebook
│   ├── train_cord_layoutlmv3.py
│   ├── requirements-train.txt
├── docs/
│   ├── DEPLOYMENT.md          # Deployment guide
│   ├── ASSESSMENT.md          # Architecture + design
├── README.md                  # This file
├── .gitignore
```

### Adding a New API Endpoint

1. **Define schema** in `backend/app/models/schemas.py`
2. **Create router** in `backend/app/api/newfeature.py`
3. **Import & include router** in `backend/app/main.py`:
   ```python
   from .api import newfeature
   app.include_router(newfeature.router)
   ```
4. **Test with Swagger UI**: http://localhost:8000/docs
5. **Update `frontend/src/services/api.js`** if adding new client call

### Extending the Extraction Pipeline

**Location**: `backend/app/services/extraction.py`

**Add custom post-processing**:
```python
# In extract_fields() function, add after NER:
if 'YOUR_FIELD' not in extracted:
    extracted['YOUR_FIELD'] = custom_extraction_logic(ocr_text)
```

**Add new LLM fallback**:
```python
# In extract_from_json():
try:
    result = await _groq_extract(...)
except:
    result = await _your_new_llm_extract(...)
```

### Running Tests

```bash
cd backend
pytest tests/ -v
```

*Note: Currently no tests. Add test cases for regression prevention.*

### Debugging

**Enable verbose logging**:
```bash
# In backend/.env
ENV=development
# Logs show detailed traces of each pipeline step
```

**Check model loading**:
```bash
curl http://localhost:8000/health
# Check "model_loaded" and "database" fields
```

**Test extraction with cURL**:
```bash
curl -X POST http://localhost:8000/extract \
  -F "file=@receipt.jpg"
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| **API returns 503** | Model not loaded | Check logs: `HF_MODEL_ID` valid? Models cache? |
| **CORS error in browser** | Frontend CORS_ORIGIN mismatch | Backend backend: `CORS_ORIGIN=http://localhost:5173` |
| **"Model not found" error** | `HF_MODEL_ID` invalid or private | Ensure repo exists, set `HF_TOKEN` if private |
| **MongoDB connection timeout** | Atlas IP whitelist | Add HF Space outbound IPs to MongoDB Atlas |
| **First extraction takes 2+ mins** | Models downloading | Normal; subsequent requests cached. Wait or upgrade RAM. |
| **Groq API 401 error** | Invalid `GROQ_API_KEY` | Check key in secrets, rotate if expired |
| **Frontend shows blank page** | `VITE_API_URL` wrong | Check frontend `.env` or Vercel env vars |
| **"No documents found" on QA** | Empty MongoDB | Upload a receipt first via extraction endpoint |

### Debug Commands

```bash
# Check backend health
curl https://shaibinkb16082002-visionex-backend.hf.space/health

# View API docs
curl https://shaibinkb16082002-visionex-backend.hf.space/openapi.json

# Test extraction locally
curl -X POST http://localhost:8000/extract \
  -F "file=@test_receipt.jpg"

# Check HF Spaces build logs
# Visit: https://huggingface.co/spaces/shaibinkb16082002/visionex-backend/logs

# Vercel deployment logs
# Visit: https://vercel.com/shaibin-k-bs-projects/frontend/deployments
```

### Performance Tuning

| Bottleneck | Tuning |
|-----------|--------|
| **OCR slow** | EasyOCR uses GPU if available; add CUDA support to Dockerfile |
| **NER slow** | Reduce image resolution before OCR; batch inference if possible |
| **LLM slow** | Use smaller models (e.g., Gemini, or local Ollama) |
| **MongoDB slow** | Index `uploaded_at` & `filename`; use connection pooling |
| **Frontend lag** | Enable Vite build optimization; deploy to Vercel edge |

---

## Limitations & Future Work

### Known Limitations

1. **PDF handling**: Multi-page PDFs treated as image sequences; no doc structure parsing
2. **Storage size**: MongoDB 16 MB per-document limit (use S3/GridFS for large PDFs)
3. **QA hallucination**: LLM temperature=0 helps, but schema constraints better
4. **Language**: Only English; multilingual support requires model retraining
5. **Auth**: No user isolation; all documents in shared namespace
6. **Cost**: Groq/Gemini API calls accumulate; implement usage tracking

### Future Enhancements

- [ ] **User authentication** + role-based access control (RBAC)
- [ ] **Batch processing** — upload multiple receipts, get CSV export
- [ ] **Custom field types** — user-configurable extraction targets
- [ ] **Model fine-tuning UI** — upload labeled data to improve model on-the-fly
- [ ] **Export formats** — JSON, CSV, PDF reports with extracted data
- [ ] **Analytics dashboard** — extraction accuracy, QA performance trends
- [ ] **Caching** — Redis for frequently asked questions
- [ ] **Smaller models** — TinyBERT, DistilBERT for faster inference
- [ ] **Offline mode** — browser-side WASM inference for privacy
- [ ] **Mobile app** — React Native frontend with camera integration

---

## License & Attribution

- **CORD dataset**: [naver-clova-ix/cord-v1](https://huggingface.co/datasets/naver-clova-ix/cord-v1) — check dataset license
- **LayoutLMv3**: Microsoft Research — [layoutlmv3-base](https://huggingface.co/microsoft/layoutlmv3-base)
- **EasyOCR**: JaidedAI — [easyocr](https://github.com/JaidedAI/EasyOCR)
- **Groq API**: Groq Inc. — [groq.com](https://groq.com)
- **Google Gemini**: Google DeepMind — [google.com/ai](https://google.com/ai)

---

## Support & Contact

- **GitHub Issues**: [Create an issue](https://github.com/shaibinkb16/Visionex/issues)
- **HF Spaces Community**: [Discussion board](https://huggingface.co/spaces/shaibinkb16082002/visionex-backend/community)
- **Live Demo**: https://frontend-omega-ten-28.vercel.app

---

**Last Updated**: March 29, 2026 | **Status**: Production Ready ✅
