"""
HTTP adapter for Constrail.
Handles external HTTP/HTTPS requests.
"""

import asyncio
import json
from typing import Optional, Any

import httpx

from ..models import ToolCall, ToolResult, ToolResultStatus
from .base import ToolAdapter, AdapterError


class HTTPAdapter(ToolAdapter):
    """Adapter for HTTP/HTTPS requests."""

    @property
    def tool_name(self) -> str:
        return "http_request"

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self.client = client or httpx.AsyncClient(timeout=30.0)

    async def execute(self, call: ToolCall) -> ToolResult:
        try:
            params = call.parameters or {}
            method = str(params.get("method", "GET")).upper()
            url = params.get("url", "")

            if not url:
                raise AdapterError("Missing required parameter 'url'")

            request_kwargs: dict[str, Any] = {}

            if "headers" in params:
                request_kwargs["headers"] = params["headers"]
            if "params" in params:
                request_kwargs["params"] = params["params"]
            if "json" in params:
                request_kwargs["json"] = params["json"]
            elif "body" in params:
                body = params["body"]
                if isinstance(body, dict):
                    request_kwargs["json"] = body
                elif isinstance(body, str):
                    request_kwargs["content"] = body.encode("utf-8")
                    request_kwargs.setdefault("headers", {})
                    request_kwargs["headers"].setdefault("Content-Type", "text/plain")
                elif isinstance(body, bytes):
                    request_kwargs["content"] = body
                    request_kwargs.setdefault("headers", {})
                    request_kwargs["headers"].setdefault("Content-Type", "application/octet-stream")
                else:
                    raise AdapterError(f"Unsupported body type: {type(body)}")

            if "timeout" in params and isinstance(params["timeout"], (int, float)):
                request_kwargs["timeout"] = params["timeout"]

            response = await self.client.request(method, url, **request_kwargs)

            result_data = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "url": str(response.url),
                "elapsed": response.elapsed.total_seconds(),
                "text": response.text,
            }

            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    result_data["json"] = response.json()
                except json.JSONDecodeError:
                    pass

            success = 200 <= response.status_code < 300
            return ToolResult(
                success=success,
                data=result_data,
                error=None if success else f"HTTP {response.status_code}",
                status=ToolResultStatus.SUCCESS if success else ToolResultStatus.ERROR,
            )

        except httpx.RequestError as e:
            return ToolResult(
                success=False,
                data={},
                error=f"HTTP request failed: {str(e)}",
                status=ToolResultStatus.ERROR,
            )
        except AdapterError as e:
            return ToolResult(
                success=False,
                data={},
                error=str(e),
                status=ToolResultStatus.ERROR,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                error=f"Unexpected error: {str(e)}",
                status=ToolResultStatus.ERROR,
            )

    async def close(self):
        await self.client.aclose()

    def __del__(self):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.close())
        except (RuntimeError, AttributeError):
            pass
