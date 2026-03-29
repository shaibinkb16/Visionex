import time
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Header
from ..services.ocr import run_ocr
from ..services.extraction import extract_fields
from ..services.storage import save_document
from ..services.pipeline_status import (
    init_request,
    add_step,
    mark_done,
    mark_error,
    get_status,
)
from ..models.schemas import ExtractionResponse

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}


@router.post("/extract", response_model=ExtractionResponse)
async def extract(file: UploadFile = File(...), x_request_id: str | None = Header(default=None)):
    logger.info("POST /extract — file: %s (%s)", file.filename, file.content_type)

    request_id = x_request_id or f"req-{int(time.time()*1000)}"
    init_request(request_id)
    add_step(request_id, "receive", "done", f"Received file {file.filename}")

    if file.content_type not in ALLOWED_TYPES:
        mark_error(request_id, "Unsupported file type")
        raise HTTPException(400, "Unsupported file type.")

    image_bytes = await file.read()
    if not image_bytes:
        mark_error(request_id, "Empty file")
        raise HTTPException(400, "Empty file.")

    logger.info("File received: %d KB", len(image_bytes) // 1024)
    add_step(request_id, "read", "done", f"Read {len(image_bytes)//1024} KB upload")
    start = time.monotonic()

    try:
        ocr_t0 = time.monotonic()
        image, words, boxes, plain_text = run_ocr(image_bytes)
        add_step(
            request_id,
            "ocr",
            "done",
            f"OCR detected {len(words)} tokens",
            int((time.monotonic() - ocr_t0) * 1000),
        )
    except Exception as e:
        logger.error("OCR failed: %s", e)
        mark_error(request_id, f"OCR failed: {e}")
        raise HTTPException(400, f"OCR failed: {e}")

    if not plain_text.strip():
        mark_error(request_id, "No text detected")
        raise HTTPException(400, "No text detected in image.")

    def progress_cb(step: dict):
        add_step(
            request_id,
            step.get("stage", "unknown"),
            step.get("status", "done"),
            step.get("detail", ""),
            step.get("elapsed_ms"),
        )

    fields, confidence, method, pipeline_trace = await extract_fields(
        image,
        words,
        boxes,
        plain_text,
        progress_cb=progress_cb,
    )

    doc_id = await save_document(
        filename=file.filename or "upload",
        ocr_text=plain_text,
        extracted=fields,
        confidence=confidence,
        method=method,
        pipeline_trace=pipeline_trace,
        file_bytes=image_bytes,
        content_type=file.content_type,
    )

    elapsed_ms = int((time.monotonic() - start) * 1000)
    add_step(request_id, "persist", "done", f"Saved document {doc_id}")
    add_step(request_id, "complete", "done", f"Extraction finished with method={method}", elapsed_ms)
    mark_done(request_id)
    logger.info("POST /extract complete — doc_id: %s, method: %s, time: %dms",
                doc_id, method, elapsed_ms)

    return ExtractionResponse(
        document_id=doc_id,
        filename=file.filename or "upload",
        content_type=file.content_type,
        extracted=fields,
        confidence=confidence,
        extraction_method=method,
        processing_time_ms=elapsed_ms,
        pipeline_trace=pipeline_trace,
    )


@router.get("/extract/status/{request_id}")
async def extract_status(request_id: str):
    status = get_status(request_id)
    if not status:
        return {
            "request_id": request_id,
            "status": "pending",
            "started_at": None,
            "updated_at": None,
            "steps": [],
        }
    return status
