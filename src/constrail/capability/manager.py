"""
Capability manager for Constrail.
Manages agent capabilities and validates tool permissions.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

from ..config import settings
from ..models import AgentIdentity

logger = logging.getLogger(__name__)


@dataclass
class ToolAllowance:
    """Allowed tool with optional constraints."""

    tool_name: str
    allowed_parameters: Optional[List[str]] = None
    deny_parameters: Optional[List[str]] = None
    max_calls_per_minute: Optional[int] = None
    require_approval: bool = False
    path_prefixes: List[str] = field(default_factory=list)
    allowed_domains: List[str] = field(default_factory=list)
    command_allowlist: List[str] = field(default_factory=list)


@dataclass
class CapabilityManifest:
    """Capability manifest for an agent."""

    agent_id: str
    tenant_id: Optional[str]
    namespace: Optional[str]
    version: int
    allowances: List[ToolAllowance]
    expires_at: Optional[str] = None


class CapabilityManager:
    """Manages agent capabilities and validates tool calls."""

    def __init__(self):
        self.manifests: Dict[str, CapabilityManifest] = {}
        self._load_manifests()

    def _load_manifests(self):
        manifests_dir = os.path.join(settings.policy_dir, "capabilities")
        if not os.path.exists(manifests_dir):
            logger.warning("Capabilities directory does not exist: %s", manifests_dir)
            return

        for filename in os.listdir(manifests_dir):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(manifests_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                manifest = self._parse_manifest(data)
                self.manifests[self._manifest_key(manifest.agent_id, manifest.tenant_id, manifest.namespace)] = manifest
                logger.info("Loaded capability manifest for agent %s", manifest.agent_id)
            except Exception as e:
                logger.error("Failed to load capability manifest %s: %s", filename, e)

    def _manifest_key(self, agent_id: str, tenant_id: Optional[str], namespace: Optional[str]) -> str:
        return f"{tenant_id or '_'}::{namespace or '_'}::{agent_id}"

    def _parse_manifest(self, data: dict) -> CapabilityManifest:
        allowances = []
        for allowance_data in data.get("allowances", []):
            tool_name = allowance_data.get("tool")
            if not tool_name:
                continue
            allowances.append(
                ToolAllowance(
                    tool_name=tool_name,
                    allowed_parameters=allowance_data.get("allowed_parameters"),
                    deny_parameters=allowance_data.get("deny_parameters"),
                    max_calls_per_minute=allowance_data.get("max_calls_per_minute"),
                    require_approval=allowance_data.get("require_approval", False),
                    path_prefixes=allowance_data.get("path_prefixes", []),
                    allowed_domains=allowance_data.get("allowed_domains", []),
                    command_allowlist=allowance_data.get("command_allowlist", []),
                )
            )

        return CapabilityManifest(
            agent_id=data.get("agent_id", "unknown"),
            tenant_id=data.get("tenant_id"),
            namespace=data.get("namespace"),
            version=data.get("version", 1),
            allowances=allowances,
            expires_at=data.get("expires_at"),
        )

    def _find_manifest(self, agent: AgentIdentity) -> Optional[CapabilityManifest]:
        keys = [
            self._manifest_key(agent.agent_id, agent.tenant_id, agent.namespace),
            self._manifest_key(agent.agent_id, agent.tenant_id, None),
            self._manifest_key(agent.agent_id, None, None),
        ]
        for key in keys:
            manifest = self.manifests.get(key)
            if manifest is not None:
                return manifest

        # Backwards-compatible fallback for agent-only callers when manifests are tenant-scoped.
        for manifest in self.manifests.values():
            if manifest.agent_id == agent.agent_id:
                if agent.tenant_id is not None and manifest.tenant_id not in {None, agent.tenant_id}:
                    continue
                return manifest
        return None

    def is_tool_allowed(self, agent: AgentIdentity, tool: str, parameters: Dict[str, Any]) -> bool:
        manifest = self._find_manifest(agent)
        if manifest is None:
            logger.warning("No capability manifest found for agent %s", agent.agent_id)
            return False

        allowance = next((a for a in manifest.allowances if a.tool_name == tool), None)
        if allowance is None:
            logger.warning("Tool %s not allowed for agent %s", tool, agent.agent_id)
            return False

        if allowance.allowed_parameters is not None:
            for param in parameters.keys():
                if param not in allowance.allowed_parameters:
                    logger.warning("Parameter %s not allowed for tool %s", param, tool)
                    return False

        if allowance.deny_parameters is not None:
            for param in parameters.keys():
                if param in allowance.deny_parameters:
                    logger.warning("Parameter %s denied for tool %s", param, tool)
                    return False

        if allowance.path_prefixes and not self._path_allowed(parameters.get("path"), allowance.path_prefixes):
            logger.warning("Path %s not allowed for tool %s", parameters.get("path"), tool)
            return False

        if allowance.allowed_domains and not self._domain_allowed(parameters.get("url"), allowance.allowed_domains):
            logger.warning("URL %s not allowed for tool %s", parameters.get("url"), tool)
            return False

        if allowance.command_allowlist and not self._command_allowed(parameters.get("command"), allowance.command_allowlist):
            logger.warning("Command %s not allowed for tool %s", parameters.get("command"), tool)
            return False

        return True

    def _path_allowed(self, path: Optional[str], prefixes: List[str]) -> bool:
        if not path:
            return False
        normalized = os.path.normpath(path)
        return any(
            normalized == os.path.normpath(prefix) or normalized.startswith(os.path.normpath(prefix).rstrip(os.sep) + os.sep)
            for prefix in prefixes
        )

    def _domain_allowed(self, url: Optional[str], allowed_domains: List[str]) -> bool:
        if not url:
            return False
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        return hostname in allowed_domains

    def _command_allowed(self, command: Optional[str], allowlist: List[str]) -> bool:
        if not command:
            return False
        command = command.strip()
        for allowed in allowlist:
            if command == allowed or command.startswith(f"{allowed} "):
                return True
        return False

    def get_allowed_tools(self, agent_id: str, tenant_id: Optional[str] = None, namespace: Optional[str] = None) -> List[str]:
        agent = AgentIdentity(agent_id=agent_id, tenant_id=tenant_id, namespace=namespace)
        manifest = self._find_manifest(agent)
        if manifest is None:
            return []
        return [a.tool_name for a in manifest.allowances]

    def reload(self):
        self.manifests.clear()
        self._load_manifests()


_default_capability_manager: Optional[CapabilityManager] = None


def get_capability_manager() -> CapabilityManager:
    global _default_capability_manager
    if _default_capability_manager is None:
        _default_capability_manager = CapabilityManager()
    return _default_capability_manager
