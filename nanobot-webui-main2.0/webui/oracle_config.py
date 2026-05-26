"""Oracle DB config persistence and connection testing helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class OracleConnectionConfig:
    user: str
    password: str
    host: str
    port: int
    service_name: str
    updated_at: str | None = None

    @property
    def dsn(self) -> str:
        return f"{self.host}:{self.port}/{self.service_name}"

    @property
    def connect_string(self) -> str:
        return f"{self.user}/{self.password}@{self.dsn}"

    def to_storage_dict(self) -> dict[str, Any]:
        return {
            "driver": "python-oracledb",
            "user": self.user,
            "password": self.password,
            "host": self.host,
            "port": self.port,
            "service_name": self.service_name,
            "dsn": self.dsn,
            "connect_string": self.connect_string,
            "updated_at": self.updated_at,
        }


DEFAULT_ORACLE_CONFIG = OracleConnectionConfig(
    user="valen",
    password="oracle",
    host="192.168.56.101",
    port=1521,
    service_name="aidemo_pdb",
)


class OracleConfigService:
    """Read, write and test Oracle connection settings."""

    def __init__(self, config_path: Path | None) -> None:
        self.config_path = config_path

    def ensure_available(self) -> Path:
        if self.config_path is None:
            raise RuntimeError("Oracle config path is not configured")
        return self.config_path

    def load(self) -> OracleConnectionConfig:
        path = self.ensure_available()
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or not path.read_text(encoding="utf-8").strip():
            config = self._with_timestamp(DEFAULT_ORACLE_CONFIG)
            self._write(path, config)
            return config

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid Oracle config JSON: {exc}") from exc

        return self._from_payload(payload)

    def save(self, payload: dict[str, Any]) -> OracleConnectionConfig:
        path = self.ensure_available()
        path.parent.mkdir(parents=True, exist_ok=True)
        config = self._with_timestamp(self._from_payload(payload))
        self._write(path, config)
        return config

    def test_connection(self, payload: dict[str, Any]) -> dict[str, Any]:
        config = self._from_payload(payload)
        try:
            import oracledb
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "python-oracledb is not installed. Install the 'oracledb' package first."
            ) from exc

        with oracledb.connect(
            user=config.user,
            password=config.password,
            dsn=config.dsn,
        ) as connection:
            metadata = self._collect_database_metadata(connection)
            return {
                "success": True,
                "message": "Oracle connection successful.",
                "dsn": config.dsn,
                "server_version": getattr(connection, "version", None),
                "character_set": metadata.get("character_set"),
                "is_rac": metadata.get("is_rac"),
                "is_multitenant": metadata.get("is_multitenant"),
            }

    def _collect_database_metadata(self, connection: Any) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "character_set": None,
            "is_rac": None,
            "is_multitenant": None,
        }

        with connection.cursor() as cursor:
            metadata["character_set"] = self._query_scalar(
                cursor,
                """
                select value
                from nls_database_parameters
                where parameter = 'NLS_CHARACTERSET'
                """,
            )

            rac_value = self._query_scalar(
                cursor,
                """
                select case when count(*) > 1 then 'TRUE' else 'FALSE' end
                from gv$instance
                """,
            )
            metadata["is_rac"] = self._parse_bool(rac_value)

            multitenant_value = self._query_scalar(
                cursor,
                """
                select cdb
                from v$database
                """,
            )
            metadata["is_multitenant"] = self._parse_bool(multitenant_value)

        return metadata

    def _query_scalar(self, cursor: Any, sql: str) -> Any:
        try:
            cursor.execute(sql)
            row = cursor.fetchone()
        except Exception:
            return None
        if not row:
            return None
        return row[0]

    def _parse_bool(self, value: Any) -> bool | None:
        if value is None:
            return None
        normalized = str(value).strip().upper()
        if normalized in {"TRUE", "YES", "Y", "1"}:
            return True
        if normalized in {"FALSE", "NO", "N", "0"}:
            return False
        return None

    def _from_payload(self, payload: dict[str, Any]) -> OracleConnectionConfig:
        user = str(payload.get("user", DEFAULT_ORACLE_CONFIG.user)).strip()
        password = str(payload.get("password", DEFAULT_ORACLE_CONFIG.password))
        host = str(payload.get("host", DEFAULT_ORACLE_CONFIG.host)).strip()
        raw_port = payload.get("port", DEFAULT_ORACLE_CONFIG.port)
        service_name = str(
            payload.get("service_name")
            or payload.get("serviceName")
            or DEFAULT_ORACLE_CONFIG.service_name
        ).strip()
        updated_at = payload.get("updated_at") or payload.get("updatedAt")

        if not user:
            raise RuntimeError("Oracle user is required")
        if not password:
            raise RuntimeError("Oracle password is required")
        if not host:
            raise RuntimeError("Oracle host is required")
        if not service_name:
            raise RuntimeError("Oracle service name is required")

        try:
            port = int(raw_port)
        except (TypeError, ValueError) as exc:
            raise RuntimeError("Oracle port must be a valid integer") from exc

        return OracleConnectionConfig(
            user=user,
            password=password,
            host=host,
            port=port,
            service_name=service_name,
            updated_at=str(updated_at) if updated_at else None,
        )

    def _with_timestamp(self, config: OracleConnectionConfig) -> OracleConnectionConfig:
        return OracleConnectionConfig(
            user=config.user,
            password=config.password,
            host=config.host,
            port=config.port,
            service_name=config.service_name,
            updated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )

    def _write(self, path: Path, config: OracleConnectionConfig) -> None:
        path.write_text(
            json.dumps(config.to_storage_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
