# Visionex Frontend

React + Vite client for receipt extraction, live pipeline tracking, and grounded QA.

## What the UI does

- Uploads receipt/image/PDF files to backend `/extract`
- Shows live extraction stages via polling `/extract/status/{request_id}`
- Displays extracted fields + confidence + pipeline trace
- Lists previous upload history and lets users pick one for QA context
- Sends grounded questions to `/query` for selected (or latest) document

## Requirements

- Node.js 20+
- Backend API running (default: `http://localhost:8000`)

## Environment

Create `.env` in this folder if needed:

```env
VITE_API_URL=http://localhost:8000
```

If unset, the client defaults to `http://localhost:8000`.

## Run locally

```bash
npm install
npm run dev
```

Open the Vite URL shown in terminal (typically `http://localhost:5173`).

## Build

```bash
npm run build
npm run preview
```

## Key source files

- `src/App.jsx`: top-level layout and result/QA orchestration
- `src/components/UploadForm.jsx`: upload, live status polling, and history list
- `src/components/ResultView.jsx`: extracted JSON and pipeline rendering
- `src/components/ChatWindow.jsx`: grounded QA chat with document selection
- `src/services/api.js`: backend API client wrappers
