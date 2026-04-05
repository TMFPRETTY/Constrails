from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from .config import settings


BASELINE_REVISION = '5eb096cebe84'


def alembic_config(database_url: str | None = None) -> Config:
    repo_root = Path(__file__).resolve().parents[2]
    cfg = Config(str(repo_root / 'alembic.ini'))
    cfg.set_main_option('script_location', str(repo_root / 'migrations'))
    effective_url = database_url or settings.database_url or cfg.get_main_option('sqlalchemy.url')
    cfg.set_main_option('sqlalchemy.url', effective_url)
    return cfg


def _maybe_stamp_existing_schema(cfg: Config) -> bool:
    engine = create_engine(cfg.get_main_option('sqlalchemy.url'))
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        if tables and 'alembic_version' not in tables:
            command.stamp(cfg, BASELINE_REVISION)
            return True
        return False
    finally:
        engine.dispose()



def upgrade_db(revision: str = 'head', database_url: str | None = None) -> None:
    cfg = alembic_config(database_url)
    stamped_existing = _maybe_stamp_existing_schema(cfg)
    if stamped_existing and revision == 'head':
        return
    url = cfg.get_main_option('sqlalchemy.url')
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            cfg.attributes['connection'] = connection
            command.upgrade(cfg, revision)
    finally:
        engine.dispose()


def current_db(verbose: bool = False, database_url: str | None = None) -> None:
    cfg = alembic_config(database_url)
    url = cfg.get_main_option('sqlalchemy.url')
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            cfg.attributes['connection'] = connection
            command.current(cfg, verbose=verbose)
    finally:
        engine.dispose()
