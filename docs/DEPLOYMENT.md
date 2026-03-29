# Deployment

This document contains the live production URLs for Visionex and the API endpoints used by the frontend.

## Live URLs

- Frontend (Vercel): https://frontend-omega-ten-28.vercel.app
- Backend Base URL (HF Space runtime): https://shaibinkb16082002-visionex-backend.hf.space
- Backend API Docs (Swagger): https://shaibinkb16082002-visionex-backend.hf.space/docs
- Backend OpenAPI JSON: https://shaibinkb16082002-visionex-backend.hf.space/openapi.json
- Backend Health: https://shaibinkb16082002-visionex-backend.hf.space/health
- HF Space Page: https://huggingface.co/spaces/shaibinkb16082002/visionex-backend

## API Endpoints

Base URL:

```text
https://shaibinkb16082002-visionex-backend.hf.space
```

Endpoints:

- `POST /extract` - upload an image/pdf for extraction
- `GET /extract/status/{request_id}` - check extraction status
- `GET /documents` - list processed documents
- `GET /documents/{document_id}/file` - fetch stored document file
- `POST /query` - ask questions over extracted document data
- `GET /health` - service health check
- `GET /docs` - interactive Swagger UI

## Frontend Configuration

The frontend should point to this backend URL:

```env
VITE_API_URL=https://shaibinkb16082002-visionex-backend.hf.space
```

Current frontend files already updated:

- `frontend/src/services/api.js`
- `frontend/.env.example`

## Verification Commands

```bash
curl https://shaibinkb16082002-visionex-backend.hf.space/health
curl https://shaibinkb16082002-visionex-backend.hf.space/openapi.json
```

## Deployment Notes

- Backend is hosted on Hugging Face Spaces (Docker).
- Frontend is hosted on Vercel.
- If backend URL changes, update `VITE_API_URL` in Vercel Environment Variables and redeploy frontend.

Last Updated: 2026-03-29
