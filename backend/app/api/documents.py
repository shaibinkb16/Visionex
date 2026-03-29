from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ..models.schemas import DocumentSummary
from ..services.storage import get_document_file_payload, list_document_summaries

router = APIRouter()


@router.get("/documents", response_model=list[DocumentSummary])
async def list_documents(limit: int = 100):
    if limit < 1 or limit > 200:
        raise HTTPException(400, "limit must be between 1 and 200")
    rows = await list_document_summaries(limit=limit)
    out = []
    for row in rows:
        out.append(
            DocumentSummary(
                document_id=row["_id"],
                filename=row.get("filename") or "",
                created_at=row.get("created_at"),
                has_file=bool(row.get("has_file")),
                extraction_method=row.get("extraction_method"),
            )
        )
    return out


@router.get("/documents/{document_id}/file")
async def download_document_file(document_id: str):
    payload = await get_document_file_payload(document_id)
    if not payload:
        raise HTTPException(404, "File not found for this document (or legacy record without stored bytes).")

    ascii_name = payload["filename"].encode("ascii", "replace").decode("ascii") or "document"
    cd = f'inline; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(payload["filename"])}'

    return Response(
        content=payload["content"],
        media_type=payload["content_type"],
        headers={"Content-Disposition": cd},
    )
