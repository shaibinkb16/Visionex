# ML Engineer assessment — design note

This document summarizes **architecture**, **training**, **design trade-offs**, and **limitations** for the document extraction and grounded QA system.

---

## 1. Problem

Organizations need **structured fields** from receipts (total, date, vendor, receipt id) and a **simple way to query** that structure in natural language without hallucinating off-document facts.

---

## 2. System architecture

```text
┌─────────────┐     POST /extract      ┌──────────────────────────────────────┐
│   Browser   │ ─────────────────────► │ FastAPI                               │
│  (React)    │ ◄───────────────────── │  OCR (EasyOCR) → NER / rules / LLM    │
└─────────────┘     JSON + doc id      │  → MongoDB (extracted + raw file)     │
       │                               └──────────────────────────────────────┘
       │    GET /documents/{id}/file
       │    POST /query { question, document_id? }
       ▼
 Grounded QA (Groq): system prompt contains only `extracted` JSON for the chosen document.
```

- **Inference model**: LayoutLMv3-class token classifier in **ONNX** via Optimum, loaded from `HF_MODEL_ID`. For layout models, runtime uses `ORTModelForCustomTasks` with `model.onnx` to support `bbox` + `pixel_values` inputs.
- **Fallbacks**: Rule-based parsing and LLM (Groq / Gemini) only **fill missing** or low-confidence fields, to keep the pipeline practical on noisy scans.
- **Persistence**: MongoDB stores structured extraction, OCR text, pipeline trace, and **optional raw upload** for UI preview (`file_data`, `content_type`).

---

## 3. Dataset and fine-tuning (mandatory)

### Dataset

- **CORD v1** (`naver-clova-ix/cord-v1` on Hugging Face): receipt images, words, and token-level labels aligned with key-value style fields.
- **Subset**: Notebook uses a **small split** (e.g. `train[:200]`) plus train/validation split for fast iteration on laptop/Colab.

### Approach

- **Model**: `microsoft/layoutlmv3-base` adapted to **token classification** (sequence labeling / NER-style), which matches the assessment’s allowed “lightweight sequence labeling.”
- **Why LayoutLMv3**: Joint encoding of text and layout (bounding boxes) fits receipts better than text-only models.
- **Training**: Hugging Face `Trainer`, a few epochs, small batch size — sufficient to demonstrate **correct fine-tuning** without large-scale compute.
- **Evaluation**: Entity-level **precision / recall / F1** (`seqeval`) on the held-out split (see `notebooks/CORD.ipynb` outputs).

### Notebook / script → production

1. Train and evaluate in **`notebooks/CORD.ipynb`** **or** the equivalent script **`notebooks/train_cord_layoutlmv3.py`** (same CORD subset, LayoutLMv3 head, `seqeval` metrics).
2. Export **ONNX** with **`optimum-cli export onnx …`** (token-classification task), as in the notebook.
3. Publish processor + ONNX to Hugging Face or point `HF_MODEL_ID` to a local export directory.

The backend tries **`ORTModelForCustomTasks`** + `model.onnx` first for LayoutLM-style inference, and only uses **`ORTModelForTokenClassification`** as a fallback for non-layout model types.

**Justification**: Fine-tuning is **explicitly in the notebook**; the API **consumes the resulting artifact**, separating research/training from deployment (common MLOps pattern).

---

## 4. Question answering

- **Method**: **Direct LLM** (Groq `llama-3.3-70b-versatile`) with a **strict system prompt**: answer only from serialized `extracted` fields — **no retrieval index** required by the brief.
- **Grounding**: If the JSON does not contain an answer, the model should reflect that; temperature is set to **0** for stability.
- **Multi-document**: API accepts optional **`document_id`** on `/query`; UI provides a **dropdown** of recent documents. Omitting `document_id` falls back to the **latest** upload.

---

## 5. API design choices

| Decision | Rationale |
|----------|-----------|
| `POST /extract` returns JSON only | Fits “structured output” requirement; file bytes stored server-side for **GET /documents/{id}/file** preview. |
| Raw file in MongoDB | Keeps demo self-contained; **16 MB BSON limit** is a known trade-off (see limitations). |
| `GET /documents` without blobs | Fast listing for the QA document picker. |
| Rate limiting (`slowapi`) | Basic abuse protection on a public demo. |

---

## 6. UI choices

- **Pipeline visualization**: Live steps during extraction improve transparency for assessors.
- **Document preview**: Images and PDFs use **stored bytes** after extraction; during upload, a **local blob preview** appears while the pipeline runs.

---

## 7. Limitations and future work

1. **BSON size**: Large PDFs may exceed MongoDB’s per-document limit; production would use **object storage** (S3, GridFS).
2. **PDF pipeline**: OCR currently follows the same path as images; **multi-page PDFs** are not first-class.
3. **QA**: No syntactic guarantee against rare hallucinations; stricter options include **template-only** answers or JSON-schema–constrained decoding.
4. **Evaluation in production**: Notebook metrics are on **CORD**; production receipts may drift — periodic **human eval** or gold sets would help.
5. **Multi-user auth**: Not in scope; all documents share one database namespace.

---

## 8. How this maps to the rubric

| Rubric item | Evidence in repo |
|-------------|------------------|
| Data processing | `notebooks/CORD.ipynb` + runtime OCR |
| Structured extraction | `backend/app/services/extraction.py`, schemas |
| Fine-tuning | `notebooks/CORD.ipynb` |
| Storage & querying | MongoDB + `/query` + optional `document_id` |
| Grounded QA | `backend/app/services/qa.py` |
| REST API | `backend/app/api/*.py` |
| UI | `frontend/` + document preview + picker |
| Documentation | This file + root `README.md` |

---

## 9. Suggested demo flow (for interview)

1. Start MongoDB, backend, frontend (see root `README.md`).
2. Upload a sample receipt → show **fields**, **trace**, **preview**.
3. Ask: “What is the total amount?” → answer from extraction only.
4. Upload a second receipt, switch **Answer using** in the chat header, repeat QA.

This demonstrates **extraction**, **grounding**, and **multi-document** behavior in under a few minutes.
