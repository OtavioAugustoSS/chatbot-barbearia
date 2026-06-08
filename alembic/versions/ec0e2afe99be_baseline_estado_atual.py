"""baseline_estado_atual

Revision ID: ec0e2afe99be
Revises:
Create Date: 2026-06-08 00:34:27.890493

ADR-014 — BASELINE VAZIA DE PROPÓSITO.

Esta revisão NÃO cria tabelas. Ela representa o schema que JÁ EXISTE no banco
de dev (construído historicamente via create_all + SQLs manuais). Por isso:

  - Banco existente (já tem as tabelas):  alembic stamp head   (registra esta
    revisão sem rodar SQL — NÃO use upgrade).
  - Banco do zero:                        create_all cria o schema a partir dos
    models, depois  alembic stamp head.   (Ver runbook e ADR-014.)

A partir daqui, toda mudança em db/models.py vira uma migration via
`alembic revision --autogenerate -m "..."` (essas SIM têm corpo). NÃO preencha
upgrade()/downgrade() desta baseline.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec0e2afe99be'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
