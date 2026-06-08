"""Fase 3 — auto-reativação do bot após timeout (webhook._verificar_e_reativar_bot).

Modo de teste é híbrido (conftest), BOT_REATIVAR_APOS_HORAS=24.
"""
from datetime import datetime, timezone, timedelta

import api.webhook as webhook
from db.models import Usuario


def _user(db, **kw):
    base = dict(telefone="5538666660001", nome_cliente="X", bot_ativo=False,
                aguardando_humano=False, atendente_id=None)
    base.update(kw)
    u = Usuario(**base)
    db.add(u); db.commit()
    return u


def test_reativa_apos_timeout(db):
    u = _user(db, bot_desativado_em=datetime.now(timezone.utc) - timedelta(hours=25))
    assert webhook._verificar_e_reativar_bot(db, u) is True
    assert u.bot_ativo is True
    assert u.reativado_por_timeout is True


def test_nao_reativa_se_recente(db):
    u = _user(db, telefone="5538666660002",
              bot_desativado_em=datetime.now(timezone.utc) - timedelta(hours=1))
    assert webhook._verificar_e_reativar_bot(db, u) is False
    assert u.bot_ativo is False


def test_hibrido_nao_reativa_com_atendente(db, atendente_teste):
    # Mesmo após 48h, se há atendente dono, exige devolução explícita.
    u = _user(db, telefone="5538666660003", atendente_id=atendente_teste.id,
              bot_desativado_em=datetime.now(timezone.utc) - timedelta(hours=48))
    assert webhook._verificar_e_reativar_bot(db, u) is False
    assert u.bot_ativo is False
