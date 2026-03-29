from fastapi import APIRouter, HTTPException
from ..services.qa import answer_question
from ..models.schemas import QueryRequest, QueryResponse

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query(body: QueryRequest):
    if not body.question.strip():
        raise HTTPException(400, "Question cannot be empty.")

    answer, doc_id = await answer_question(body.question, body.document_id)
    return QueryResponse(answer=answer, source_document_id=doc_id)
