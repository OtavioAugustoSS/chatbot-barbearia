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

    ✅ APLICADA no MySQL de dev em 2026-06-08 com autorização do dono (verificação
    de integridade pós-migration: 4 usuários intactos, status_conversa preservado).

    DROP usuarios.estado_atual: coluna NÃO referenciada em lugar nenhum do código
    (grep limpo), com dados legados uniformes ('BOAS_VINDAS' em todas as linhas) de
    uma máquina de estado antiga, hoje substituída por status_conversa + fluxo de menu.
    O downgrade re-cria a coluna com o default 'BOAS_VINDAS' (não os valores por-linha,
    que eram todos o default mesmo).

    INCLUÍDO (autorizado pelo dono; schema real inspecionado via SHOW CREATE TABLE):
      - status_conversa ENUM('open',...)→VARCHAR(20), preservando NOT NULL DEFAULT 'open'.
      - filtros_salvos.criterios JSON→TEXT, preservando NOT NULL.
        (valores já são strings/JSON-em-texto compatíveis; conversão sem perda).

    NÃO incluído (exige backfill; divergência benigna):
      - usuario_labels.atribuido_em (nullable).
      - data_ultima_interacao TIMESTAMP (tem ON UPDATE CURRENT_TIMESTAMP no DB) — comportamento
        de auto-update útil; manter.

    NUNCA aplicar (falso-positivo perigoso do autogenerate):
      - historico_conversas.ID/id: MySQL é case-insensitive → MESMA coluna física.
        drop_column('ID')+add_column('id') = PERDA DE DADOS.
    """
    op.drop_column('usuarios', 'estado_atual')
    op.alter_column(
        'usuarios', 'status_conversa',
        existing_type=sa.Enum('open', 'pending', 'resolved', 'snoozed'),
        type_=sa.String(length=20),
        existing_nullable=False,
        existing_server_default=sa.text("'open'"),
    )
    op.alter_column(
        'filtros_salvos', 'criterios',
        existing_type=sa.JSON(),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        'filtros_salvos', 'criterios',
        existing_type=sa.Text(),
        type_=sa.JSON(),
        existing_nullable=False,
    )
    op.alter_column(
        'usuarios', 'status_conversa',
        existing_type=sa.String(length=20),
        type_=sa.Enum('open', 'pending', 'resolved', 'snoozed'),
        existing_nullable=False,
        existing_server_default=sa.text("'open'"),
    )
    op.add_column('usuarios', sa.Column('estado_atual', sa.String(length=50),
                                        server_default='BOAS_VINDAS', nullable=True))
