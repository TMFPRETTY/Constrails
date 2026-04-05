from sqlalchemy import create_engine, inspect, text

from constrail.db_migrate import BASELINE_REVISION, current_db, upgrade_db



def test_upgrade_db_creates_schema_in_fresh_sqlite(tmp_path):
    db_path = tmp_path / 'fresh.sqlite'
    database_url = f'sqlite:///{db_path}'

    upgrade_db('head', database_url=database_url)

    engine = create_engine(database_url)
    try:
        tables = set(inspect(engine).get_table_names())
        assert 'approval_requests' in tables
        with engine.connect() as conn:
            version = conn.execute(text('SELECT version_num FROM alembic_version')).scalar_one()
            assert version == BASELINE_REVISION
    finally:
        engine.dispose()


def test_upgrade_db_stamps_existing_schema(tmp_path):
    db_path = tmp_path / 'existing.sqlite'
    database_url = f'sqlite:///{db_path}'

    engine = create_engine(database_url)
    try:
        with engine.begin() as conn:
            conn.execute(text('CREATE TABLE approval_requests (approval_id CHAR(36) PRIMARY KEY)'))
    finally:
        engine.dispose()

    upgrade_db('head', database_url=database_url)
