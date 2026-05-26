"""Workspace file serving with auth and workspace boundary checks."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from webui.api.deps import get_current_user, get_services
from webui.api.gateway import ServiceContainer

router = APIRouter()


def _resolve_safe(workspace: Path, path: str) -> Path:
    """Resolve a relative or absolute path and ensure it stays inside workspace."""
    candidate = Path(path)
    full = candidate.resolve() if candidate.is_absolute() else (workspace / path).resolve()

    workspace_resolved = workspace.resolve()
    try:
        full.relative_to(workspace_resolved)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Access denied: path outside workspace",
        ) from exc

    return full


@router.get("/file")
async def serve_workspace_file(
    path: Annotated[str, Query(..., description="Relative or absolute file path within the workspace")],
    _current_user: Annotated[dict, Depends(get_current_user)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> FileResponse:
    workspace = svc.config.workspace_path
    full = _resolve_safe(workspace, path)

    if not full.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    if not full.is_file():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Path is not a file")

    media_type, _ = mimetypes.guess_type(str(full))
    return FileResponse(
        str(full),
        media_type=media_type or "application/octet-stream",
        filename=full.name,
    )
