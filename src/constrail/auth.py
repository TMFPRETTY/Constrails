"""
Auth helpers for Constrails alpha.
Supports legacy static keys plus signed bearer tokens.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from jose import JWTError, jwt

from .config import settings


Role = Literal['agent', 'admin']


@dataclass
class AuthPrincipal:
    key: str
    role: Role
    tenant_id: Optional[str] = None
    namespace: Optional[str] = None
    subject: Optional[str] = None
    auth_type: str = 'api_key'

    @property
    def scoped(self) -> bool:
        return bool(self.tenant_id or self.namespace)

    def allows_agent(self, agent_id: str) -> bool:
        if not self.scoped:
            return True
        return agent_id == settings.agent_api_key or agent_id == (self.subject or settings.agent_api_key)


class AuthService:
    def authenticate(self, credential: str) -> AuthPrincipal | None:
        principal = self.authenticate_bearer_token(credential)
        if principal is not None:
            return principal
        return self.authenticate_api_key(credential)

    def authenticate_api_key(self, api_key: str) -> AuthPrincipal | None:
        if api_key == settings.admin_api_key:
            return AuthPrincipal(
                key=api_key,
                role='admin',
                tenant_id=settings.admin_tenant_id,
                namespace=settings.admin_namespace,
                subject='admin',
                auth_type='api_key',
            )
        if api_key == settings.agent_api_key:
            return AuthPrincipal(
                key=api_key,
                role='agent',
                tenant_id=settings.agent_tenant_id,
                namespace=settings.agent_namespace,
                subject=settings.agent_api_key,
                auth_type='api_key',
            )
        return None

    def authenticate_bearer_token(self, token: str) -> AuthPrincipal | None:
        if not settings.secret_key:
            return None
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.token_algorithm],
                audience=settings.token_audience,
                issuer=settings.token_issuer,
                options={'verify_aud': True, 'verify_iss': True},
            )
        except JWTError:
            return None

        role = payload.get('role')
        sub = payload.get('sub')
        if role not in {'agent', 'admin'} or not sub:
            return None

        return AuthPrincipal(
            key=token,
            role=role,
            tenant_id=payload.get('tenant_id'),
            namespace=payload.get('namespace'),
            subject=payload.get('agent_id') or sub,
            auth_type='bearer',
        )


_default_auth_service: AuthService | None = None


def get_auth_service() -> AuthService:
    global _default_auth_service
    if _default_auth_service is None:
        _default_auth_service = AuthService()
    return _default_auth_service
