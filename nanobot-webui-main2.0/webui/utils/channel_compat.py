"""Compatibility helpers for legacy WebUI channel/session semantics."""

from __future__ import annotations


WEBUI_TRANSPORT_CHANNELS = frozenset({"websocket", "web"})
WEBUI_SESSION_PREFIX = "web:"
WEBSOCKET_TRANSPORT_CHANNEL = "websocket"


def is_webui_transport_channel(channel: str | None) -> bool:
    """Return True when *channel* targets the browser-backed WebUI transport."""
    return (channel or "") in WEBUI_TRANSPORT_CHANNELS


def normalize_transport_channel(channel: str | None) -> str | None:
    """Canonicalize legacy transport names while preserving empty values."""
    if channel == "web":
        return WEBSOCKET_TRANSPORT_CHANNEL
    return channel


def is_webui_session_key(key: str | None) -> bool:
    """Return True when *key* belongs to a WebUI-owned chat session."""
    return bool(key) and key.startswith(WEBUI_SESSION_PREFIX)


def get_webui_user_scope(key: str | None) -> str | None:
    """Return the stable ``web:<user_id>`` scope for a WebUI session key."""
    if not is_webui_session_key(key):
        return None
    raw = str(key)
    if raw.count(":") < 2:
        return None
    user_id = raw.split(":", 2)[1]
    return f"{WEBUI_SESSION_PREFIX}{user_id}"


def resolve_webui_callback_key(channel: str | None, chat_id: str | None) -> str:
    """Build the callback-registry key while preserving legacy ``web`` semantics."""
    raw_channel = channel or ""
    raw_chat_id = chat_id or ""
    if raw_channel == "web":
        legacy_scope = get_webui_user_scope(raw_chat_id)
        if legacy_scope:
            return legacy_scope
    return f"{raw_channel}:{raw_chat_id}"


def classify_session_type(session_key: str | None, fallback: str | None = None) -> str:
    """Return a user-facing session type label from a session key or file prefix."""
    if is_webui_session_key(session_key):
        return WEBSOCKET_TRANSPORT_CHANNEL
    normalized = normalize_transport_channel(fallback)
    return normalized or (fallback or "unknown")
