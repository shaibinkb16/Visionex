from datetime import datetime

from pydantic import BaseModel, Field
from typing import Optional


class ExtractedFields(BaseModel):
    total_amount: Optional[str] = None
    date: Optional[str] = None
    vendor_name: Optional[str] = None
    receipt_id: Optional[str] = None


class ConfidenceScores(BaseModel):
    total_amount: Optional[float] = None
    date: Optional[float] = None
    vendor_name: Optional[float] = None
    receipt_id: Optional[float] = None


class PipelineStep(BaseModel):
    stage: str
    status: str
    detail: str
    elapsed_ms: Optional[int] = None


class ExtractionResponse(BaseModel):
    document_id: str
    filename: str
    content_type: Optional[str] = None
    extracted: ExtractedFields
    confidence: ConfidenceScores
    extraction_method: str
    processing_time_ms: int
    pipeline_trace: list[PipelineStep] = []


class DocumentSummary(BaseModel):
    document_id: str
    filename: str
    created_at: datetime | None = None
    has_file: bool = False
    extraction_method: str | None = None


class QueryRequest(BaseModel):
    question: str
    document_id: Optional[str] = Field(
        default=None,
        description="If set, answer using this document's extraction; otherwise latest.",
    )


class QueryResponse(BaseModel):
    answer: str
    source_document_id: str


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    db_connected: bool
