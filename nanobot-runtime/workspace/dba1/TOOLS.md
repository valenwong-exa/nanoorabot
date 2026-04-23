# Tool Usage Notes

Tool signatures are provided automatically via function calling.
This file documents non-obvious constraints and usage patterns.

## exec — Safety Limits

- Commands have a configurable timeout (default 60s)
- Dangerous commands are blocked (rm -rf, format, dd, shutdown, etc.)
- Output is truncated at 10,000 characters
- `restrictToWorkspace` config can limit file access to the workspace

## cron — Scheduled Reminders

- Please refer to cron skill for usage.

## Windows — Open Local HTML Files

- In `PowerShell`, prefer:
  - `Start-Process "E:\nanobot-main\dba1\east_ssc_trend.html"`
- In `PowerShell`, do not prefer CMD-style:
  - `start "" "E:\nanobot-main\dba1\east_ssc_trend.html"`
- Reason:
  - `start` is a CMD habit and is less predictable in PowerShell
  - `Start-Process` is the more stable choice for AI/agent execution in PowerShell
- In `CMD`, prefer:
  - `start "" "E:\nanobot-main\dba1\east_ssc_trend.html"`
  - or `explorer "E:\nanobot-main\dba1\east_ssc_trend.html"`
- In `CMD`, `start` must keep the empty title argument `""`
- When typing directly in `CMD`, do not add extra backslash escaping
- When paths pass through JSON, Python, or program string building, escape according to that layer so the final command does not become malformed like `\\`
- If the shell is uncertain on Windows, prefer:
  - `explorer "full file path"`
