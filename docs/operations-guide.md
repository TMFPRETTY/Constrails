# Constrails Operations Guide

This guide documents the current operator playbooks for observing Constrails, running the approval worker, and managing audit retention/export during beta.

## 1. Observability and Alerting

### Core metrics to watch

From `/metrics` and `GET /v1/admin/metrics`, prioritize:

- `constrail_approval_outbox_total`
- `constrail_approval_outbox_pending`
- `constrail_approval_outbox_failed`
- `constrail_approval_outbox_delivered`
- `constrail_quota_events_total`
- `constrail_quota_events_last_hour`
- `constrail_audit_records_total`
- `constrail_audit_records_last_hour`
- `constrail_sandbox_executions_total`
- `constrail_sandbox_failed_total`
- `constrail_sandbox_production_ready`

### Recommended dashboard sections

#### Approval operations
Track:
- pending outbox items
- failed deliveries
- delivered webhook volume
- approval summary trends over time

Investigate when:
- pending outbox items remain non-zero for multiple worker intervals
- failed deliveries rise after a deployment
- delivered volume drops unexpectedly while approval creation continues

#### Quota and abuse visibility
Track:
- quota events per hour
- spikes by environment or tenant
- unusual bursts after policy/config changes

Investigate when:
- quota events last hour spike sharply
- a single tenant or tool is saturating thresholds
- enforcement mode changes produce unexpected request suppression

#### Audit activity
Track:
- total audit growth
- audit records last hour
- checkpoint cadence
- audit verification success in post-change checks

Investigate when:
- audit growth stops during expected traffic
- audit verification fails after deployments or restores
- checkpoint/export cadence falls behind policy

#### Sandbox posture
Track:
- production-ready flag
- failed sandbox executions
- changes in sandbox validation warnings

Investigate when:
- `constrail_sandbox_production_ready` becomes `0`
- sandbox failures spike after image or runtime changes
- posture changes after host/container updates

### Recommended alerts

Start simple and practical:

- **Approval backlog alert:** pending outbox items remain above 0 for more than 10 minutes
- **Approval delivery degradation alert:** failed outbox items increase repeatedly within 15 minutes
- **Sandbox posture alert:** `constrail_sandbox_production_ready == 0` in production
- **Sandbox failure alert:** `constrail_sandbox_failed_total` increases unexpectedly after deployment
- **Quota pressure alert:** quota events last hour exceed normal baseline by a defined multiplier
- **Audit integrity alert:** `constrail audit-verify --json` fails during scheduled checks

## 2. Approval Worker Operations

### Current recommended mode

For beta, run the approval worker as a dedicated long-lived process using:

```bash
constrail approval-worker-serve --sleep-seconds 1 --limit 20 --backoff-multiplier 2 --max-sleep-seconds 30
```

If you want bounded runs for cron-style execution, use:

```bash
constrail approval-run-worker --cycles 10 --sleep-seconds 1 --limit 20 --backoff-multiplier 2 --max-sleep-seconds 30 --json
```

### Operational expectations

- only one primary worker process should drain the same outbox unless you intentionally accept duplicate race risk
- webhook receivers should be designed to tolerate retries and idempotent event handling
- failed deliveries should be reviewed through approval summary, outbox summary, and logs

### Failure handling

If the worker appears unhealthy:
1. run `constrail approval-summary --json`
2. run `constrail approval-outbox-summary --json`
3. inspect the webhook receiver and network path
4. retry a failed approval webhook with `constrail approval-retry-webhook <approval_id> --json`
5. if needed, drain the backlog manually with `constrail approval-drain-outbox --limit 20 --json`

### What to log

Capture and retain:
- worker start/stop events
- per-cycle processed/delivered/failed/idle summaries
- webhook failures and response errors
- configuration changes affecting webhook URL, secret, retry limit, or worker cadence

## 3. Audit Retention and Export Operations

### What to retain

At minimum, retain:
- audit records
- audit checkpoints
- approval records
- quota event history needed for incident review

### Recommended beta posture

- keep database backups on a regular schedule
- export audit checkpoints periodically with:

```bash
constrail audit-checkpoint --json
```

- store checkpoint artifacts outside the primary database environment
- run audit verification after restores, upgrades, and significant config changes:

```bash
constrail audit-verify --json
```

### Retention guidance

Suggested starting point:
- keep operational audit history hot in Postgres for at least 30 days
- archive older checkpoints and database backups to longer-term storage
- define environment-specific retention for quota event pruning

Quota pruning example:

```bash
constrail quota-prune --older-than-seconds 2592000 --json
```

### Incident review workflow

During an incident:
1. export or capture the current audit checkpoint
2. run audit verification
3. collect approval summaries and outbox status
4. capture quota summary and relevant quota events
5. preserve metrics snapshots and relevant logs before cleanup

## 4. Suggested Scheduled Checks

Daily or post-deploy:
- `constrail audit-verify --json`
- `constrail approval-summary --json`
- `constrail quota-summary --json`
- `constrail sandbox-validate --json`

Weekly:
- export and archive an audit checkpoint
- review quota pruning policy
- review approval delivery failure trends
- verify backup restore procedure in staging when possible

## 5. Beta Limitations to Remember

- approval worker durability is operationally useful, but not yet a fully documented distributed queue system
- observability is good enough for pilots, but not yet a polished packaged dashboard product
- audit checkpointing is useful for operator workflows, but not yet externally anchored or cryptographically notarized

Treat this guide as a living operator runbook and update it as production practices mature.
