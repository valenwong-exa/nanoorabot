"""Windows OpenSSH tool for executing Linux SSH and SCP operations."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool


class WinSshLinuxTool(Tool):
    """Run ssh/scp from Windows OpenSSH against Linux hosts."""
    _scopes = {"core", "subagent"}

    def __init__(self, timeout: int = 120, max_output_chars: int = 20000):
        self.timeout = timeout
        self.max_output_chars = max_output_chars

    @property
    def name(self) -> str:
        return "win_ssh_linux"

    @property
    def description(self) -> str:
        return (
            "Use Windows OpenSSH to run Linux ssh commands and scp upload/download via private key. "
            "OpenSSH location is read from OPENSSH_HOME. "
            "Important: when running multiple remote Linux commands from Windows CMD through ssh, "
            "prefer wrapping them with bash -lc, for example: "
            "ssh -i oracle26ee_101.key oracle@192.168.56.101 bash -lc \"hostname; date; uptime\". "
            "On Linux-native shells, bash -lc is usually not required just to run multiple commands."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["ssh_exec", "scp_upload", "scp_download"],
                    "description": "Operation mode: run ssh command, upload file, or download file",
                },
                "host": {
                    "type": "string",
                    "description": "Linux host IP or DNS",
                },
                "username": {
                    "type": "string",
                    "description": "Remote Linux username",
                },
                "keyName": {
                    "type": "string",
                    "description": "Private key filename under OPENSSH_HOME, e.g. css2.key",
                },
                "command": {
                    "type": "string",
                    "description": (
                        "Command text for ssh_exec mode. Important: when this tool is invoked from Windows CMD "
                        "and you need to run multiple commands on the remote Linux host, prefer using "
                        "bash -lc, for example: bash -lc \"hostname; date; uptime\". "
                        "On Linux-native shells, multiple commands usually do not require bash -lc."
                    ),
                },
                "localPath": {
                    "type": "string",
                    "description": "Local file path for scp_upload/scp_download",
                },
                "remotePath": {
                    "type": "string",
                    "description": "Remote file path for scp_upload/scp_download",
                },
                "port": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 65535,
                    "description": "SSH port, default 22",
                },
                "strictHostKeyChecking": {
                    "type": "boolean",
                    "description": "Whether to enforce host key checking, default false",
                },
                "timeout": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Timeout in seconds",
                },
            },
            "required": ["mode", "host", "username", "keyName"],
        }

    async def execute(
        self,
        mode: str,
        host: str,
        username: str,
        key_name: str | None = None,
        command: str | None = None,
        local_path: str | None = None,
        remote_path: str | None = None,
        port: int = 22,
        strict_host_key_checking: bool = False,
        timeout: int | None = None,
        **kwargs: Any,
    ) -> str:
        key_name = key_name or kwargs.get("keyName")
        local_path = local_path or kwargs.get("localPath")
        remote_path = remote_path or kwargs.get("remotePath")
        strict_host_key_checking = kwargs.get("strictHostKeyChecking", strict_host_key_checking)

        if key_name is None:
            return "Error: Missing required parameter 'keyName'."

        openssh_home = os.environ.get("OPENSSH_HOME", "").strip()
        if not openssh_home:
            # Fallback to default path if OPENSSH_HOME is not set
            default_path = r"E:\OpenSSH-Win64"
            if os.path.exists(default_path):
                openssh_home = default_path
            else:
                return (
                    "Error: OPENSSH_HOME is not configured and default path "
                    f"({default_path}) does not exist. "
                    "Please ask the user to provide OpenSSH absolute path and set OPENSSH_HOME."
                )

        openssh_dir = Path(openssh_home)
        if not openssh_dir.exists():
            return (
                f"Error: OPENSSH_HOME path does not exist: {openssh_home}. "
                "Please ask the user to provide a valid OpenSSH path."
            )

        ssh_executable = self._resolve_executable(openssh_dir, "ssh")
        scp_executable = self._resolve_executable(openssh_dir, "scp")
        if mode == "ssh_exec" and ssh_executable is None:
            return (
                "Error: ssh executable not found under OPENSSH_HOME. "
                "Please ask the user to provide a valid OpenSSH package."
            )
        if mode in {"scp_upload", "scp_download"} and scp_executable is None:
            return (
                "Error: scp executable not found under OPENSSH_HOME. "
                "Please ask the user to provide a valid OpenSSH package."
            )

        key_path = openssh_dir / key_name
        if not key_path.exists():
            return (
                f"Error: private key not found: {key_path}. "
                "Please ask the user to provide the correct key filename in OPENSSH_HOME."
            )

        target = f"{username}@{host}"
        run_timeout = timeout or self.timeout
        options = self._build_ssh_options(strict_host_key_checking)

        if mode == "ssh_exec":
            if not command:
                return "Error: 'command' is required for mode 'ssh_exec'."
            args = [
                str(ssh_executable),
                "-i",
                str(key_path),
                "-p",
                str(port),
                *options,
                target,
                command,
            ]
        elif mode == "scp_upload":
            if not local_path or not remote_path:
                return "Error: 'localPath' and 'remotePath' are required for mode 'scp_upload'."
            if not Path(local_path).exists():
                return f"Error: localPath does not exist: {local_path}"
            args = [
                str(scp_executable),
                "-i",
                str(key_path),
                "-P",
                str(port),
                *options,
                str(local_path),
                f"{target}:{remote_path}",
            ]
        elif mode == "scp_download":
            if not local_path or not remote_path:
                return "Error: 'localPath' and 'remotePath' are required for mode 'scp_download'."
            args = [
                str(scp_executable),
                "-i",
                str(key_path),
                "-P",
                str(port),
                *options,
                f"{target}:{remote_path}",
                str(local_path),
            ]
        else:
            return "Error: Unsupported mode. Use one of: ssh_exec, scp_upload, scp_download."

        try:
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except Exception as e:
            return f"Error: Failed to start OpenSSH command: {e}"

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=run_timeout)
        except asyncio.TimeoutError:
            process.kill()
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                pass
            return f"Error: OpenSSH command timed out after {run_timeout} seconds"

        out_text = stdout.decode("utf-8", errors="replace").strip()
        err_text = stderr.decode("utf-8", errors="replace").strip()

        parts: list[str] = []
        if out_text:
            parts.append(out_text)
        if err_text:
            parts.append(f"STDERR:\n{err_text}")
        if process.returncode not in (0, None):
            parts.append(f"Exit code: {process.returncode}")

        result = "\n\n".join(parts) if parts else "(no output)"
        if len(result) > self.max_output_chars:
            extra = len(result) - self.max_output_chars
            result = result[: self.max_output_chars] + f"\n... (truncated, {extra} more chars)"
        return result

    @staticmethod
    def _resolve_executable(openssh_dir: Path, binary_name: str) -> Path | None:
        for filename in (f"{binary_name}.exe", binary_name):
            candidate = openssh_dir / filename
            if candidate.exists():
                return candidate
        return None

    @staticmethod
    def _build_ssh_options(strict_host_key_checking: bool) -> list[str]:
        if strict_host_key_checking:
            return ["-o", "BatchMode=yes"]
        return [
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=NUL",
        ]
