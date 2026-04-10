from click.testing import CliRunner
from sqlalchemy import create_engine, text

from constrail.cli import cli
from constrail.db_migrate import BASELINE_REVISION, upgrade_db


runner = CliRunner()


def test_existing_db_migration_validation_path(tmp_path):
    db_path = tmp_path / 'existing-rehearsal.sqlite'
    database_url = f'sqlite:///{db_path}'

    engine = create_engine(database_url)
    try:
        with engine.begin() as conn:
            conn.execute(text('CREATE TABLE approval_requests (approval_id CHAR(36) PRIMARY KEY)'))
    finally:
        engine.dispose()

    upgrade_db('head', database_url=database_url)

    engine = create_engine(database_url)
    try:
        tables = set(__import__('sqlalchemy').inspect(engine).get_table_names())
        assert 'approval_requests' in tables
    finally:
        engine.dispose()


def test_approval_worker_serve_emits_cycle_json(monkeypatch):
    from constrail import cli as cli_module

    class FakeService:
        def __init__(self):
            self.calls = 0

        def drain_outbox(self, limit=20):
            self.calls += 1
            return {
                'processed': 0,
                'delivered': 0,
                'failed': 0,
                'idle': True,
            }

    monkeypatch.setattr(cli_module, 'init_db', lambda: None)
    monkeypatch.setattr(cli_module, 'get_approval_service', lambda: FakeService())
    monkeypatch.setattr(cli_module.time, 'sleep', lambda seconds: None)

    result = runner.invoke(
        cli,
        ['approval-worker-serve', '--sleep-seconds', '0', '--limit', '5', '--max-cycles', '1'],
    )

    assert result.exit_code == 0
    assert '"cycle": 1' in result.output
    assert '"idle": true' in result.output.lower()


def test_metrics_and_alert_review_commands_smoke():
    result = runner.invoke(cli, ['doctor', '--json'])
    assert result.exit_code == 0
    assert '"production_ready"' in result.output

    result = runner.invoke(cli, ['sandbox-validate', '--json'])
    assert result.exit_code == 0
    assert '"production_ready"' in result.output
