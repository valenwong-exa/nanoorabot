"""Knowledge Base routes backed by the Oracle Vector Search API."""

from __future__ import annotations

import asyncio
import mimetypes
import os
from typing import Annotated, Any, Literal

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from webui.api.deps import get_services, require_admin
from webui.api.gateway import ServiceContainer
from webui.api.models import (
    KnowledgeBaseDeleteResponse,
    KnowledgeBaseDocumentListItem,
    KnowledgeBaseDocumentListResponse,
    KnowledgeBaseHealthResponse,
    KnowledgeBaseSearchRequest,
    KnowledgeBaseSearchResult,
    KnowledgeBaseUploadResponse,
)

router = APIRouter()

_UPLOAD_TIMEOUT = httpx.Timeout(600.0, connect=10.0)
_SEARCH_TIMEOUT = httpx.Timeout(600.0, connect=10.0)
_ALLOWED_SUFFIXES = {".pdf", ".txt"}
_DEFAULT_ENGINE: Literal["qwen", "bge"] = "qwen"
_ENGINE_CONFIGS = {
    "qwen": {
        "base_url": "http://127.0.0.1:19000",
        "docs_table": "LC_DEMO_DOCUMENTS",
        "chunks_table": "LC_DEMO_CHUNKS",
    },
    "bge": {
        "base_url": "http://127.0.0.1:19001",
        "docs_table": "LC_DEMO_DOCUMENTS_BGE",
        "chunks_table": "LC_DEMO_CHUNKS_BGE",
    },
}


def _resolve_engine(
    engine: str | None,
) -> tuple[Literal["qwen", "bge"], dict[str, str]]:
    normalized = (engine or _DEFAULT_ENGINE).strip().lower()
    if normalized not in _ENGINE_CONFIGS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unsupported knowledge base engine.")

    default_config = _ENGINE_CONFIGS[normalized]
    base_url = os.getenv(
        f"NANOBOT_VECTOR_API_BASE_{normalized.upper()}",
        os.getenv("NANOBOT_VECTOR_API_BASE", default_config["base_url"]),
    ).rstrip("/")

    docs_table = os.getenv(
        f"NANOBOT_VECTOR_DOCS_TABLE_{normalized.upper()}",
        default_config["docs_table"],
    )
    chunks_table = os.getenv(
        f"NANOBOT_VECTOR_CHUNKS_TABLE_{normalized.upper()}",
        default_config["chunks_table"],
    )

    return normalized, {
        "base_url": base_url,
        "docs_table": docs_table,
        "chunks_table": chunks_table,
    }


def _raise_upstream_error(exc: httpx.HTTPStatusError) -> None:
    detail = exc.response.text
    try:
        payload = exc.response.json()
        if isinstance(payload, dict):
            detail = str(payload.get("detail") or payload)
    except ValueError:
        pass
    raise HTTPException(exc.response.status_code, detail) from exc


def _get_oracle_connection(svc: ServiceContainer):
    try:
        import oracledb
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "python-oracledb is not installed. Install the 'oracledb' package first."
        ) from exc

    config = svc.oracle_config.load()
    return oracledb.connect(
        user=config.user,
        password=config.password,
        dsn=config.dsn,
    )


def _list_documents(
    svc: ServiceContainer,
    *,
    engine: str,
    page: int,
    page_size: int,
    keyword: str | None,
    document_type: str | None,
) -> KnowledgeBaseDocumentListResponse:
    _, config = _resolve_engine(engine)
    docs_table = config["docs_table"]
    chunks_table = config["chunks_table"]
    conditions: list[str] = []
    bind_vars: dict[str, Any] = {}

    if keyword:
        conditions.append("lower(d.document_name) like :keyword")
        bind_vars["keyword"] = f"%{keyword.strip().lower()}%"

    if document_type:
        conditions.append("lower(d.document_type) = :document_type")
        bind_vars["document_type"] = document_type.strip().lower()

    where_clause = f" where {' and '.join(conditions)}" if conditions else ""

    count_sql = f"""
        select count(*)
          from {docs_table} d
        {where_clause}
    """

    data_sql = f"""
        select d.doc_id,
               d.document_name,
               d.document_type,
               d.source_file,
               to_char(d.created_at, 'YYYY-MM-DD HH24:MI:SS'),
               (
                 select count(*)
                   from {chunks_table} c
                  where c.doc_id = d.doc_id
               ) as chunk_count
          from {docs_table} d
        {where_clause}
         order by d.created_at desc, d.doc_id desc
         offset :offset_rows rows fetch next :page_size rows only
    """

    with _get_oracle_connection(svc) as connection:
        with connection.cursor() as cursor:
            cursor.execute(count_sql, bind_vars)
            total_row = cursor.fetchone()
            total = int(total_row[0]) if total_row and total_row[0] is not None else 0

            data_bind_vars = {
                **bind_vars,
                "offset_rows": (page - 1) * page_size,
                "page_size": page_size,
            }
            cursor.execute(data_sql, data_bind_vars)
            rows = cursor.fetchall() or []

    items = [
        KnowledgeBaseDocumentListItem(
            docId=int(row[0]),
            documentName=str(row[1]),
            documentType=str(row[2]),
            sourceFile=str(row[3]) if row[3] is not None else None,
            createdAt=str(row[4]) if row[4] is not None else None,
            chunkCount=int(row[5] or 0),
        )
        for row in rows
    ]

    return KnowledgeBaseDocumentListResponse(
        items=items,
        total=total,
        page=page,
        pageSize=page_size,
    )


def _delete_document(
    svc: ServiceContainer,
    *,
    engine: str,
    doc_id: int,
) -> KnowledgeBaseDeleteResponse:
    _, config = _resolve_engine(engine)
    docs_table = config["docs_table"]
    chunks_table = config["chunks_table"]
    with _get_oracle_connection(svc) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"select count(*) from {docs_table} where doc_id = :doc_id",
                {"doc_id": doc_id},
            )
            row = cursor.fetchone()
            exists = bool(row and row[0])
            if not exists:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")

            cursor.execute(
                f"delete from {chunks_table} where doc_id = :doc_id",
                {"doc_id": doc_id},
            )
            deleted_chunk_count = int(cursor.rowcount or 0)

            cursor.execute(
                f"delete from {docs_table} where doc_id = :doc_id",
                {"doc_id": doc_id},
            )
            deleted_document_count = int(cursor.rowcount or 0)
            connection.commit()

    return KnowledgeBaseDeleteResponse(
        success=True,
        docId=doc_id,
        deletedDocumentCount=deleted_document_count,
        deletedChunkCount=deleted_chunk_count,
    )


@router.get("/health", response_model=KnowledgeBaseHealthResponse)
async def get_knowledge_base_health(
    _admin: Annotated[dict, Depends(require_admin)],
    engine: Annotated[Literal["qwen", "bge"], Query()] = _DEFAULT_ENGINE,
) -> KnowledgeBaseHealthResponse:
    _, config = _resolve_engine(engine)
    base_url = config["base_url"]
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{base_url}/health")
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _raise_upstream_error(exc)
        except httpx.RequestError as exc:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                f"Knowledge base API is unavailable: {exc}",
            ) from exc

    data = response.json()
    return KnowledgeBaseHealthResponse(
        status=str(data.get("status", "unknown")),
        baseUrl=base_url,
    )


@router.get("/documents", response_model=KnowledgeBaseDocumentListResponse)
async def list_knowledge_base_documents(
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
    engine: Annotated[Literal["qwen", "bge"], Query()] = _DEFAULT_ENGINE,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 10,
    keyword: Annotated[str | None, Query()] = None,
    document_type: Annotated[str | None, Query(alias="documentType")] = None,
) -> KnowledgeBaseDocumentListResponse:
    try:
        return await asyncio.to_thread(
            _list_documents,
            svc,
            engine=engine,
            page=page,
            page_size=page_size,
            keyword=keyword,
            document_type=document_type,
        )
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Failed to list documents: {exc}",
        ) from exc


@router.post("/upload", response_model=KnowledgeBaseUploadResponse)
async def upload_knowledge_base_document(
    file: Annotated[UploadFile, File(...)],
    _admin: Annotated[dict, Depends(require_admin)],
    engine: Annotated[Literal["qwen", "bge"], Form()] = _DEFAULT_ENGINE,
    chunk_size_tokens: Annotated[int, Form()] = 500,
    chunk_overlap_tokens: Annotated[int, Form()] = 50,
    source_file: Annotated[str, Form()] = "webui",
    document_type: Annotated[str | None, Form()] = None,
    device: Annotated[str, Form()] = "auto",
) -> KnowledgeBaseUploadResponse:
    _, config = _resolve_engine(engine)
    filename = file.filename or ""
    suffix = os.path.splitext(filename)[1].lower()
    if suffix not in _ALLOWED_SUFFIXES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Only .pdf and .txt files are supported.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uploaded file is empty.")

    guessed_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    payload: dict[str, Any] = {
        "chunk_size_tokens": str(chunk_size_tokens),
        "chunk_overlap_tokens": str(chunk_overlap_tokens),
        "source_file": source_file,
        "device": device,
        "docs_table": config["docs_table"],
        "chunks_table": config["chunks_table"],
    }
    if document_type:
        payload["document_type"] = document_type

    base_url = config["base_url"]
    async with httpx.AsyncClient(timeout=_UPLOAD_TIMEOUT) as client:
        try:
            response = await client.post(
                f"{base_url}/documents/upload",
                files={"file": (filename, content, guessed_type)},
                data=payload,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _raise_upstream_error(exc)
        except httpx.RequestError as exc:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                f"Knowledge base upload failed: {exc}",
            ) from exc

    data = response.json()
    return KnowledgeBaseUploadResponse(
        documentName=str(data.get("document_name", filename)),
        documentType=str(data.get("document_type", suffix.lstrip("."))),
        docId=data.get("doc_id"),
        inserted=bool(data.get("inserted")),
        parsedChunkCount=int(data.get("parsed_chunk_count", 0)),
        insertedChunkCount=int(data.get("inserted_chunk_count", 0)),
        fullTextLength=int(data.get("full_text_length", 0)),
        fullTextPreview=data.get("full_text_preview"),
    )


@router.delete("/documents/{doc_id}", response_model=KnowledgeBaseDeleteResponse)
async def delete_knowledge_base_document(
    doc_id: int,
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
    engine: Annotated[Literal["qwen", "bge"], Query()] = _DEFAULT_ENGINE,
) -> KnowledgeBaseDeleteResponse:
    try:
        return await asyncio.to_thread(_delete_document, svc, engine=engine, doc_id=doc_id)
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Failed to delete document: {exc}",
        ) from exc


@router.post("/search", response_model=list[KnowledgeBaseSearchResult])
async def search_knowledge_base(
    body: KnowledgeBaseSearchRequest,
    _admin: Annotated[dict, Depends(require_admin)],
) -> list[KnowledgeBaseSearchResult]:
    _, config = _resolve_engine(body.engine)
    payload: dict[str, Any] = {
        "prompt": body.prompt,
        "top_k": body.topK,
        "reranker_score": body.rerankerScore,
        "return_mode": "title",
        "device": body.device,
    }
    if body.documentType:
        payload["document_type"] = body.documentType

    base_url = config["base_url"]
    async with httpx.AsyncClient(timeout=_SEARCH_TIMEOUT) as client:
        try:
            response = await client.post(f"{base_url}/search", json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _raise_upstream_error(exc)
        except httpx.RequestError as exc:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                f"Knowledge base search failed: {exc}",
            ) from exc

    data = response.json()
    if not isinstance(data, list):
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Knowledge base API returned an invalid search response.",
        )

    results: list[KnowledgeBaseSearchResult] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        title = str(item.get("txt", "")).strip()
        if not title:
            continue
        try:
            score = float(item.get("score", 0.0))
        except (TypeError, ValueError):
            score = 0.0
        results.append(KnowledgeBaseSearchResult(title=title, score=score))
    return results
