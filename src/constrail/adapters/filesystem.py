"""
Filesystem tool adapter.
"""

import shutil
from pathlib import Path

from .base import ToolAdapter, AdapterError
from ..models import ToolCall, ToolResult, ToolResultStatus


class FilesystemAdapter(ToolAdapter):
    """Adapter for filesystem operations (read, write, list, delete)."""

    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    @property
    def tool_name(self) -> str:
        return "filesystem"

    async def execute(self, call: ToolCall) -> ToolResult:
        operation = call.parameters.get("operation", "read")
        path = call.parameters.get("path")
        if not path:
            raise AdapterError("Missing 'path' parameter")

        target = self._resolve_path(path)

        try:
            if operation == "read":
                data = await self._read(target)
            elif operation == "write":
                content = call.parameters.get("content")
                if content is None:
                    raise AdapterError("Missing 'content' parameter for write")
                data = await self._write(target, content)
            elif operation == "list":
                data = await self._list(target)
            elif operation == "delete":
                data = await self._delete(target)
            else:
                raise AdapterError(f"Unknown operation '{operation}'")

            return ToolResult(success=True, data=data, status=ToolResultStatus.SUCCESS)
        except AdapterError as e:
            return ToolResult(success=False, error=str(e), data=None, status=ToolResultStatus.ERROR)
        except Exception as e:
            return ToolResult(success=False, error=f"Filesystem operation failed: {e}", data=None, status=ToolResultStatus.ERROR)

    def _resolve_path(self, path: str) -> Path:
        joined = (self.base_path / path).resolve()
        try:
            joined.relative_to(self.base_path)
        except ValueError:
            raise AdapterError(f"Path '{path}' attempts to escape sandbox")
        return joined

    async def _read(self, path: Path) -> dict:
        if not path.exists():
            raise AdapterError(f"File not found: {path}")
        if not path.is_file():
            raise AdapterError(f"Not a file: {path}")
        content = path.read_text(encoding="utf-8")
        return {"content": content, "path": str(path)}

    async def _write(self, path: Path, content: str) -> dict:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"path": str(path), "bytes_written": len(content)}

    async def _list(self, path: Path) -> dict:
        if not path.exists():
            raise AdapterError(f"Directory not found: {path}")
        if not path.is_dir():
            raise AdapterError(f"Not a directory: {path}")
        items = []
        for entry in path.iterdir():
            items.append(
                {
                    "name": entry.name,
                    "type": "file" if entry.is_file() else "directory",
                    "size": entry.stat().st_size if entry.is_file() else 0,
                }
            )
        return {"path": str(path), "items": items}

    async def _delete(self, path: Path) -> dict:
        if not path.exists():
            raise AdapterError(f"Path does not exist: {path}")
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
        return {"path": str(path)}
