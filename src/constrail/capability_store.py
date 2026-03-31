"""
Persistence helpers for capability manifest lifecycle management.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from .database import CapabilityManifestModel, SessionLocal


class CapabilityStore:
    def list_manifests(
        self,
        agent_id: Optional[str] = None,
        active: Optional[bool] = None,
    ) -> list[CapabilityManifestModel]:
        db = SessionLocal()
        try:
            query = db.query(CapabilityManifestModel)
            if agent_id is not None:
                query = query.filter(CapabilityManifestModel.agent_id == agent_id)
            if active is not None:
                query = query.filter(CapabilityManifestModel.active == active)
            return query.order_by(CapabilityManifestModel.created_at.desc()).all()
        finally:
            db.close()

    def create_manifest(
        self,
        agent_id: str,
        tenant_id: Optional[str],
        namespace: Optional[str],
        version: int,
        allowed_tools: list[dict],
        active: bool = True,
    ) -> CapabilityManifestModel:
        db = SessionLocal()
        try:
            row = CapabilityManifestModel(
                agent_id=agent_id,
                tenant_id=tenant_id,
                namespace=namespace,
                version=version,
                allowed_tools=allowed_tools,
                created_at=datetime.utcnow(),
                active=active,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return row
        finally:
            db.close()


_default_capability_store: Optional[CapabilityStore] = None


def get_capability_store() -> CapabilityStore:
    global _default_capability_store
    if _default_capability_store is None:
        _default_capability_store = CapabilityStore()
    return _default_capability_store
