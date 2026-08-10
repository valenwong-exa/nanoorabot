"""webui.patches — monkey-patches applied to nanobot at startup.

Each sub-module targets one concern and exposes a single ``apply()`` function.
Call ``apply_all()`` once at process start (done by ``webui.__main__``).

Patch inventory
───────────────
channels    [Channel]     Relax access-control managed by the WebUI.
mcp_dynamic [MCPDynamic]  Per-server MCP stacks for dynamic load/unload.
oracle_persistence [OraclePersistence] Restore Oracle audit/memory on main3.
session     [Session]     Filter WebUI-only session roles from LLM history.
provider    [Provider]    Auto-fall-back to OpenAI /v1/responses when needed.
skills      [Skills]      Honour .disabled_skills.json from the WebUI toggle.
subagent    [SubAgent]    Push tool-call progress to WebUI / external channels.
tool_approval [ToolApproval] Restore legacy warn/approve/cancel flow on main3.
"""

from __future__ import annotations

from webui.patches import channels, config, mcp_dynamic, oracle_persistence, provider, session, skills, subagent, tool_approval


def apply_all() -> None:
    """Apply every patch in dependency order."""
    config.apply()       # must run early to intercept Config methods
    mcp_dynamic.apply()  # must run before agent is created
    oracle_persistence.apply()
    tool_approval.apply()
    channels.apply()
    session.apply()
    provider.apply()
    skills.apply()
    subagent.apply()
