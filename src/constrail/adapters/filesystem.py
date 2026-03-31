"""
Filesystem tool adapter.
"""

import os
import shutil
from pathlib import Path
from typing import Any, Dict
from .base import ToolAdapter, AdapterError
from ..models import ToolCall


class FilesystemAdapter(ToolAdapter):
    """Adapter for filesystem operations (read, write, list)."""

    def __init__(self, base_path: str = "/workspace"):
        self.base_path = Path(base_path).resolve()
        # Ensure base_path exists and is a directory
        self.base_path.mkdir(parents=True, exist_ok=True)

    @property
    def tool_name(self) -> str:
        return "filesystem"

    async def execute(self, call: ToolCall) -> Dict[str, Any]:
        operation = call.parameters.get("operation", "read")
        path = call.parameters.get("path")
        if not path:
            raise AdapterError("Missing 'path' parameter")

        # Sanitize path: ensure it's within base_path
        target = self._resolve_path(path)

        if operation == "read":
            return await self._read(target)
        elif operation == "write":
            content = call.parameters.get("content")
            if content is None:
                raise AdapterError("Missing 'content' parameter for write")
            return await self._write(target, content)
        elif operation == "list":
            return await self._list(target)
        elif operation == "delete":
            return await self._delete(target)
        else:
            raise AdapterError(f"Unknown operation '{operation}'")

    def _resolve_path(self, path: str) -> Path:
        """Resolve a relative path, ensuring it stays within base_path."""
        # Normalize and join
        joined = (self.base_path / path).resolve()
        # Ensure the joined path is still under base_path
        try:
            joined.relative_to(self.base_path)
        except ValueError:
            raise AdapterError(f"Path '{path}' attempts to escape sandbox")
        return joined

    async def _read(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            raise AdapterError(f"File not found: {path}")
        if not path.is_file():
            raise AdapterError(f"Not a file: {path}")
        try:
            content = path.read_text(encoding="utf-8")
            return {"success": True, "content": content, "path": str(path)}
        except Exception as e:
            raise AdapterError(f"Read failed: {e}")

    async def _write(self, path: Path, content: str) -> Dict[str, Any]:
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text(content, encoding="utf-8")
            return {"success": True, "path": str(path), "bytes_written": len(content)}
        except Exception as e:
            raise AdapterError(f"Write failed: {e}")

    async def _list(self, path: Path) -> Dict[str, Any]:
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
        return {"success": True, "path": str(path), "items": items}

    async def _delete(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            raise AdapterError(f"Path does not exist: {path}")
        try:
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
            return {"success": True, "path": str(path)}
        except Exception as e:
            raise AdapterError(f"Delete failed: {e}")