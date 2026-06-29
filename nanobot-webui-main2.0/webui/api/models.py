"""Pydantic request / response models for the webui API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    id: str
    username: str
    role: str
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo


class ChangePasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=6)


# ---------------------------------------------------------------------------
# Users (admin)
# ---------------------------------------------------------------------------


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=6)
    role: Literal["admin", "user"] = "user"


# ---------------------------------------------------------------------------
# Agent Settings / Config
# ---------------------------------------------------------------------------


class AgentSettingsResponse(BaseModel):
    model: str
    provider: str
    max_tokens: int
    temperature: float
    max_iterations: int
    context_window_tokens: int
    reasoning_effort: str | None
    workspace: str
    restrict_to_workspace: bool
    exec_timeout: int
    path_append: str
    web_search_api_key: str  # masked
    web_proxy: str | None
    send_progress: bool
    send_tool_hints: bool


class AgentSettingsRequest(BaseModel):
    model: str | None = None
    provider: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    max_iterations: int | None = None
    context_window_tokens: int | None = None
    reasoning_effort: str | None = None
    workspace: str | None = None
    restrict_to_workspace: bool | None = None
    exec_timeout: int | None = None
    path_append: str | None = None
    web_search_api_key: str | None = None
    web_proxy: str | None = None
    send_progress: bool | None = None
    send_tool_hints: bool | None = None


class HeartbeatConfigModel(BaseModel):
    enabled: bool
    interval_s: int


class GatewayConfigResponse(BaseModel):
    host: str
    port: int
    heartbeat: HeartbeatConfigModel


class GatewayConfigRequest(BaseModel):
    host: str | None = None
    port: int | None = None
    heartbeat_enabled: bool | None = None
    heartbeat_interval_s: int | None = None


# ---------------------------------------------------------------------------
# Oracle DB Config
# ---------------------------------------------------------------------------


class OracleConfigResponse(BaseModel):
    user: str
    password: str
    host: str
    port: int
    serviceName: str
    dsn: str
    connectString: str
    configPath: str | None = None
    updatedAt: str | None = None


class OracleConfigRequest(BaseModel):
    user: str
    password: str
    host: str
    port: int
    serviceName: str


class OracleConnectionTestResponse(BaseModel):
    success: bool
    message: str
    dsn: str
    serverVersion: str | None = None
    characterSet: str | None = None
    isRac: bool | None = None
    isMultitenant: bool | None = None


class ToolPolicyRuleModel(BaseModel):
    command: str = Field(..., min_length=1)
    matchType: Literal["literal", "regex"] = "literal"
    regexFlags: str = ""
    category: str = Field(..., min_length=1)
    severity: str = Field(..., min_length=1)
    mode: str = Field(..., min_length=1)
    scope: str = Field(..., min_length=1)
    note: str = ""


class ToolPolicyResponse(BaseModel):
    version: int
    name: str
    source: str
    description: str
    rules: list[ToolPolicyRuleModel]
    configPath: str | None = None
    updatedAt: str | None = None


class ToolPolicyRequest(BaseModel):
    version: int = 1
    name: str = Field(default="dangerous_tool_policy", min_length=1)
    source: str = Field(default="webui-defense-page", min_length=1)
    description: str = ""
    rules: list[ToolPolicyRuleModel] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Knowledge Base / Vector Search
# ---------------------------------------------------------------------------


class KnowledgeBaseHealthResponse(BaseModel):
    status: str
    baseUrl: str


class KnowledgeBaseUploadResponse(BaseModel):
    documentName: str
    documentType: str
    docId: int | None = None
    inserted: bool
    parsedChunkCount: int
    insertedChunkCount: int
    fullTextLength: int
    fullTextPreview: str | None = None


class KnowledgeBaseSearchRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    topK: int = Field(default=5, ge=1, le=50)
    rerankerScore: float = Field(default=0.3, ge=0.0, le=1.0)
    engine: Literal["qwen", "bge"] = "qwen"
    documentType: Literal["pdf", "txt"] | None = None
    device: Literal["auto", "cuda", "cpu"] = "auto"


class KnowledgeBaseSearchResult(BaseModel):
    title: str
    score: float


class KnowledgeBaseDocumentListItem(BaseModel):
    docId: int
    documentName: str
    documentType: str
    sourceFile: str | None = None
    createdAt: str | None = None
    chunkCount: int


class KnowledgeBaseDocumentListResponse(BaseModel):
    items: list[KnowledgeBaseDocumentListItem]
    total: int
    page: int
    pageSize: int


class KnowledgeBaseDeleteResponse(BaseModel):
    success: bool
    docId: int
    deletedDocumentCount: int
    deletedChunkCount: int


# ---------------------------------------------------------------------------
# Host Inventory Refresh
# ---------------------------------------------------------------------------


class HostInventoryRefreshConfigResponse(BaseModel):
    enabled: bool
    intervalMinutes: int
    isRunning: bool
    lastRunAt: str | None = None
    lastSuccessAt: str | None = None
    lastError: str | None = None


class HostInventoryRefreshConfigRequest(BaseModel):
    enabled: bool | None = None
    intervalMinutes: int | None = Field(default=None, ge=1, le=1440)


# ---------------------------------------------------------------------------
# S3 / OSS Storage
# ---------------------------------------------------------------------------


class S3ConfigResponse(BaseModel):
    enabled: bool
    endpoint_url: str
    access_key_id: str
    secret_access_key: str  # masked
    bucket: str
    region: str
    public_base_url: str


class S3ConfigRequest(BaseModel):
    enabled: bool | None = None
    endpoint_url: str | None = None
    access_key_id: str | None = None
    secret_access_key: str | None = None  # empty string = keep current
    bucket: str | None = None
    region: str | None = None
    public_base_url: str | None = None


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------


class ProviderInfo(BaseModel):
    name: str
    api_key_masked: str  # empty string → not configured, "••••{last4}" → configured
    api_base: str | None
    extra_headers: dict[str, str] | None = None
    has_key: bool
    # [AI:START] tool=copilot date=2026-03-12 author=chenweikang
    models: list[str] = Field(default_factory=list)  # User-defined model list
    # [AI:END]
    is_custom: bool = False  # True if it's dynamically added via webui_config

class CreateProviderRequest(BaseModel):
    name: str
    api_key: str | None = None
    api_base: str | None = None
    extra_headers: dict[str, str] | None = None
    models: list[str] | None = None

class UpdateProviderRequest(BaseModel):
    api_key: str | None = None  # empty string clears the key
    api_base: str | None = None
    extra_headers: dict[str, str] | None = None
    # [AI:START] tool=copilot date=2026-03-12 author=chenweikang
    models: list[str] | None = None  # None = no change, [] = clear list
    # [AI:END]


# ---------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------


class ChannelStatus(BaseModel):
    name: str
    enabled: bool
    running: bool
    config: dict[str, Any]  # full channel config (API keys masked by route handler)


class UpdateChannelRequest(BaseModel):
    enabled: bool | None = None          # from the toggle Switch
    config: dict[str, Any] = Field(default_factory=dict)  # partial config fields


# ---------------------------------------------------------------------------
# MCP Servers
# ---------------------------------------------------------------------------


class MCPServerInfo(BaseModel):
    name: str
    type: str | None
    command: str
    args: list[str]
    env: dict[str, str]
    url: str
    headers: dict[str, str]
    timeout: int
    enabled: bool = True


class MCPServerRequest(BaseModel):
    type: str | None = None
    command: str = ""
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    url: str = ""
    headers: dict[str, str] = Field(default_factory=dict)
    timeout: int = 30
    enabled: bool = True


class MCPServerEnabledUpdate(BaseModel):
    enabled: bool


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------


class SkillInfo(BaseModel):
    name: str
    source: Literal["builtin", "workspace"]
    path: str
    description: str = ""
    available: bool
    enabled: bool = True
    unavailable_reason: str | None = None


class SkillContent(BaseModel):
    name: str
    source: str
    content: str


class CreateSkillRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    content: str


class UpdateSkillRequest(BaseModel):
    content: str


# ---------------------------------------------------------------------------
# Cron Jobs
# ---------------------------------------------------------------------------


class CronScheduleModel(BaseModel):
    kind: Literal["at", "every", "cron"]
    at_ms: int | None = None
    every_ms: int | None = None
    expr: str | None = None
    tz: str | None = None


class CronPayloadModel(BaseModel):
    message: str
    deliver: bool = False
    channel: str | None = None
    to: str | None = None


class CronStateModel(BaseModel):
    next_run_at_ms: int | None
    last_run_at_ms: int | None
    last_status: str | None
    last_error: str | None


class CronJobInfo(BaseModel):
    id: str
    name: str
    enabled: bool
    schedule: CronScheduleModel
    payload: CronPayloadModel
    state: CronStateModel
    delete_after_run: bool
    created_at_ms: int
    updated_at_ms: int


class CronJobRequest(BaseModel):
    name: str = Field(..., min_length=1)
    enabled: bool = True
    schedule: CronScheduleModel
    payload: CronPayloadModel
    delete_after_run: bool = False


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


class SessionInfo(BaseModel):
    key: str
    created_at: str | None
    updated_at: str | None
    last_message: str | None = None  # last user/assistant message preview


class MessageInfo(BaseModel):
    role: str
    content: str | list | None
    timestamp: str | None = None
    tool_calls: list | None = None
    tool_call_id: str | None = None
    name: str | None = None


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


class DashboardStats(BaseModel):
    model: str
    enabled_channels: int
    total_channels: int
    sessions_today: int
    channel_statuses: list[ChannelStatus]
    recent_sessions: list[SessionInfo]
