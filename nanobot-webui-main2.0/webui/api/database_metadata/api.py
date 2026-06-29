"""FastAPI routes for SQLcl-backed database metadata tree access."""

from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel

from webui.api.database_metadata.metadata_service import DatabaseMetadataService
from webui.api.database_metadata.json_cache import default_cache_dir, oracle_ops_core_skill_dir
from webui.api.deps import get_current_user, get_services
from webui.api.gateway import ServiceContainer

router = APIRouter()
metadata_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="metadata-api")


async def _run_metadata_in_executor(func, /, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(metadata_executor, partial(func, *args, **kwargs))


def _service_for_workspace(svc: ServiceContainer) -> DatabaseMetadataService:
    workspace = Path(svc.config.workspace_path).expanduser()
    return DatabaseMetadataService(
        cache_base_dir=default_cache_dir(workspace),
        config_base_dir=oracle_ops_core_skill_dir(workspace),
    )


class OpenDatabaseMetadataRequest(BaseModel):
    connectionId: str
    sqlclConnectionName: str
    displayName: str


class OpenDatabaseMetadataResponse(BaseModel):
    success: bool
    fromCache: bool
    connectionId: str
    tree: dict[str, Any]


class DatabaseMetadataNodeRequest(BaseModel):
    connectionId: str
    sqlclConnectionName: str
    nodeId: str
    nodeType: str
    schemaName: str | None = None


class DatabaseMetadataNodeResponse(BaseModel):
    success: bool
    fromCache: bool
    connectionId: str
    node: dict[str, Any]


class TableDdlRequest(BaseModel):
    connectionId: str
    sqlclConnectionName: str
    schemaName: str
    tableName: str
    forceRefresh: bool = False


class TableDdlResponse(BaseModel):
    success: bool
    connectionId: str
    sqlText: str
    cachePath: str
    cacheHit: bool


class ProcedureDdlRequest(BaseModel):
    connectionId: str
    sqlclConnectionName: str
    schemaName: str
    procedureName: str
    forceRefresh: bool = False


class ProcedureDdlResponse(BaseModel):
    success: bool
    connectionId: str
    sqlText: str
    cachePath: str
    cacheHit: bool


class SourceDdlRequest(BaseModel):
    connectionId: str
    sqlclConnectionName: str
    schemaName: str
    objectType: str
    objectName: str
    forceRefresh: bool = False


class SourceDdlResponse(BaseModel):
    success: bool
    connectionId: str
    sqlText: str
    cachePath: str
    cacheHit: bool


@router.post("/open", response_model=OpenDatabaseMetadataResponse)
async def open_database_metadata(
    body: OpenDatabaseMetadataRequest,
    svc: ServiceContainer = Depends(get_services),
    _user: dict[str, Any] = Depends(get_current_user),
) -> OpenDatabaseMetadataResponse:
    started_at = time.perf_counter()
    logger.info(
        "HTTP open metadata tree start: connection_id={} sqlcl_connection={} display_name={}",
        body.connectionId,
        body.sqlclConnectionName,
        body.displayName,
    )
    try:
        result = await _run_metadata_in_executor(
            _service_for_workspace(svc).open_connection,
            connection_id=body.connectionId,
            sqlcl_connection_name=body.sqlclConnectionName,
            display_name=body.displayName,
        )
        logger.info(
            "HTTP open metadata tree success: connection_id={} sqlcl_connection={} from_cache={} elapsed_ms={:.1f}",
            body.connectionId,
            body.sqlclConnectionName,
            result["fromCache"],
            (time.perf_counter() - started_at) * 1000,
        )
        return OpenDatabaseMetadataResponse(**result)
    except ValueError as exc:
        logger.warning(
            "HTTP open metadata tree bad request: connection_id={} sqlcl_connection={} elapsed_ms={:.1f} detail={}",
            body.connectionId,
            body.sqlclConnectionName,
            (time.perf_counter() - started_at) * 1000,
            exc,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.warning(
            "HTTP open metadata tree failed: connection_id={} sqlcl_connection={} elapsed_ms={:.1f} detail={}",
            body.connectionId,
            body.sqlclConnectionName,
            (time.perf_counter() - started_at) * 1000,
            exc,
        )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/load-node", response_model=DatabaseMetadataNodeResponse)
async def load_database_metadata_node(
    body: DatabaseMetadataNodeRequest,
    svc: ServiceContainer = Depends(get_services),
    _user: dict[str, Any] = Depends(get_current_user),
) -> DatabaseMetadataNodeResponse:
    try:
        result = await _run_metadata_in_executor(
            _service_for_workspace(svc).load_node,
            connection_id=body.connectionId,
            sqlcl_connection_name=body.sqlclConnectionName,
            node_id=body.nodeId,
            node_type=body.nodeType,
            schema_name=body.schemaName,
        )
        return DatabaseMetadataNodeResponse(**result)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/refresh-node", response_model=DatabaseMetadataNodeResponse)
async def refresh_database_metadata_node(
    body: DatabaseMetadataNodeRequest,
    svc: ServiceContainer = Depends(get_services),
    _user: dict[str, Any] = Depends(get_current_user),
) -> DatabaseMetadataNodeResponse:
    try:
        result = await _run_metadata_in_executor(
            _service_for_workspace(svc).refresh_node,
            connection_id=body.connectionId,
            sqlcl_connection_name=body.sqlclConnectionName,
            node_id=body.nodeId,
            node_type=body.nodeType,
            schema_name=body.schemaName,
        )
        return DatabaseMetadataNodeResponse(**result)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/table-ddl", response_model=TableDdlResponse)
async def get_table_ddl(
    body: TableDdlRequest,
    svc: ServiceContainer = Depends(get_services),
    _user: dict[str, Any] = Depends(get_current_user),
) -> TableDdlResponse:
    try:
        result = await _run_metadata_in_executor(
            _service_for_workspace(svc).get_table_ddl,
            connection_id=body.connectionId,
            sqlcl_connection_name=body.sqlclConnectionName,
            schema_name=body.schemaName,
            table_name=body.tableName,
            force_refresh=body.forceRefresh,
        )
        return TableDdlResponse(**result)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/procedure-ddl", response_model=ProcedureDdlResponse)
async def get_procedure_ddl(
    body: ProcedureDdlRequest,
    svc: ServiceContainer = Depends(get_services),
    _user: dict[str, Any] = Depends(get_current_user),
) -> ProcedureDdlResponse:
    try:
        result = await _run_metadata_in_executor(
            _service_for_workspace(svc).get_procedure_ddl,
            connection_id=body.connectionId,
            sqlcl_connection_name=body.sqlclConnectionName,
            schema_name=body.schemaName,
            procedure_name=body.procedureName,
            force_refresh=body.forceRefresh,
        )
        return ProcedureDdlResponse(**result)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/source-ddl", response_model=SourceDdlResponse)
async def get_source_ddl(
    body: SourceDdlRequest,
    svc: ServiceContainer = Depends(get_services),
    _user: dict[str, Any] = Depends(get_current_user),
) -> SourceDdlResponse:
    try:
        result = await _run_metadata_in_executor(
            _service_for_workspace(svc).get_source_ddl,
            connection_id=body.connectionId,
            sqlcl_connection_name=body.sqlclConnectionName,
            schema_name=body.schemaName,
            object_type=body.objectType,
            object_name=body.objectName,
            force_refresh=body.forceRefresh,
        )
        return SourceDdlResponse(**result)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
