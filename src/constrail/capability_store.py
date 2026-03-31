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
        tenant_id: Optional[str] = None,
        namespace: Optional[str] = None,
    ) -> list[CapabilityManifestModel]:
        db = SessionLocal()
        try:
            query = db.query(CapabilityManifestModel)
            if agent_id is not None:
                query = query.filter(CapabilityManifestModel.agent_id == agent_id)
            if active is not None:
                query = query.filter(CapabilityManifestModel.active == active)
            if tenant_id is not None:
                query = query.filter(CapabilityManifestModel.tenant_id == tenant_id)
            if namespace is not None:
                query = query.filter(CapabilityManifestModel.namespace == namespace)
            return query.order_by(CapabilityManifestModel.created_at.desc()).all()
        finally:
            db.close()

    def get_manifest(self, manifest_id: int) -> Optional[CapabilityManifestModel]:
        db = SessionLocal()
        try:
            return db.query(CapabilityManifestModel).filter(CapabilityManifestModel.id == manifest_id).first()
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

    def deactivate_manifest(self, manifest_id: int) -> Optional[CapabilityManifestModel]:
        db = SessionLocal()
        try:
            row = db.query(CapabilityManifestModel).filter(CapabilityManifestModel.id == manifest_id).first()
            if row is None:
                return None
            row.active = False
            db.commit()
            db.refresh(row)
            return row
        finally:
            db.close()

    def create_next_version(
        self,
        manifest_id: int,
        allowed_tools: Optional[list[dict]] = None,
        activate: bool = True,
    ) -> Optional[CapabilityManifestModel]:
        db = SessionLocal()
        try:
            row = db.query(CapabilityManifestModel).filter(CapabilityManifestModel.id == manifest_id).first()
            if row is None:
                return None
            if activate:
                row.active = False
            new_row = CapabilityManifestModel(
                agent_id=row.agent_id,
                tenant_id=row.tenant_id,
                namespace=row.namespace,
                version=row.version + 1,
                allowed_tools=allowed_tools if allowed_tools is not None else row.allowed_tools,
                created_at=datetime.utcnow(),
                active=activate,
            )
            db.add(new_row)
            db.commit()
            db.refresh(new_row)
            return new_row
        finally:
            db.close()


_default_capability_store: Optional[CapabilityStore] = None


def get_capability_store() -> CapabilityStore:
    global _default_capability_store
    if _default_capability_store is None:
        _default_capability_store = CapabilityStore()
    return _default_capability_store
