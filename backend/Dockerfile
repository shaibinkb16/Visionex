FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for CV/NLP libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port (HF Spaces uses 7860, local dev uses 8000)
EXPOSE 7860

# Run FastAPI with uvicorn
# HF Spaces sets PORT=7860, fallback to 8000 for local
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}
