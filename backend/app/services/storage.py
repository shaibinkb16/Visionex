from datetime import datetime, timezone

from bson import Binary, ObjectId

from ..core.dependencies import get_db


async def save_document(
    filename: str,
    ocr_text: str,
    extracted: dict,
    confidence: dict,
    method: str,
    pipeline_trace: list | None = None,
    file_bytes: bytes | None = None,
    content_type: str | None = None,
) -> str:
    doc: dict = {
        "filename": filename,
        "ocr_text": ocr_text,
        "extracted": extracted,
        "confidence": confidence,
        "extraction_method": method,
        "pipeline_trace": pipeline_trace or [],
        "created_at": datetime.now(timezone.utc),
        "content_type": content_type,
        "has_file": bool(file_bytes),
    }
    if file_bytes:
        doc["file_data"] = Binary(file_bytes)
    result = await get_db()["documents"].insert_one(doc)
    return str(result.inserted_id)


async def get_latest_document() -> dict | None:
    return await get_db()["documents"].find_one(
        {},
        sort=[("created_at", -1)],
    )


async def get_document_by_id(doc_id: str) -> dict | None:
    try:
        oid = ObjectId(doc_id)
    except Exception:
        return None
    return await get_db()["documents"].find_one({"_id": oid})


async def list_document_summaries(limit: int = 100) -> list[dict]:
    cursor = (
        get_db()["documents"]
        .find(
            {},
            projection={"file_data": 0, "ocr_text": 0},
        )
        .sort("created_at", -1)
        .limit(limit)
    )
    rows = []
    async for row in cursor:
        row["_id"] = str(row["_id"])
        rows.append(row)
    return rows


async def get_document_file_payload(doc_id: str) -> dict | None:
    try:
        oid = ObjectId(doc_id)
    except Exception:
        return None
    doc = await get_db()["documents"].find_one(
        {"_id": oid},
        projection={"file_data": 1, "content_type": 1, "filename": 1},
    )
    if not doc or not doc.get("file_data"):
        return None
    data = bytes(doc["file_data"])
    return {
        "content": data,
        "content_type": doc.get("content_type") or "application/octet-stream",
        "filename": doc.get("filename") or "document",
    }
