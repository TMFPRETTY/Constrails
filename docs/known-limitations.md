# Known Limitations

This document lists the most important current limitations in Constrails beta so operators and evaluators can make informed deployment decisions.

## 1. Approval worker durability

Constrails has a useful approval outbox, delivery tracking, retry hooks, a bounded worker, and a long-running worker mode. However:
- it is not yet documented as a distributed queue system
- duplicate-delivery tolerance should be assumed at webhook receivers
- operators should run it as a dedicated process and monitor backlog/failure counts

## 2. Sandbox coverage is stronger than before, but not universal

Constrails can enforce stricter sandbox posture and validate Docker-oriented production settings, but:
- environment validation is not yet broad across all target platforms
- Docker should still be treated as a carefully configured containment layer, not magic isolation
- operators remain responsible for host hardening and runtime security

## 3. Policy confidence depends on deployment posture

Constrails supports degraded and strict policy availability modes. Even with good live-path testing:
- richer rego/fallback parity validation can still improve confidence
- operators must choose degraded vs strict posture intentionally
- OPA availability remains an important trust boundary in production

## 4. Auth and key lifecycle are solid, but still maturing

Bearer token validation, revocation, key visibility, and rotation bridging exist, but:
- full enterprise key management is not yet built in
- external secret-manager integration remains an operator concern
- production deployments should minimize reliance on static keys

## 5. Audit integrity is better, but not externally anchored

Constrails includes audit verification and checkpoint export workflows, but:
- default storage is still operator-controlled infrastructure
- checkpoints are not yet externally notarized or signed for third-party attestation
- long-term retention and archival policies remain deployment-specific

## 6. Upgrade confidence is improving, but still not full GA posture

Constrails now has Alembic migrations, DB operator commands, and Postgres CI validation, but:
- broader multi-version upgrade-path testing is still needed
- restore-based rollback remains the default safe recovery posture
- operators should validate upgrades in staging before production rollout

## 7. Observability is useful, but not a packaged monitoring product

Constrails exposes admin metrics, `/metrics`, and operator docs, but:
- packaged dashboards are not bundled
- alert thresholds still need environment-specific tuning
- operators should integrate with their own monitoring stack

## 8. Remaining GA blockers are mostly release-time assurances

At this point, the major remaining blockers are less about missing core controls and more about final release-time confidence:
- explicit GA support promises
- final release security review
- confirmation that no unresolved high-severity issues remain
- final release notes that match the actual support posture

## 9. Beta means operational caution is still required

Constrails is real beta software, not a toy, but also not yet a fully mature GA control plane. Production-oriented pilots are reasonable. Mission-critical deployment should still be approached with staged rollout, backups, monitoring, and explicit operator ownership.
