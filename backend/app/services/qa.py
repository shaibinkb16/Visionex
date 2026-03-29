import json
import logging
import time

from groq import Groq
from ..core.config import settings
from ..utils.sanitize import sanitize
from .storage import get_document_by_id, get_latest_document

logger = logging.getLogger(__name__)


def _get_groq_client() -> Groq:
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured")
    return Groq(api_key=settings.GROQ_API_KEY)


async def answer_question(question: str, document_id: str | None = None) -> tuple[str, str]:
    logger.info("── QA pipeline start ──────────────────────────────────")
    logger.info("Question: %s", question)

    if document_id:
        doc = await get_document_by_id(document_id)
        if not doc:
            return "No document found for the selected id.", ""
    else:
        doc = await get_latest_document()
    if not doc:
        logger.warning("No documents found in database.")
        return "No documents have been processed yet.", ""

    doc_id = str(doc["_id"])
    logger.info("Using document: %s (file: %s)", doc_id, doc.get("filename", "unknown"))
    logger.info("Extracted context: %s", doc["extracted"])

    context = json.dumps(doc["extracted"], indent=2)
    clean_q = sanitize(question)

    try:
        client = _get_groq_client()
    except Exception as e:
        logger.warning("Groq client unavailable for QA: %s", e)
        return "Question answering is unavailable because GROQ_API_KEY is not configured.", doc_id

    logger.info(f"Calling Groq for QA ({settings.GROQ_MODEL_ID})...")
    t0 = time.monotonic()

    resp = client.chat.completions.create(
        model=settings.GROQ_MODEL_ID,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant. Answer questions using only "
                    f"the following extracted receipt data:\n{context}"
                ),
            },
            {"role": "user", "content": clean_q},
        ],
        temperature=0,
    )

    elapsed = time.monotonic() - t0
    answer = resp.choices[0].message.content.strip()
    logger.info("Groq QA responded in %.0fms", elapsed * 1000)
    logger.info("Answer: %s", answer)
    logger.info("── QA pipeline end ────────────────────────────────────")

    return answer, doc_id
