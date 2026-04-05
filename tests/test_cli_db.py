import uuid
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from constrail.db_migrate import upgrade_db



def test_db_upgrade_and_current_commands(tmp_path):
    db_path = (tmp_path / f'{uuid.uuid4().hex}-cli-db.sqlite').resolve()
    if db_path.exists():
        db_path.unlink()
    database_url = f'sqlite:///{db_path}'

    upgrade_db('head', database_url=database_url)
    assert db_path.exists(), str(db_path)

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert 'approval_requests' in tables
        with engine.connect() as conn:
            version = conn.execute(text('SELECT version_num FROM alembic_version')).scalar_one()
            assert version == '5eb096cebe84'
    finally:
        engine.dispose()



def test_db_upgrade_stamps_existing_schema(tmp_path):
    db_path = (tmp_path / f'{uuid.uuid4().hex}-stamped.sqlite').resolve()
    if db_path.exists():
        db_path.unlink()
    database_url = f'sqlite:///{db_path}'

    engine = create_engine(database_url)
    try:
        with engine.begin() as conn:
            conn.execute(text('CREATE TABLE approval_requests (approval_id CHAR(36) PRIMARY KEY)'))
    finally:
        engine.dispose()

    upgrade_db('head', database_url=database_url)
