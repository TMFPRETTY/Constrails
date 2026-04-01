from __future__ import annotations

import hashlib
import json
from typing import Any

from .database import AuditRecordModel, SessionLocal


class AuditVerifier:
    def verify(self) -> dict[str, Any]:
        db = SessionLocal()
        try:
            rows = db.query(AuditRecordModel).order_by(AuditRecordModel.start_time.asc()).all()
            previous_hash = None
            checked = 0
            for row in rows:
                expected = self._compute_hash(row, previous_hash)
                if row.chain_prev_hash != previous_hash:
                    return {
                        'ok': False,
                        'checked': checked,
                        'error': 'chain_prev_hash mismatch',
                        'request_id': str(row.request_id),
                    }
                if row.chain_hash != expected:
                    return {
                        'ok': False,
                        'checked': checked,
                        'error': 'chain_hash mismatch',
                        'request_id': str(row.request_id),
                    }
                previous_hash = row.chain_hash
                checked += 1
            return {'ok': True, 'checked': checked, 'error': None}
        finally:
            db.close()

    def _compute_hash(self, row, prev_hash: str | None) -> str:
        payload = {
            'prev_hash': prev_hash,
            'request_id': str(row.request_id),
            'agent_id': row.agent_id,
            'tool': row.tool,
            'parameters': row.parameters,
            'risk_score': row.risk_score,
            'risk_level': row.risk_level.value if hasattr(row.risk_level, 'value') else str(row.risk_level),
            'policy_decision': row.policy_decision.value if hasattr(row.policy_decision, 'value') else str(row.policy_decision),
            'final_decision': row.final_decision.value if hasattr(row.final_decision, 'value') else str(row.final_decision),
            'approval_id': str(row.approval_id) if row.approval_id else None,
            'replayed_from_approval_id': str(row.replayed_from_approval_id) if row.replayed_from_approval_id else None,
            'sandbox_id': row.sandbox_id,
            'error': row.error,
            'auth_type': row.auth_type,
            'auth_subject': row.auth_subject,
            'auth_token_id': row.auth_token_id,
            'auth_key_id': row.auth_key_id,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
        return hashlib.sha256(encoded).hexdigest()


_default_verifier: AuditVerifier | None = None


def get_audit_verifier() -> AuditVerifier:
    global _default_verifier
    if _default_verifier is None:
        _default_verifier = AuditVerifier()
    return _default_verifier
