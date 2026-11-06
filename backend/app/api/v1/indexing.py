from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request

from app.core.auth import require_write_access
from app.schemas.ingestion import JobAccepted, JobInput, JobResponse
from app.services.indexing.jobs import job_response
from app.services.indexing.submission import submit_job

router = APIRouter(
    prefix="/index/jobs", tags=["indexing"], dependencies=[Depends(require_write_access)]
)


@router.post("", status_code=202, response_model=JobAccepted)
async def submit(
    options: JobInput, request: Request, idempotency_key: Annotated[str | None, Header()] = None
):
    return await submit_job(request.app.state.services, options, idempotency_key)


@router.get("/{job_id}", response_model=JobResponse)
async def inspect(
    job_id: UUID,
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: str | None = None,
):
    return await job_response(request.app.state.services, job_id, limit, cursor)
