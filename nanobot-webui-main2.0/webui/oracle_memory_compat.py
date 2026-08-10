"""Asynchronous Oracle persistence reused by the WebUI main3 compatibility layer."""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

_AUDIT_INSERT_SQL = """
insert into NB_AGENT_AUDIT (
    SESSION_KEY,
    TURN_ID,
    ITERATION_NO,
    LLM_CALL_SEQ,
    ATTEMPT_NO,
    REQUEST_PHASE,
    CHANNEL,
    CHAT_ID,
    PROVIDER_NAME,
    MODEL_NAME,
    MODEL_PRESET,
    REQUEST_STARTED_AT,
    RESPONSE_ENDED_AT,
    LATENCY_MS,
    FINISH_REASON,
    STOP_REASON,
    ERROR_KIND,
    ERROR_TYPE,
    ERROR_CODE,
    PROMPT_TOKENS,
    COMPLETION_TOKENS,
    TOTAL_TOKENS,
    TOOL_COUNT,
    REQUEST_MESSAGES_JSON,
    REQUEST_TOOLS_JSON,
    REQUEST_OPTIONS_JSON,
    RESPONSE_JSON,
    ERROR_MESSAGE
) values (
    :session_key,
    :turn_id,
    :iteration_no,
    :llm_call_seq,
    :attempt_no,
    :request_phase,
    :channel,
    :chat_id,
    :provider_name,
    :model_name,
    :model_preset,
    :request_started_at,
    :response_ended_at,
    :latency_ms,
    :finish_reason,
    :stop_reason,
    :error_kind,
    :error_type,
    :error_code,
    :prompt_tokens,
    :completion_tokens,
    :total_tokens,
    :tool_count,
    :request_messages_json,
    :request_tools_json,
    :request_options_json,
    :response_json,
    :error_message
)
"""

_MEMORY_INSERT_SQL = """
insert into NB_AGENT_MEMORY (
    SESSION_KEY,
    MESSAGE_ID,
    MESSAGE_SEQ,
    TURN_ID,
    ROLE,
    CHANNEL,
    CHAT_ID,
    SENDER_ID,
    INJECTED_EVENT,
    TOOL_CALL_ID,
    TOOL_NAME,
    LATENCY_MS,
    MESSAGE_TS,
    CONTENT_TEXT,
    MESSAGE_JSON
) values (
    :session_key,
    :message_id,
    :message_seq,
    :turn_id,
    :role,
    :channel,
    :chat_id,
    :sender_id,
    :injected_event,
    :tool_call_id,
    :tool_name,
    :latency_ms,
    :message_ts,
    :content_text,
    :message_json
)
"""


@dataclass(slots=True)
class OracleConfig:
    user: str
    password: str
    dsn: str


class OracleMemoryService:
    """Best-effort async writer for Oracle audit and memory tables."""

    def __init__(
        self,
        *,
        audit_enabled: bool = False,
        memory_enabled: bool = False,
        config_path: str | Path | None = None,
        batch_size: int = 25,
        max_queue_size: int = 1000,
    ) -> None:
        self.audit_enabled = bool(audit_enabled)
        self.memory_enabled = bool(memory_enabled)
        self.config_path = (
            Path(config_path).expanduser().resolve(strict=False)
            if config_path
            else None
        )
        self.batch_size = max(1, int(batch_size))
        self.max_queue_size = max(1, int(max_queue_size))
        self._queue: asyncio.Queue[tuple[str, dict[str, Any]]] | None = None
        self._worker: asyncio.Task[None] | None = None
        self._closing = False
        self._last_error_log_at = 0.0

    def publish_audit(self, payload: dict[str, Any]) -> None:
        if not self.audit_enabled:
            return
        normalized = dict(payload)
        for key in (
            "request_messages_json",
            "request_tools_json",
            "request_options_json",
            "response_json",
        ):
            normalized[key] = (
                None
                if normalized.get(key) is None
                else self._json_dumps(normalized.get(key))
            )
        self._enqueue("audit", normalized)

    def publish_memory(self, payload: dict[str, Any]) -> None:
        if not self.memory_enabled:
            return
        self._enqueue("memory", payload)

    def publish_session_message(
        self,
        session_key: str,
        message: dict[str, Any],
        *,
        channel: str | None = None,
        chat_id: str | None = None,
    ) -> None:
        effective_channel, effective_chat_id = self.split_session_key(session_key)
        payload = {
            "session_key": session_key,
            "message_id": str(message.get("message_id") or ""),
            "message_seq": self._safe_int(message.get("message_seq")),
            "turn_id": self._string_or_none(message.get("turn_id")),
            "role": self._string_or_none(message.get("role")),
            "channel": channel or effective_channel,
            "chat_id": chat_id or effective_chat_id,
            "sender_id": self._string_or_none(message.get("sender_id")),
            "injected_event": self._string_or_none(message.get("injected_event")),
            "tool_call_id": self._string_or_none(message.get("tool_call_id")),
            "tool_name": self._string_or_none(message.get("name")),
            "latency_ms": self._safe_int(message.get("latency_ms")),
            "message_ts": self._parse_timestamp(message.get("timestamp")),
            "content_text": self._extract_text(message.get("content")),
            "message_json": self._json_dumps(message),
        }
        if (
            not payload["message_id"]
            or payload["message_seq"] is None
            or not payload["role"]
        ):
            return
        self.publish_memory(payload)

    @staticmethod
    def split_session_key(session_key: str | None) -> tuple[str | None, str | None]:
        if not session_key:
            return None, None
        if ":" not in session_key:
            return session_key, None
        channel, chat_id = session_key.split(":", 1)
        return channel or None, chat_id or None

    def _enqueue(self, kind: str, payload: dict[str, Any]) -> None:
        enabled = self.audit_enabled or self.memory_enabled
        if not enabled or self.config_path is None or self._closing:
            return
        if not self._ensure_worker():
            return
        assert self._queue is not None
        try:
            self._queue.put_nowait((kind, payload))
        except asyncio.QueueFull:
            logger.warning(
                "Oracle memory queue full ({} items); dropping {} record",
                self.max_queue_size,
                kind,
            )

    def _ensure_worker(self) -> bool:
        if self._worker is not None and not self._worker.done():
            return True
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return False
        self._queue = asyncio.Queue(maxsize=self.max_queue_size)
        self._worker = loop.create_task(self._run_worker())
        return True

    async def close(self) -> None:
        self._closing = True
        worker = self._worker
        queue = self._queue
        if worker is None or queue is None:
            return
        try:
            queue.put_nowait(("__close__", {}))
        except asyncio.QueueFull:
            pass
        try:
            await asyncio.wait_for(worker, timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Timed out while closing Oracle memory writer")
            worker.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await worker

    async def _run_worker(self) -> None:
        assert self._queue is not None
        batch: list[tuple[str, dict[str, Any]]] = []
        while True:
            timeout_s = 0.25 if batch else None
            try:
                if timeout_s is None:
                    item = await self._queue.get()
                else:
                    item = await asyncio.wait_for(self._queue.get(), timeout=timeout_s)
            except asyncio.TimeoutError:
                item = None

            if item is None:
                if batch:
                    await self._flush_batch(batch)
                    batch = []
                continue

            kind, payload = item
            if kind == "__close__":
                if batch:
                    await self._flush_batch(batch)
                break

            batch.append((kind, payload))
            if len(batch) >= self.batch_size:
                await self._flush_batch(batch)
                batch = []

    async def _flush_batch(self, batch: list[tuple[str, dict[str, Any]]]) -> None:
        if not batch:
            return
        audit_rows = [payload for kind, payload in batch if kind == "audit"]
        memory_rows = [payload for kind, payload in batch if kind == "memory"]
        try:
            await asyncio.to_thread(self._flush_sync, audit_rows, memory_rows)
        except Exception as exc:
            self._rate_limited_log("Oracle memory flush failed", exc)

    def _flush_sync(
        self,
        audit_rows: list[dict[str, Any]],
        memory_rows: list[dict[str, Any]],
    ) -> None:
        config = self._load_config_sync()
        if config is None:
            return
        try:
            import oracledb
        except ModuleNotFoundError as exc:
            raise RuntimeError("python-oracledb is not installed") from exc

        with oracledb.connect(
            user=config.user,
            password=config.password,
            dsn=config.dsn,
        ) as connection:
            with connection.cursor() as cursor:
                if audit_rows:
                    cursor.executemany(_AUDIT_INSERT_SQL, audit_rows)
                if memory_rows:
                    cursor.executemany(_MEMORY_INSERT_SQL, memory_rows)
            connection.commit()

    def _load_config_sync(self) -> OracleConfig | None:
        path = self.config_path
        if path is None:
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise RuntimeError(f"Oracle config file not found: {path}")
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid Oracle config JSON: {exc}") from exc

        user = str(payload.get("user") or "").strip()
        password = str(payload.get("password") or "")
        dsn = str(payload.get("dsn") or "").strip()
        if not dsn:
            host = str(payload.get("host") or "").strip()
            port = payload.get("port") or 1521
            service_name = str(
                payload.get("service_name")
                or payload.get("serviceName")
                or ""
            ).strip()
            if host and service_name:
                dsn = f"{host}:{int(port)}/{service_name}"

        if not user or not password or not dsn:
            raise RuntimeError(
                "Oracle config must define user, password and dsn "
                "(or host/port/service_name)"
            )
        return OracleConfig(user=user, password=password, dsn=dsn)

    def _rate_limited_log(self, message: str, exc: Exception) -> None:
        now = time.monotonic()
        if now - self._last_error_log_at >= 30.0:
            self._last_error_log_at = now
            logger.exception("{}: {}", message, exc)
        else:
            logger.debug("{}: {}", message, exc)

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _string_or_none(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _parse_timestamp(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        text = str(value).strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None

    @classmethod
    def _extract_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            text = value.strip()
            return text or None
        if isinstance(value, list):
            parts: list[str] = []
            for block in value:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = str(block.get("text") or "").strip()
                    if text:
                        parts.append(text)
                elif block is not None:
                    text = str(block).strip()
                    if text:
                        parts.append(text)
            joined = "\n".join(parts).strip()
            return joined or None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _json_default(value: Any) -> Any:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.isoformat()
        return str(value)

    @classmethod
    def _json_dumps(cls, value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, default=cls._json_default)
