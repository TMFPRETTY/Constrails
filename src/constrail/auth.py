"""
Auth helpers for Constrails alpha.
Supports legacy static keys plus signed bearer tokens.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional, Any

from jose import JWTError, jwt

from .config import settings
from .database import RevokedTokenModel, SessionLocal


Role = Literal['agent', 'admin']


@dataclass
class AuthPrincipal:
    key: str
    role: Role
    tenant_id: Optional[str] = None
    namespace: Optional[str] = None
    subject: Optional[str] = None
    auth_type: str = 'api_key'
    token_id: Optional[str] = None

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

    def mint_token(
        self,
        *,
        role: Role,
        subject: str,
        tenant_id: Optional[str] = None,
        namespace: Optional[str] = None,
        agent_id: Optional[str] = None,
        expires_minutes: Optional[int] = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        exp = now + timedelta(minutes=expires_minutes or settings.token_expire_minutes)
        token_id = f"tok-{int(now.timestamp())}-{subject}"
        payload = {
            'jti': token_id,
            'role': role,
            'sub': subject,
            'iss': settings.token_issuer,
            'aud': settings.token_audience,
            'iat': int(now.timestamp()),
            'exp': int(exp.timestamp()),
        }
        if tenant_id is not None:
            payload['tenant_id'] = tenant_id
        if namespace is not None:
            payload['namespace'] = namespace
        if agent_id is not None:
            payload['agent_id'] = agent_id
        return jwt.encode(payload, settings.secret_key, algorithm=settings.token_algorithm)

    def inspect_token(self, token: str) -> dict[str, Any]:
        return jwt.get_unverified_claims(token)

    def revoke_token(self, token: str) -> dict[str, Any]:
        claims = self.inspect_token(token)
        token_id = claims.get('jti')
        if not token_id:
            raise ValueError('Token missing jti claim')
        db = SessionLocal()
        try:
            existing = db.query(RevokedTokenModel).filter(RevokedTokenModel.token_id == token_id).first()
            if existing is None:
                row = RevokedTokenModel(
                    token_id=token_id,
                    subject=claims.get('sub', 'unknown'),
                    role=claims.get('role', 'unknown'),
                    expires_at=datetime.fromtimestamp(claims['exp'], tz=timezone.utc) if claims.get('exp') else None,
                )
                db.add(row)
                db.commit()
            return {'revoked': True, 'token_id': token_id, 'subject': claims.get('sub')}
        finally:
            db.close()

    def is_token_revoked(self, token_id: str | None) -> bool:
        if not token_id:
            return False
        db = SessionLocal()
        try:
            row = db.query(RevokedTokenModel).filter(RevokedTokenModel.token_id == token_id).first()
            return row is not None
        finally:
            db.close()

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
        token_id = payload.get('jti')
        if role not in {'agent', 'admin'} or not sub:
            return None
        if self.is_token_revoked(token_id):
            return None

        return AuthPrincipal(
            key=token,
            role=role,
            tenant_id=payload.get('tenant_id'),
            namespace=payload.get('namespace'),
            subject=payload.get('agent_id') or sub,
            auth_type='bearer',
            token_id=token_id,
        )


_default_auth_service: AuthService | None = None


def get_auth_service() -> AuthService:
    global _default_auth_service
    if _default_auth_service is None:
        _default_auth_service = AuthService()
    return _default_auth_service
