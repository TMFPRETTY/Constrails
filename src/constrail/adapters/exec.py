"""
Exec adapter for Constrail.
Handles execution of shell commands with sandbox-aware fallback behavior.
"""

import asyncio
import subprocess

from ..models import ToolCall, ToolResult, ToolResultStatus
from .base import ToolAdapter, AdapterError


class ExecAdapter(ToolAdapter):
    """Adapter for executing shell commands."""

    def __init__(self, sandbox_executor=None):
        self.sandbox_executor = sandbox_executor

    @property
    def tool_name(self) -> str:
        return "exec"

    async def execute(self, call: ToolCall) -> ToolResult:
        try:
            params = call.parameters or {}
            command = params.get("command", "")

            if not command:
                raise AdapterError("Missing required parameter 'command'")

            if self.sandbox_executor is not None:
                result = await self.sandbox_executor.execute(command)
                exit_code = result.get("exit_code")
                success = exit_code == 0
                return ToolResult(
                    success=success,
                    data=result,
                    error=None if success else f"Command failed with exit code {exit_code}",
                    status=ToolResultStatus.SUCCESS if success else ToolResultStatus.ERROR,
                )

            timeout = params.get("timeout")
            cwd = params.get("cwd")
            env = params.get("env")

            process = await asyncio.create_subprocess_shell(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                cwd=cwd,
                env=env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout if timeout else None,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return ToolResult(
                    success=False,
                    data={
                        "exit_code": None,
                        "stdout": "",
                        "stderr": "",
                        "timeout": True,
                    },
                    error=f"Command timed out after {timeout} seconds",
                    status=ToolResultStatus.TIMEOUT,
                )

            exit_code = process.returncode
            result_data = {
                "exit_code": exit_code,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "timeout": False,
            }
            success = exit_code == 0
            return ToolResult(
                success=success,
                data=result_data,
                error=None if success else f"Command failed with exit code {exit_code}",
                status=ToolResultStatus.SUCCESS if success else ToolResultStatus.ERROR,
            )

        except AdapterError as e:
            return ToolResult(success=False, data={}, error=str(e), status=ToolResultStatus.ERROR)
        except Exception as e:
            return ToolResult(success=False, data={}, error=f"Unexpected error: {str(e)}", status=ToolResultStatus.ERROR)
