from webui.utils.channel_compat import (
    classify_session_type,
    get_webui_user_scope,
    is_webui_session_key,
    is_webui_transport_channel,
    normalize_transport_channel,
    resolve_webui_callback_key,
)


def test_normalize_transport_channel_maps_legacy_web_to_websocket() -> None:
    assert normalize_transport_channel("web") == "websocket"
    assert normalize_transport_channel("websocket") == "websocket"
    assert normalize_transport_channel("cli") == "cli"
    assert normalize_transport_channel(None) is None


def test_is_webui_transport_channel_accepts_legacy_and_native_values() -> None:
    assert is_webui_transport_channel("web") is True
    assert is_webui_transport_channel("websocket") is True
    assert is_webui_transport_channel("cli") is False


def test_is_webui_session_key_uses_web_namespace_not_transport_name() -> None:
    assert is_webui_session_key("web:42:abcd1234") is True
    assert is_webui_session_key("websocket:42:abcd1234") is False
    assert is_webui_session_key("cli:direct") is False


def test_get_webui_user_scope_extracts_stable_owner_scope() -> None:
    assert get_webui_user_scope("web:42:abcd1234") == "web:42"
    assert get_webui_user_scope("web:42") is None
    assert get_webui_user_scope("cli:direct") is None


def test_resolve_webui_callback_key_preserves_legacy_and_native_shapes() -> None:
    assert resolve_webui_callback_key("websocket", "web:42:abcd1234") == "websocket:web:42:abcd1234"
    assert resolve_webui_callback_key("web", "web:42:abcd1234") == "web:42"
    assert resolve_webui_callback_key("web", "legacy-room") == "web:legacy-room"


def test_classify_session_type_reports_browser_sessions_as_websocket() -> None:
    assert classify_session_type("web:42:abcd1234", "web") == "websocket"
    assert classify_session_type("cli:direct", "cli") == "cli"
    assert classify_session_type("", "web") == "websocket"
