"""
Base classes for tool adapters.
"""

import abc

from ..models import ToolCall, ToolResult


class ToolAdapter(abc.ABC):
    """Abstract base class for all tool adapters."""

    @abc.abstractmethod
    async def execute(self, call: ToolCall) -> ToolResult:
        """Execute the tool call and return a ToolResult."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def tool_name(self) -> str:
        """Name of the tool this adapter handles."""
        raise NotImplementedError


class AdapterError(Exception):
    """Raised when a tool adapter encounters an error."""

    pass
