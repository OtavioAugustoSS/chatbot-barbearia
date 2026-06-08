"""alinhamento_schema_dev

Revision ID: 93f27a8a4c60
Revises: ec0e2afe99be
Create Date: 2026-06-08 19:41:40.238874

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '93f27a8a4c60'
down_revision: Union[str, Sequence[str], None] = 'ec0e2afe99be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Alinhamento de schema com db/models.py (ADR-014).

    ⚠️ ESTA MIGRATION NÃO FOI APLICADA AUTOMATICAMENTE — requer decisão do dono.

    DROP usuarios.estado_atual: a coluna NÃO é referenciada em nenhum lugar do código
    (grep limpo em api/services/core/db/static/scripts), MAS **contém dados** legados
    (valor 'BOAS_VINDAS' em todas as linhas) de uma máquina de estado antiga, hoje
    substituída por status_conversa + o fluxo de menu. Como tem dados e o drop é
    irreversível (o downgrade re-cria a coluna, mas NÃO os dados), deixei para aplicar
    de forma ATENDIDA, com o dono ciente. Para aplicar: `alembic upgrade head`.

    NÃO incluído (divergências benignas que NÃO afetam runtime, exigem cuidado):
      - status_conversa ENUM→VARCHAR(20): precisa preservar server_default 'open'
        (MODIFY COLUMN no MySQL dropa o default se não for re-declarado).
      - filtros_salvos.criterios JSON→TEXT: trivial, mas agrupar com o de cima.
      - usuario_labels.atribuido_em (nullable): precisa backfill.

    NUNCA aplicar (falso-positivo perigoso do autogenerate):
      - historico_conversas.ID/id: MySQL é case-insensitive → MESMA coluna física.
        drop_column('ID')+add_column('id') = PERDA DE DADOS.
    """
    op.drop_column('usuarios', 'estado_atual')


def downgrade() -> None:
    op.add_column('usuarios', sa.Column('estado_atual', sa.String(length=50), nullable=True))
