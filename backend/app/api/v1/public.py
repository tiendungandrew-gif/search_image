from fastapi import APIRouter, Depends, Request, Response

from app.core.guest import require_guest_access
from app.schemas.workspace import WorkspaceSnapshot
from app.services.workspace import workspace_snapshot

router = APIRouter(prefix="/public", tags=["Public"], dependencies=[Depends(require_guest_access)])


@router.get("/workspace", response_model=WorkspaceSnapshot)
async def workspace(request: Request, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Cookie, Authorization"
    value = await workspace_snapshot(request)
    value["public_datasets"] = request.state.public_datasets
    value["limits"]["top_k"] = min(
        value["limits"]["top_k"], request.app.state.settings.guest_max_top_k
    )
    for key in value["capabilities"]:
        if key != "text_search":
            value["capabilities"][key] = False
    value["rag"] = {"enabled": False, "configured": False, "streaming": False}
    value["agent"] = {"enabled": False, "llm_planning": False}
    return value
