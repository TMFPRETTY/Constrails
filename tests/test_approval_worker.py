from constrail.approval import ApprovalService


def test_run_worker_reports_idle_backoff_summary(monkeypatch):
    service = ApprovalService()

    calls = {'count': 0}

    def _fake_drain(limit=20):
        calls['count'] += 1
        return {
            'processed': 0,
            'delivered': 0,
            'failed': 0,
            'idle': True,
        }

    monkeypatch.setattr(service, 'drain_outbox', _fake_drain)

    result = service.run_worker(
        cycles=3,
        sleep_seconds=0,
        limit=5,
        backoff_multiplier=2.0,
        max_sleep_seconds=4.0,
    )

    assert result['cycles'] == 3
    assert result['processed'] == 0
    assert result['delivered'] == 0
    assert result['failed'] == 0
    assert result['idle_cycles'] == 3
    assert len(result['cycle_results']) == 3
