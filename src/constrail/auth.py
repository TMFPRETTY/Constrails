"""
Simple auth helpers for Constrails alpha.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from .config import settings


Role = Literal['agent', 'admin']


@dataclass
class AuthPrincipal:
    key: str
    role: Role
    tenant_id: Optional[str] = None
    namespace: Optional[str] = None

    @property
    def scoped(self) -> bool:
        return bool(self.tenant_id or self.namespace)

    def allows_agent(self, agent_id: str) -> bool:
        if not self.scoped:
            return True
        return agent_id == settings.agent_api_key


class AuthService:
    def authenticate(self, api_key: str) -> AuthPrincipal | None:
        if api_key == settings.admin_api_key:
            return AuthPrincipal(
                key=api_key,
                role='admin',
                tenant_id=settings.admin_tenant_id,
                namespace=settings.admin_namespace,
            )
        if api_key == settings.agent_api_key:
            return AuthPrincipal(
                key=api_key,
                role='agent',
                tenant_id=settings.agent_tenant_id,
                namespace=settings.agent_namespace,
            )
        return None


_default_auth_service: AuthService | None = None


def get_auth_service() -> AuthService:
    global _default_auth_service
    if _default_auth_service is None:
        _default_auth_service = AuthService()
    return _default_auth_service
