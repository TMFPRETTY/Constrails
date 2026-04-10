# Constrails GA Checklist

This checklist defines the bar for moving Constrails from beta to general availability.

## 1. Release bar

Before GA, all of the following should be true:

- [ ] full automated suite is green on `main`
- [ ] Postgres migration validation is green in CI
- [ ] production deployment docs are current
- [ ] operations guide is current
- [ ] known limitations are current and honest
- [ ] security review has been refreshed for the intended GA release
- [ ] no known unresolved high-severity security issues remain
- [ ] release notes clearly describe supported deployment posture and limitations

## 2. Production guarantees

- [ ] supported Python and Postgres versions are explicitly documented
- [ ] upgrade procedure is documented and tested
- [ ] backup and restore procedure is documented
- [ ] rollback posture is documented
- [ ] at least one staged production-like upgrade rehearsal has been completed

## 3. Operations readiness

- [ ] `/metrics` and admin metrics cover the key operator signals
- [ ] recommended dashboards and alerts are documented
- [ ] approval worker runbook is documented
- [ ] audit retention and export runbook is documented
- [ ] scheduled operational checks are documented

## 4. Security and trust

- [ ] security audit has been refreshed for the release
- [ ] known trust boundaries and deployment assumptions are documented
- [ ] secret and token lifecycle guidance is production-usable
- [ ] sandbox production posture requirements are documented and validated
- [ ] audit verification workflow is documented for upgrades and restores

## 5. Positioning and support expectations

- [ ] README language matches actual support posture
- [ ] release guide targets the intended release class
- [ ] known limitations document is linked from public docs
- [ ] GA messaging avoids unsupported claims

## 6. Recommended final gate

A practical final gate before GA should include:

1. fresh deploy on Postgres
2. migration on an existing staged database
3. approval worker smoke verification
4. audit verification and checkpoint export
5. sandbox posture validation
6. metrics and alert smoke review
7. sign-off that docs match the shipped system

Until those conditions are met, Constrails should remain in beta.
