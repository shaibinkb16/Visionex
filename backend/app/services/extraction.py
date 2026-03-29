"""
extraction.py  —  Fixed & Clean Receipt Extraction Pipeline
============================================================
Changes:
  1. Vendor  → first MENU span that looks like a real shop name.
  2. Total   → PRICE span immediately after a MENU span containing total keywords,
               fallback to largest price span.
  3. NER-first priority — NER wins when confidence >= threshold.
               LLM fills only fields that are still missing.
  4. Cleaner logging.
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections import Counter
from typing import Any, Tuple

import numpy as np
from PIL import Image
from groq import Groq
from google import genai
from google.genai import types
from optimum.onnxruntime import ORTModelForCustomTasks
from transformers import AutoConfig, AutoProcessor

try:
    from optimum.onnxruntime import ORTModelForTokenClassification
except ImportError:
    ORTModelForTokenClassification = None  # type: ignore[misc, assignment]

from ..core.config import settings
from ..utils.sanitize import sanitize

logger = logging.getLogger(__name__)

_model: Any | None = None
_processor = None

ENTITY_MAP = {
    "TOTAL": "total_amount",
    "DATE": "date",
    "VENDOR": "vendor_name",
    "RECEIPT_ID": "receipt_id",
}

_HEADER_NOISE = re.compile(
    r"^("
    r"cash\s*bill|tax\s*invoice|receipt|invoice|bill|order|"
    r"slip|memo|statement|ticket|voucher|"
    r"quantity|rate|amount|subtotal|sub-total|"
    r"sl\.?\s*no\.?|s\.?\s*no\.?|item|items|no\.?|"
    r"total|grand\s*total|net\s*total|"
    r"date|time|table|cashier|server|waiter|"
    r"thank\s*you|please\s*come\s*again"
    r")$",
    re.I,
)

_VENDOR_NOISE = re.compile(
    r"(your\s*logo|slogan|tax\s*invoice|invoice\b|billed\s*to|summary|"
    r"add\s*cgst|add\s*sgst|total\s*tax|total\s*outstanding|"
    r"pan\b|gst\b|hsn\b|date\b|email|@|upi|amount|quantity|rate)",
    re.I,
)

_VENDOR_HINT = re.compile(
    r"\b(shop|store|mart|restaurant|cafe|bakery|pharmacy|supermarket|traders|enterprises|"
    r"footwear|fashion|hotel)\b",
    re.I,
)

_TOTAL_LABEL = re.compile(r"\b(grand\s*total|net\s*total|total\s*amount|total)\b", re.I)

_DATE_PAT = re.compile(
    r"\b(\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}[./-]\d{2}[./-]\d{2})\b"
)
_MONTH_NAME_DATE_PAT = re.compile(
    r"\b(?:"
    r"(?:\d{1,2})(?:st|nd|rd|th)?[\s\-/.]+(?:jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|sept|september|oct|october|nov|november|dec|december)[\s\-/.]+\d{2,4}"
    r"|"
    r"(?:jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|sept|september|oct|october|nov|november|dec|december)[\s\-/.]+(?:\d{1,2})(?:st|nd|rd|th)?[\s\-/.]+\d{2,4}"
    r")\b",
    re.I,
)
_RECEIPT_PAT = re.compile(
    r"(?:bill|receipt|invoice|order|txn|transaction)\s*(?:no\.?|number|id|#)\s*[:\-]?\s*"
    r"([A-Z0-9][A-Z0-9\-_/\.]{1,})",
    re.I,
)
_RECEIPT_TOKEN_PAT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-_/\.]{2,}$")
_RECEIPT_HAS_DIGIT = re.compile(r"\d")
_TOTAL_LINE_PAT = re.compile(
    r"(?:grand\s*total|net\s*total|total\s*amount|amount\s*due|total)\s*[:\-]?\s*([\$€£₹]?[\d][\d,]*(?:\.\d{1,2})?)",
    re.I,
)

# Initialize LLM clients lazily (only if API keys are set)
_groq_client = None
_gemini_client = None

GROQ_MODEL = "llama-3.3-70b-versatile"
GEMINI_MODEL = "gemini-2.0-flash"


def _get_groq_client():
    """Lazy initialize Groq client only if API key is available."""
    global _groq_client
    if _groq_client is None:
        if not settings.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY not configured. Set it in environment variables.")
        _groq_client = Groq(api_key=settings.GROQ_API_KEY)
    return _groq_client


def _get_gemini_client():
    """Lazy initialize Gemini client only if API key is available."""
    global _gemini_client
    if _gemini_client is None:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY not configured. Set it in environment variables.")
        _gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _gemini_client


_LLM_PROMPT = """Extract these fields from the receipt text and return JSON only:
{{"total_amount": null, "date": null, "vendor_name": null, "receipt_id": null}}

Rules:
- total_amount: prefer final total / grand total
- date: receipt date in any visible format
- vendor_name: store/business name
- receipt_id: bill/invoice/receipt/transaction id
- Use null if unavailable

Receipt text:
{text}

Return only valid JSON.
"""


def load_model() -> None:
    global _model, _processor
    logger.info("Loading LayoutLMv3 ONNX model: %s", settings.HF_MODEL_ID)
    t0 = time.perf_counter()
    if not settings.HF_MODEL_ID or "your-username/" in settings.HF_MODEL_ID:
        logger.warning(
            "HF_MODEL_ID is a placeholder (%s). Skipping NER model load.",
            settings.HF_MODEL_ID,
        )
        _model = None
        _processor = None
        return
    try:
        cfg = AutoConfig.from_pretrained(settings.HF_MODEL_ID)
        model_type = str(getattr(cfg, "model_type", "")).lower()
        is_layout_model = "layoutlm" in model_type

        _processor = AutoProcessor.from_pretrained(settings.HF_MODEL_ID, apply_ocr=False)
        # LayoutLM models require bbox + pixel_values, so custom tasks wrapper is mandatory.
        _model = None
        try:
            _model = ORTModelForCustomTasks.from_pretrained(
                settings.HF_MODEL_ID, file_name="model.onnx"
            )
            logger.info("Loaded ORTModelForCustomTasks from %s", settings.HF_MODEL_ID)
        except Exception as e:
            if is_layout_model:
                logger.error(
                    "ORTModelForCustomTasks load failed for layout model (%s). "
                    "Skipping NER model load to avoid invalid bbox inference path.",
                    e,
                )
                _model = None
            else:
                logger.info("ORTModelForCustomTasks load failed (%s), trying token-classification wrapper…", e)
            if _model is None and (not is_layout_model) and ORTModelForTokenClassification is not None:
                _model = ORTModelForTokenClassification.from_pretrained(settings.HF_MODEL_ID)
                logger.info("Loaded ORTModelForTokenClassification from %s", settings.HF_MODEL_ID)
        if _model is None:
            raise RuntimeError("Could not load a compatible ONNX model wrapper")
        logger.info(
            "LayoutLMv3 loaded in %.2fs ✓ | inputs: %s",
            time.perf_counter() - t0,
            list(_model.input_names.keys()),
        )
    except Exception as exc:
        logger.error("Model load failed: %s", exc)
        _model = None
        _processor = None


def is_model_loaded() -> bool:
    return _model is not None and _processor is not None


def _softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max(axis=-1, keepdims=True))
    return e / e.sum(axis=-1, keepdims=True)


def _extract_number(text: str) -> float | None:
    m = re.search(r"\d[\d,]*(?:\.\d+)?", text.replace(" ", ""))
    if not m:
        return None
    try:
        return float(m.group().replace(",", ""))
    except ValueError:
        return None


def _parse_llm_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.replace("json", "", 1).strip()
    data = json.loads(raw)
    return {
        "total_amount": data.get("total_amount") or None,
        "date": data.get("date") or None,
        "vendor_name": data.get("vendor_name") or None,
        "receipt_id": data.get("receipt_id") or None,
    }


def _normalize_ocr_text(text: str) -> str:
    # Normalize repeated whitespace and OCR separators around numeric date patterns.
    t = re.sub(r"\s+", " ", text)
    t = re.sub(r"(?<=\d)[|](?=\d)", "/", t)
    t = re.sub(r"(?<=\d)[,](?=\d{2}(\D|$))", ".", t)
    return t.strip()


async def _groq_extract(text: str) -> dict:
    logger.info("Calling Groq fallback...")
    try:
        client = _get_groq_client()
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": _LLM_PROMPT.format(text=text)}],
            temperature=0,
        )
        return _parse_llm_json(resp.choices[0].message.content)
    except RuntimeError as e:
        raise RuntimeError(f"Groq extraction failed: {e}")


async def _gemini_extract(text: str) -> dict:
    logger.info("Calling Gemini fallback...")
    try:
        client = _get_gemini_client()
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=_LLM_PROMPT.format(text=text),
            config=types.GenerateContentConfig(temperature=0),
        )
        return _parse_llm_json(resp.text)
    except RuntimeError as e:
        raise RuntimeError(f"Gemini extraction failed: {e}")


def _aggregate_spans(word_preds: dict[int, tuple[str, float, str]]) -> list[tuple[str, str, float]]:
    spans: list[tuple[str, str, float]] = []
    current_entity: str | None = None
    current_words: list[str] = []
    current_scores: list[float] = []

    def flush() -> None:
        nonlocal current_entity, current_words, current_scores
        if current_entity and current_words:
            spans.append(
                (
                    current_entity,
                    " ".join(current_words),
                    round(sum(current_scores) / len(current_scores), 4),
                )
            )
        current_entity = None
        current_words = []
        current_scores = []

    for wid in sorted(word_preds):
        label, score, word = word_preds[wid]
        if label.startswith("B-"):
            flush()
            current_entity = label[2:]
            current_words = [word]
            current_scores = [score]
        elif label.startswith("I-") and current_entity == label[2:]:
            current_words.append(word)
            current_scores.append(score)
        else:
            flush()

    flush()
    return spans


def _derive_vendor(menu_spans: list[tuple[str, float]]) -> tuple[str | None, float]:
    best_text = None
    best_score = float("-inf")
    best_conf = 0.0

    for text, conf in menu_spans:
        cleaned = _clean_vendor_text(text)
        if not _is_vendor_candidate(cleaned):
            continue

        score = _score_vendor_candidate(cleaned, conf)
        if score > best_score:
            best_text = cleaned
            best_score = score
            best_conf = conf

    if best_text:
        return best_text, best_conf
    return None, 0.0


def _clean_vendor_text(text: str) -> str:
    s = text.strip(" -:;,.|")
    # Remove common promotional/header fragments.
    s = re.sub(r"(?i)\byour\s*logo\b", "", s)
    s = re.sub(r"(?i)\bslogan\s*here\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    # Trim trailing 'Shop No...' style address fragment.
    s = re.sub(r"(?i)\bshop\s*no\.?\b.*$", "", s).strip(" -:;,.|")
    return s


def _is_vendor_candidate(text: str) -> bool:
    if not text:
        return False
    if _HEADER_NOISE.match(text):
        return False
    if _VENDOR_NOISE.search(text):
        return False
    if len(text) < 3:
        return False
    # Reject heavily numeric candidates.
    alpha = len(re.findall(r"[A-Za-z]", text))
    digits = len(re.findall(r"\d", text))
    if digits > alpha:
        return False
    return True


def _score_vendor_candidate(text: str, conf: float) -> float:
    score = 0.0
    # Model confidence contributes but is not the only signal.
    score += conf * 10.0
    # Prefer medium-length names.
    words = len(text.split())
    score += min(words, 6) * 1.2
    # Strong boost for shop-like words.
    if _VENDOR_HINT.search(text):
        score += 8.0
    # Penalize suspicious generic strings.
    if re.search(r"(?i)^(cash\s*bill|tax\s*invoice|invoice)$", text):
        score -= 10.0
    return score


def _derive_total(raw_spans: list[tuple[str, str, float]], price_spans: list[tuple[str, float]]) -> tuple[str | None, float]:
    for i, (label, text, _) in enumerate(raw_spans):
        if "MENU" in label and _TOTAL_LABEL.search(text):
            for j in range(i + 1, len(raw_spans)):
                next_label, next_text, next_score = raw_spans[j]
                if "PRICE" in next_label:
                    if _extract_number(next_text) is not None:
                        return next_text.strip(), next_score
                    break
                if "MENU" in next_label:
                    break

    best_text: str | None = None
    best_score: float = 0.0
    best_val: float | None = None
    for txt, score in price_spans:
        n = _extract_number(txt)
        if n is not None and (best_val is None or n > best_val):
            best_val = n
            best_text = txt.strip()
            best_score = score

    return best_text, best_score


def _derive_total_from_text(ocr_text: str) -> str | None:
    # 1) Prefer explicit total-like lines.
    m = _TOTAL_LINE_PAT.search(ocr_text)
    if m:
        return m.group(1)

    # 2) Fallback: choose largest monetary-looking value in text.
    nums = re.findall(r"[\$€£₹]?[\d][\d,]*(?:\.\d{1,2})?", ocr_text)
    best_val = None
    best_txt = None
    for tok in nums:
        val = _extract_number(tok)
        if val is None:
            continue
        if best_val is None or val > best_val:
            best_val = val
            best_txt = tok
    return best_txt


def _derive_vendor_from_text(words: list[str]) -> str | None:
    # Try first few tokens as header candidate line.
    if not words:
        return None

    candidates: list[str] = []
    max_window = min(len(words), 8)
    for end in range(2, max_window + 1):
        cand = _clean_vendor_text(" ".join(words[:end]).strip(" :,-"))
        if not cand:
            continue
        if not _is_vendor_candidate(cand):
            continue
        candidates.append(cand)

    # Choose best plausible header candidate.
    if candidates:
        return max(candidates, key=lambda c: _score_vendor_candidate(c, 0.3))
    return None


def _extract_receipt_id_from_tokens(words: list[str]) -> str | None:
    lower_words = [w.lower() for w in words]
    label_tokens = {"bill", "receipt", "invoice", "order", "txn", "transaction"}
    marker_tokens = {"no", "no.", "number", "id", "#"}
    stop_tokens = {"date", "time", "total", "amount", "qty", "quantity"}

    for i, w in enumerate(lower_words):
        if w in label_tokens:
            window = words[i + 1 : i + 8]
            seen_marker = False
            for tok in window:
                clean_tok = tok.strip(":#;,.()[]{}")
                lower_tok = clean_tok.lower()
                if lower_tok in marker_tokens:
                    seen_marker = True
                    continue
                if clean_tok.lower() in stop_tokens:
                    break
                if _RECEIPT_TOKEN_PAT.match(clean_tok):
                    if seen_marker and lower_tok not in marker_tokens:
                        return clean_tok
    return None


def _derive_date_from_menu_spans(menu_spans: list[tuple[str, float]]) -> tuple[str | None, float]:
    # Prefer spans that explicitly contain 'date'.
    prioritized = sorted(menu_spans, key=lambda x: ("date" not in x[0].lower(),))
    for text, score in prioritized:
        m = _DATE_PAT.search(text)
        if m:
            return m.group(1), score
        m2 = _MONTH_NAME_DATE_PAT.search(text)
        if m2:
            return m2.group(0), score
    return None, 0.0


def _derive_receipt_from_menu_spans(menu_spans: list[tuple[str, float]]) -> tuple[str | None, float]:
    # Prefer bill/receipt-like spans first.
    prioritized = sorted(
        menu_spans,
        key=lambda x: not any(k in x[0].lower() for k in ("bill", "receipt", "invoice", "order", "txn", "transaction")),
    )

    for text, score in prioritized:
        m = _RECEIPT_PAT.search(text)
        if m and _RECEIPT_HAS_DIGIT.search(m.group(1)):
            return m.group(1), score

        # Extra fallback inside a receipt-like MENU span: first token containing digit.
        if any(k in text.lower() for k in ("bill", "receipt", "invoice", "order", "txn", "transaction")):
            for tok in text.split():
                clean_tok = tok.strip(":#;,.()[]{}")
                if _RECEIPT_TOKEN_PAT.match(clean_tok) and _RECEIPT_HAS_DIGIT.search(clean_tok):
                    return clean_tok, score

    return None, 0.0


def _run_ner(image: Image.Image, words: list[str], boxes: list[list[int]]) -> tuple[dict[str, str | None], dict[str, float]]:
    logger.info("Running LayoutLMv3 NER on %d words...", len(words))

    encoding = _processor(
        image,
        words,
        boxes=boxes,
        return_tensors="pt",
        truncation=True,
        max_length=512,
        padding="max_length",
    )

    onnx_inputs = {k: encoding[k] for k in _model.input_names if k in encoding}
    t0 = time.perf_counter()
    outputs = _model(**onnx_inputs)
    logger.info("ONNX inference in %dms", int((time.perf_counter() - t0) * 1000))

    logits = outputs["logits"] if isinstance(outputs, dict) else outputs.logits
    logits = np.asarray(logits)[0]
    probs = _softmax(logits)
    pred_ids = np.argmax(logits, axis=-1)
    pred_conf = probs[np.arange(len(pred_ids)), pred_ids]

    id2label = _model.config.id2label
    word_ids = encoding.word_ids(batch_index=0)

    word_preds: dict[int, tuple[str, float, str]] = {}
    for idx, wid in enumerate(word_ids):
        if wid is None or wid in word_preds:
            continue
        word_preds[wid] = (
            id2label[pred_ids[idx]],
            float(pred_conf[idx]),
            words[wid] if wid < len(words) else "",
        )

    raw_spans = _aggregate_spans(word_preds)
    logger.info("Raw spans: %s", [(e, t) for e, t, _ in raw_spans])

    fields: dict[str, str | None] = {
        "vendor_name": None,
        "total_amount": None,
        "date": None,
        "receipt_id": None,
    }
    confidence: dict[str, float] = {}

    for entity, text, score in raw_spans:
        key = ENTITY_MAP.get(entity)
        if key and key not in fields:
            fields[key] = text.strip()
            confidence[key] = score

    menu_spans = [(txt, sc) for ent, txt, sc in raw_spans if ent == "MENU"]
    price_spans = [(txt, sc) for ent, txt, sc in raw_spans if ent == "PRICE"]

    if fields.get("vendor_name") is None:
        vendor, vendor_score = _derive_vendor(menu_spans)
        if vendor:
            fields["vendor_name"] = vendor
            confidence["vendor_name"] = vendor_score

    if fields.get("total_amount") is None:
        total, total_score = _derive_total(raw_spans, price_spans)
        if total:
            fields["total_amount"] = total
            confidence["total_amount"] = total_score

    # Pull date and receipt id from model spans (MENU lines often contain "Date ..." and "Bill No ...").
    if fields.get("date") is None:
        date_val, date_score = _derive_date_from_menu_spans(menu_spans)
        if date_val:
            fields["date"] = date_val
            confidence["date"] = date_score

    if fields.get("receipt_id") is None:
        rid, rid_score = _derive_receipt_from_menu_spans(menu_spans)
        if rid:
            fields["receipt_id"] = rid
            confidence["receipt_id"] = rid_score

    return fields, confidence


def _rule_based(ocr_text: str, words: list[str]) -> dict[str, str | None]:
    normalized = _normalize_ocr_text(ocr_text)
    fields = {
        "vendor_name": None,
        "total_amount": None,
        "date": None,
        "receipt_id": None,
    }

    # Date fallbacks: numeric first, then month-name forms.
    m_date = _DATE_PAT.search(normalized)
    if m_date:
        fields["date"] = m_date.group(1)
    else:
        m_date_text = _MONTH_NAME_DATE_PAT.search(normalized)
        if m_date_text:
            fields["date"] = m_date_text.group(0)

    # Receipt-id fallbacks: label regex then token-window inference.
    m_receipt = _RECEIPT_PAT.search(normalized)
    if m_receipt and _RECEIPT_HAS_DIGIT.search(m_receipt.group(1)):
        fields["receipt_id"] = m_receipt.group(1)
    else:
        tok_id = _extract_receipt_id_from_tokens(words)
        if tok_id and _RECEIPT_HAS_DIGIT.search(tok_id):
            fields["receipt_id"] = tok_id

    # Total fallback from OCR text when NER misses total.
    fields["total_amount"] = _derive_total_from_text(normalized)

    # Vendor fallback from top OCR tokens when NER misses vendor.
    fields["vendor_name"] = _derive_vendor_from_text(words)

    return fields


async def extract_fields(
    image: Image.Image,
    words: list[str],
    boxes: list[list[int]],
    plain_text: str,
    progress_cb=None,
) -> Tuple[dict, dict, str, list[dict[str, Any]]]:
    """Returns (fields, confidence, method, pipeline_trace)."""
    logger.info("── Extraction pipeline start ──────────────────────────")

    all_keys = {"vendor_name", "total_amount", "date", "receipt_id"}
    trace: list[dict[str, Any]] = []

    def add_step(stage: str, status: str, detail: str, elapsed_ms: int | None = None) -> None:
        step = {
            "stage": stage,
            "status": status,
            "detail": detail,
            "elapsed_ms": elapsed_ms,
        }
        trace.append(step)
        if progress_cb:
            try:
                progress_cb(step)
            except Exception:
                pass

    add_step("sanitize", "done", "OCR text sanitized and normalized")
    clean_text = sanitize(plain_text)

    ner_fields = {k: None for k in all_keys}
    ner_conf: dict[str, float] = {}

    if is_model_loaded() and words:
        try:
            ner_t0 = time.perf_counter()
            ner_fields, ner_conf = _run_ner(image, words, boxes)
            add_step(
                "ner",
                "done",
                f"NER processed {len(words)} words and found {len([k for k, v in ner_fields.items() if v])} candidate fields",
                int((time.perf_counter() - ner_t0) * 1000),
            )
        except Exception as exc:
            logger.warning("NER failed: %s", exc)
            add_step("ner", "error", f"NER inference failed: {exc}")
    else:
        add_step("ner", "skipped", "Model not loaded or OCR words are empty")

    accepted = {k: None for k in all_keys}
    confidence = {k: 0.0 for k in all_keys}

    # NER-first priority with threshold gate.
    # For date and receipt_id we trust model-derived values when present,
    # even if confidence is below the global threshold.
    for k in all_keys:
        v = ner_fields.get(k)
        c = float(ner_conf.get(k, 0.0))
        if not v:
            continue

        if k in {"date", "receipt_id"}:
            accepted[k] = v
            confidence[k] = round(c, 4)
            continue

        if c >= settings.CONFIDENCE_THRESHOLD:
            accepted[k] = v
            confidence[k] = round(c, 4)

    logger.info("NER accepted fields: %s", {k: v for k, v in accepted.items() if v})
    add_step(
        "threshold_gate",
        "done",
        f"Accepted {len([k for k, v in accepted.items() if v])} fields above confidence threshold {settings.CONFIDENCE_THRESHOLD}",
    )

    # Rule-based fills only missing fields (no API cost)
    rule_fields = _rule_based(clean_text, words)
    for k in all_keys:
        if accepted[k] is None and rule_fields.get(k):
            accepted[k] = rule_fields[k]
            confidence[k] = 0.0
    add_step(
        "rule_fallback",
        "done",
        f"Rule engine filled {len([k for k, v in accepted.items() if v and confidence.get(k, 0) == 0.0])} fields",
    )

    # Low-confidence NER rescue before LLM (still cheaper than API calls).
    for k in all_keys:
        if accepted[k] is None and ner_fields.get(k):
            accepted[k] = ner_fields[k]
            confidence[k] = round(float(ner_conf.get(k, 0.0)), 4)
            logger.info("Using low-confidence NER fallback for %s: %s", k, accepted[k])
    add_step(
        "ner_rescue",
        "done",
        f"Low-confidence NER rescue produced {len([k for k, v in accepted.items() if v])} total fields so far",
    )

    # Final vendor cleanup gate.
    if accepted.get("vendor_name"):
        cleaned_vendor = _clean_vendor_text(str(accepted["vendor_name"]))
        if not _is_vendor_candidate(cleaned_vendor):
            accepted["vendor_name"] = None
            confidence["vendor_name"] = 0.0
        else:
            accepted["vendor_name"] = cleaned_vendor

    missing = [k for k in all_keys if not accepted.get(k)]

    if not missing:
        method = "ner+rule"
        logger.info("Final fields: %s", accepted)
        logger.info("── Extraction pipeline end (method=%s) ───────", method)
        add_step("finalize", "done", f"Extraction completed with method={method}")
        return accepted, confidence, method, trace

    logger.info("Missing fields: %s — triggering LLM fallback", missing)

    llm_fields: dict[str, Any] = {}
    method = "llm"
    try:
        llm_t0 = time.perf_counter()
        llm_fields = await _groq_extract(clean_text)
        add_step("llm_groq", "done", "Groq fallback returned structured fields", int((time.perf_counter() - llm_t0) * 1000))
    except Exception as exc:
        logger.warning("Groq failed: %s — trying Gemini", exc)
        add_step("llm_groq", "error", f"Groq fallback failed: {exc}")
        try:
            gem_t0 = time.perf_counter()
            llm_fields = await _gemini_extract(clean_text)
            add_step("llm_gemini", "done", "Gemini fallback returned structured fields", int((time.perf_counter() - gem_t0) * 1000))
        except Exception as exc2:
            logger.error("Gemini also failed: %s", exc2)
            logger.info("── Extraction pipeline end (method=ner_partial) ────")
            add_step("llm_gemini", "error", f"Gemini fallback failed: {exc2}")
            add_step("finalize", "done", "Extraction completed with partial NER output")
            return accepted, confidence, "ner_partial", trace

    # LLM fills only still-missing fields
    for k in missing:
        if llm_fields.get(k):
            accepted[k] = llm_fields[k]
            confidence[k] = 0.0

    logger.info("Final fields: %s", accepted)
    logger.info("── Extraction pipeline end (method=%s) ───────", method)
    add_step("finalize", "done", f"Extraction completed with method={method}")
    return accepted, confidence, method, trace
