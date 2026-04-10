# Constrails GA Checklist

This document is the live execution board for moving Constrails from beta to general availability.

Status labels:
- **Done**: shipped and documented
- **Partial**: materially in place, but not yet strong enough for GA sign-off
- **Open**: still needs implementation or real-world validation

## 1. Release bar

### Current status
- **Done**: full automated suite is green on `main`
- **Done**: Postgres migration validation exists in CI
- **Done**: production deployment docs, operations guide, known limitations, and release guidance exist
- **Partial**: security review has been refreshed, but not yet as a final intended GA release review
- **Open**: no known unresolved high-severity security issues remain
- **Open**: release notes for the eventual GA release still need to clearly describe support posture and limitations

### Remaining work
- perform a final GA-targeted security review pass
- produce GA release notes and explicit support posture language
- confirm no unresolved high-severity issues remain at release time

## 2. Production guarantees

### Current status
- **Done**: supported Python and Postgres baseline is documented
- **Done**: upgrade, backup, restore, and rollback posture are documented
- **Partial**: upgrade procedure is tested in CI for baseline migration flows
- **Open**: staged production-like upgrade rehearsal on a realistic existing database
- **Open**: broader multi-version upgrade-path validation

### Remaining work
- run and document a staged upgrade rehearsal on a non-trivial database
- validate at least one existing-schema upgrade path between released versions
- decide whether additional rollback tooling or guidance is needed before GA

## 3. Operations readiness

### Current status
- **Done**: `/metrics` and admin metrics expose key operator signals
- **Done**: recommended dashboards and alert guidance are documented
- **Done**: approval worker runbook is documented
- **Done**: audit retention and export runbook is documented
- **Done**: scheduled operational checks are documented
- **Partial**: observability is operator-usable, but not yet a polished packaged dashboard/alerts bundle

### Remaining work
- optionally ship example dashboards or alert rules
- run an end-to-end operational smoke review using the documented runbooks

## 4. Security and trust

### Current status
- **Done**: security audit exists and release-bar security expectations are documented
- **Done**: known trust boundaries and deployment assumptions are documented
- **Partial**: secret and token lifecycle guidance is production-usable, but still early compared with mature enterprise key management
- **Done**: sandbox production posture requirements are documented and validated
- **Done**: audit verification workflow is documented for upgrades and restores
- **Partial**: audit checkpoints exist, but are not externally anchored or signed for stronger third-party attestation

### Remaining work
- perform a final GA security review pass
- decide whether externally anchored or signed audit checkpoints are required before GA
- tighten key lifecycle/operator guidance where needed

## 5. Positioning and support expectations

### Current status
- **Done**: README language matches current beta support posture
- **Done**: release guide targets the intended beta/release-candidate flow
- **Done**: known limitations are linked from public docs
- **Done**: current messaging avoids unsupported GA claims
- **Open**: final GA support matrix and support promise language

### Remaining work
- define GA support expectations explicitly
- decide what version-compatibility and deprecation promises GA will make

## 6. Recommended final gate

A practical final gate before GA should include:

1. fresh deploy on Postgres
2. migration on an existing staged database
3. approval worker smoke verification
4. audit verification and checkpoint export
5. sandbox posture validation
6. metrics and alert smoke review
7. sign-off that docs match the shipped system

## 7. Immediate next implementation batches

### Batch D, final GA validation
- run a realistic staged Postgres upgrade rehearsal
- validate migration on an existing staged database snapshot or rehearsal DB
- perform approval worker smoke verification using the ops guide
- perform metrics and alert smoke review

### Batch E, final security and support posture
- refresh the security audit as a GA-targeted review
- define the GA support matrix and compatibility promises
- decide whether signed/external audit anchoring is required before GA

### Batch F, GA release prep
- draft GA release notes
- update README/release docs from beta to GA only if the above gates are actually satisfied
- perform final release sign-off

Until those conditions are met, Constrails should remain in beta.
