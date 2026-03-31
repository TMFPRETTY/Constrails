"""
Capability manager for Constrail.
Manages agent capabilities and validates tool permissions.
"""

import json
import logging
import os
from typing import Dict, List, Set, Optional
from dataclasses import dataclass

from ..models import AgentIdentity
from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class ToolAllowance:
    """Allowed tool with optional constraints."""
    tool_name: str
    allowed_parameters: List[str] = None  # None means all parameters allowed
    deny_parameters: List[str] = None
    max_calls_per_minute: Optional[int] = None
    require_approval: bool = False


@dataclass
class CapabilityManifest:
    """Capability manifest for an agent."""
    agent_id: str
    version: int
    allowances: List[ToolAllowance]
    expires_at: Optional[str] = None  # ISO timestamp


class CapabilityManager:
    """Manages agent capabilities and validates tool calls."""
    
    def __init__(self):
        self.manifests: Dict[str, CapabilityManifest] = {}
        self._load_manifests()
    
    def _load_manifests(self):
        """Load capability manifests from disk."""
        manifests_dir = os.path.join(settings.policy_dir, "capabilities")
        if not os.path.exists(manifests_dir):
            logger.warning(f"Capabilities directory does not exist: {manifests_dir}")
            return
        
        for filename in os.listdir(manifests_dir):
            if filename.endswith(".json"):
                path = os.path.join(manifests_dir, filename)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    manifest = self._parse_manifest(data)
                    self.manifests[manifest.agent_id] = manifest
                    logger.info(f"Loaded capability manifest for agent {manifest.agent_id}")
                except Exception as e:
                    logger.error(f"Failed to load capability manifest {filename}: {e}")
    
    def _parse_manifest(self, data: dict) -> CapabilityManifest:
        """Parse JSON data into CapabilityManifest."""
        allowances = []
        for allowance_data in data.get("allowances", []):
            tool_name = allowance_data.get("tool")
            if not tool_name:
                continue
            allowance = ToolAllowance(
                tool_name=tool_name,
                allowed_parameters=allowance_data.get("allowed_parameters"),
                deny_parameters=allowance_data.get("deny_parameters"),
                max_calls_per_minute=allowance_data.get("max_calls_per_minute"),
                require_approval=allowance_data.get("require_approval", False),
            )
            allowances.append(allowance)
        
        return CapabilityManifest(
            agent_id=data.get("agent_id", "unknown"),
            version=data.get("version", 1),
            allowances=allowances,
            expires_at=data.get("expires_at"),
        )
    
    def is_tool_allowed(self, agent: AgentIdentity, tool: str, parameters: Dict[str, any]) -> bool:
        """
        Check if the agent is allowed to call the tool with given parameters.
        Returns True if allowed, False otherwise.
        """
        manifest = self.manifests.get(agent.agent_id)
        if manifest is None:
            logger.warning(f"No capability manifest found for agent {agent.agent_id}")
            return False
        
        # Check expiration
        if manifest.expires_at:
            # Simple expiration check (TODO: parse ISO timestamp)
            pass
        
        # Find allowance for this tool
        allowance = None
        for a in manifest.allowances:
            if a.tool_name == tool:
                allowance = a
                break
        
        if allowance is None:
            logger.warning(f"Tool {tool} not allowed for agent {agent.agent_id}")
            return False
        
        # Check parameter constraints
        if allowance.allowed_parameters is not None:
            for param in parameters.keys():
                if param not in allowance.allowed_parameters:
                    logger.warning(f"Parameter {param} not allowed for tool {tool}")
                    return False
        
        if allowance.deny_parameters is not None:
            for param in parameters.keys():
                if param in allowance.deny_parameters:
                    logger.warning(f"Parameter {param} denied for tool {tool}")
                    return False
        
        # TODO: rate limiting
        
        return True
    
    def get_allowed_tools(self, agent_id: str) -> List[str]:
        """Get list of allowed tools for an agent."""
        manifest = self.manifests.get(agent_id)
        if manifest is None:
            return []
        return [a.tool_name for a in manifest.allowances]
    
    def reload(self):
        """Reload manifests from disk."""
        self.manifests.clear()
        self._load_manifests()


# Default capability manager instance
_default_capability_manager: Optional[CapabilityManager] = None


def get_capability_manager() -> CapabilityManager:
    """Get or create the default capability manager."""
    global _default_capability_manager
    if _default_capability_manager is None:
        _default_capability_manager = CapabilityManager()
    return _default_capability_manager