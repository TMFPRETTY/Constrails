"""
Exec adapter for Constrail.
Handles execution of shell commands with sandbox-aware behavior.
"""

from ..models import ToolCall, ToolResult, ToolResultStatus
from .base import AdapterError, ToolAdapter


class ExecAdapter(ToolAdapter):
    """Adapter for executing shell commands."""

    def __init__(self, sandbox_executor=None, allow_unsandboxed: bool = False):
        self.sandbox_executor = sandbox_executor
        self.allow_unsandboxed = allow_unsandboxed

    @property
    def tool_name(self) -> str:
        return "exec"

    async def execute(self, call: ToolCall) -> ToolResult:
        try:
            params = call.parameters or {}
            command = params.get("command", "")
            cwd = params.get("cwd")
            env = params.get("env")
            timeout = params.get("timeout")

            if not command:
                raise AdapterError("Missing required parameter 'command'")

            if self.sandbox_executor is not None:
                result = await self.sandbox_executor.execute(
                    command,
                    cwd=cwd,
                    env=env,
                    timeout=timeout,
                )
                success = result.exit_code == 0 and not result.timeout
                return ToolResult(
                    success=success,
                    data=result.to_dict(),
                    error=None if success else (
                        f"Command timed out in sandbox {result.sandbox_id}"
                        if result.timeout
                        else f"Command failed with exit code {result.exit_code} in sandbox {result.sandbox_id}"
                    ),
                    metadata={
                        'sandbox_id': result.sandbox_id,
                        'sandbox_executor': result.executor,
                    },
                    status=ToolResultStatus.SUCCESS if success else (ToolResultStatus.TIMEOUT if result.timeout else ToolResultStatus.ERROR),
                )

            if not self.allow_unsandboxed:
                return ToolResult(
                    success=False,
                    data={"sandbox_required": True},
                    error="Unsandboxed exec is disabled; configure a sandbox executor or explicitly opt into unsandboxed execution",
                    status=ToolResultStatus.BLOCKED,
                )

            raise AdapterError("Unsandboxed execution path is not enabled in this build")

        except AdapterError as e:
            return ToolResult(success=False, data={}, error=str(e), status=ToolResultStatus.ERROR)
        except Exception as e:
            return ToolResult(success=False, data={}, error=f"Unexpected error: {str(e)}", status=ToolResultStatus.ERROR)
