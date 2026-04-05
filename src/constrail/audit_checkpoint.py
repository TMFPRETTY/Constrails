from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .database import AuditRecordModel, SessionLocal


def create_audit_checkpoint(output_path: str | None = None) -> dict[str, Any]:
    db = SessionLocal()
    try:
        rows = db.query(AuditRecordModel).order_by(AuditRecordModel.start_time.asc()).all()
        if not rows:
            payload = {
                'created_at': datetime.utcnow().isoformat(),
                'records': 0,
                'last_request_id': None,
                'chain_hash': None,
            }
        else:
            last = rows[-1]
            payload = {
                'created_at': datetime.utcnow().isoformat(),
                'records': len(rows),
                'last_request_id': str(last.request_id),
                'chain_hash': last.chain_hash,
            }
        payload['checkpoint_hash'] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
        ).hexdigest()
        if output_path:
            target = Path(output_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(payload, indent=2))
        return payload
    finally:
        db.close()
