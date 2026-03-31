"""
HTTP adapter for Constrail.
Performs HTTP/HTTPS requests.
"""

import httpx
import logging
from typing import Dict, Any

from .base import ToolAdapter, ToolResult

logger = logging.getLogger(__name__)


class HTTPAdapter(ToolAdapter):
    """Adapter for HTTP requests."""
    
    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute an HTTP request.
        
        Expected parameters:
        - method: HTTP method (GET, POST, etc.) default GET
        - url: URL to request
        - headers: dict of headers (optional)
        - body: request body for POST/PUT (optional)
        - timeout: timeout in seconds (optional)
        """
        method = parameters.get("method", "GET").upper()
        url = parameters.get("url")
        headers = parameters.get("headers", {})
        body = parameters.get("body")
        timeout = parameters.get("timeout", 30.0)
        
        if not url:
            return ToolResult(
                success=False,
                error="Missing required parameter 'url'",
                data=None,
                metadata={"adapter": "http"},
            )
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    content=body if isinstance(body, bytes) else body,
                    timeout=timeout,
                )
                
                # Prepare result data
                data = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response.text,
                }
                
                success = 200 <= response.status_code < 300
                error = None if success else f"HTTP {response.status_code}"
                
                return ToolResult(
                    success=success,
                    error=error,
                    data=data,
                    metadata={
                        "adapter": "http",
                        "method": method,
                        "url": url,
                    },
                )
        except httpx.TimeoutException:
            return ToolResult(
                success=False,
                error="Request timeout",
                data=None,
                metadata={"adapter": "http", "timeout": True},
            )
        except Exception as e:
            logger.exception(f"HTTP request failed: {e}")
            return ToolResult(
                success=False,
                error=f"HTTP request failed: {e}",
                data=None,
                metadata={"adapter": "http"},
            )