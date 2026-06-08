"""Ambiente Alembic — ADR-014.

A URL do banco e o metadata vêm de db.* (sem duplicar credenciais).
db/models.py é a fonte de verdade do schema; o autogenerate compara
Base.metadata contra o banco real.
"""
import sys
from pathlib import Path
from logging.config import fileConfig

from alembic import context

# Garante o root do projeto no path para importar db.*
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import SQLALCHEMY_DATABASE_URL, Base
from db import models  # noqa: F401 — importa todos os models para registrá-los em Base.metadata

# Config do alembic.ini + logging
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# URL vem do projeto, não do alembic.ini (que fica vazio).
config.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Gera SQL sem conectar (alembic upgrade --sql)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Conecta ao banco e aplica as migrations."""
    from sqlalchemy import engine_from_config, pool

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
