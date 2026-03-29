import io
import logging
import time

import easyocr
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

_reader = None


def get_reader() -> easyocr.Reader:
    global _reader
    if _reader is None:
        logger.info("Initializing EasyOCR (first call — downloading models if needed)...")
        t0 = time.monotonic()
        _reader = easyocr.Reader(["en"], gpu=False)
        logger.info("EasyOCR ready in %.2fs ✓", time.monotonic() - t0)
    return _reader


def run_ocr(image_bytes: bytes) -> tuple[Image.Image, list[str], list[list[int]], str]:
    """
    Returns:
        image       : PIL Image (RGB)
        words       : list of word strings
        boxes       : list of [x0, y0, x1, y1] normalized to 0-1000 (LayoutLMv3 format)
        plain_text  : full OCR text joined for LLM fallback
    """
    logger.info("Running OCR on image (%d KB)...", len(image_bytes) // 1024)
    t0 = time.monotonic()

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = image.size
    logger.info("Image size: %dx%d px", w, h)

    # detail=1 returns [[bbox_points, text, confidence], ...]
    results = get_reader().readtext(np.array(image), detail=1)
    elapsed = time.monotonic() - t0
    logger.info("EasyOCR completed in %.0fms — %d text regions detected", elapsed * 1000, len(results))

    words, boxes = [], []
    for (bbox_points, text, conf) in results:
        # bbox_points: [[x0,y0],[x1,y0],[x1,y1],[x0,y1]]
        xs = [p[0] for p in bbox_points]
        ys = [p[1] for p in bbox_points]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)

        # Normalize to 0-1000 as required by LayoutLMv3
        nx0 = int(min(max(x0 / w, 0), 1) * 1000)
        ny0 = int(min(max(y0 / h, 0), 1) * 1000)
        nx1 = int(min(max(x1 / w, 0), 1) * 1000)
        ny1 = int(min(max(y1 / h, 0), 1) * 1000)

        # Split multi-word detections into individual tokens
        for word in text.split():
            words.append(word)
            boxes.append([nx0, ny0, nx1, ny1])

    plain_text = " ".join(words)
    logger.info("OCR extracted %d words, %d chars", len(words), len(plain_text))
    logger.info("OCR text preview: %.200s%s", plain_text, "..." if len(plain_text) > 200 else "")
    return image, words, boxes, plain_text
