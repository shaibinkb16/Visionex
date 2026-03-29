# Visionex — Document extraction & grounded QA

End-to-end pipeline: **upload receipt → OCR → LayoutLMv3-style NER (+ rules / LLM fallback) → MongoDB → grounded question answering** via a FastAPI backend and React UI.

## Repository layout

| Path | Purpose |
|------|---------|
| `backend/` | FastAPI app (`/extract`, `/query`, `/documents`, `/health`) |
| `frontend/` | Vite + React client |
| `notebooks/CORD.ipynb` | **CORD subset**, LayoutLMv3 **fine-tuning**, metrics, ONNX export |
| `docs/ASSESSMENT.md` | Architecture, training rationale, trade-offs, limitations |

## Prerequisites

- **Python** 3.10+ (backend)
- **Node.js** 20+ (frontend)
- **MongoDB** (local or Atlas URI)
- API keys (see **Environment**): Groq, Google Gemini (extraction fallback), Hugging Face model access as needed

## Environment variables

### Backend (`backend/.env`)

Create `backend/.env` (never commit secrets):

```env
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
MONGODB_URI=mongodb://localhost:27017
# Database name in code: `doc_extraction`, collection `documents` (see backend/app/core/dependencies.py)

HF_MODEL_ID=your-username/cord-layoutlmv3-onnx
CONFIDENCE_THRESHOLD=0.75
CORS_ORIGIN=http://localhost:5173
ENV=development
```

- **`HF_MODEL_ID`**: Hugging Face repo (or local path) for the **ONNX** LayoutLMv3 checkpoint used at inference. This should be the artifact produced after notebook training/export (or your published model).
- **`CORS_ORIGIN`**: Must match the **browser origin** of the frontend. The backend code default is `http://localhost:3000`, while Vite dev usually runs on `http://localhost:5173`, so set this explicitly in `.env`.

### Frontend (`frontend/.env` optional)

```env
VITE_API_URL=http://localhost:8000
```

If unset, the client defaults to `http://localhost:8000`.

## Notebook → ONNX → `HF_MODEL_ID`

### Option A — Jupyter / Colab (`notebooks/CORD.ipynb`)

1. Open **`notebooks/CORD.ipynb`** in **Google Colab** or locally (GPU optional but faster).
2. Run cells to train on **`naver-clova-ix/cord-v1`** (subset), evaluate (P/R/F1), save **`./cord-layoutlmv3-final`**, then **`optimum-cli export onnx`** into **`./cord-layoutlmv3-onnx`**.
3. Push the ONNX folder + processor to Hugging Face (e.g. `ShaibinkB/cord-layoutlmv3-onnx`) or keep a local path.
4. Set **`HF_MODEL_ID`** in `backend/.env` to that repo id or directory.

### Option B — Python script (same logic, no notebook)

```bash
cd notebooks
pip install -r requirements-train.txt
python train_cord_layoutlmv3.py --output_dir ./cord-layoutlmv3-final
python train_cord_layoutlmv3.py --export_onnx --output_dir ./cord-layoutlmv3-final --onnx_dir ./cord-layoutlmv3-onnx
# Or export only:
python train_cord_layoutlmv3.py --export_only --model_dir ./cord-layoutlmv3-final --onnx_dir ./cord-layoutlmv3-onnx
```

The API loads **`ORTModelForCustomTasks`** + `model.onnx` for LayoutLM-style models (requires `bbox` + `pixel_values` inputs). For non-layout model types, it can fall back to **`ORTModelForTokenClassification`** when available. See `load_model()` in `backend/app/services/extraction.py`.

## Run MongoDB

Example with Docker:

```bash
docker run -d -p 27017:27017 --name mongo mongo:7
```

Use the same host in `MONGODB_URI`.

## Run the backend

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
source venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite (usually **http://localhost:5173**). Ensure **`CORS_ORIGIN`** matches.

## API overview

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/extract` | Multipart file upload → JSON extraction + stores **raw file** for preview |
| `GET` | `/extract/status/{request_id}` | Live pipeline status/steps for polling UI |
| `GET` | `/documents` | List recent documents (metadata; no large blobs) |
| `GET` | `/documents/{id}/file` | Inline file for UI preview (images / PDF) |
| `POST` | `/query` | Body: `{"question": "...", "document_id": "<optional>"}` — grounded on `extracted`; omit id for **latest** |
| `GET` | `/health` | Liveness + DB + model flag |

## Stored files & limits

- Original upload bytes are stored in MongoDB under `file_data` (**BSON max ~16 MB per document**). Suitable for receipts; very large PDFs may need another object store.

## License / attribution

- **CORD**: [naver-clova-ix/cord-v1](https://huggingface.co/datasets/naver-clova-ix/cord-v1) (check dataset license for your use).
- Third-party models (LayoutLMv3, Groq, Gemini) subject to their respective terms.
