"""
Base classes for tool adapters.
"""

import abc
from typing import Any, Dict
from ..models import ToolCall


class ToolAdapter(abc.ABC):
    """Abstract base class for all tool adapters."""

    @abc.abstractmethod
    async def execute(self, call: ToolCall) -> Dict[str, Any]:
        """Execute the tool call and return a result dict."""
        pass

    @property
    @abc.abstractmethod
    def tool_name(self) -> str:
        """Name of the tool this adapter handles."""
        pass


class AdapterError(Exception):
    """Raised when a tool adapter encounters an error."""
    pass