"""
Rodada 2 — fluxo LGPD end-to-end via chat (P0).

"apagar meus dados" → confirmação "APAGAR" em 10min → exclusão total.
Qualquer outro texto ou janela expirada cancela. A canônica informativa
("política de privacidade") continua intacta.
"""
from datetime import datetime, timedelta, timezone

import pytest

from db.models import HistoricoConversa, Label, NotaInterna, Usuario, usuario_labels
from tests.conftest import _montar_payload_webhook


def _msg(client, tel, texto, mid):
    return client.post("/webhook", json=_montar_payload_webhook(tel, texto, message_id=mid))


def _setup_cliente_com_dados(db, tel, atendente_id=None):
    user = Usuario(telefone=tel, nome_cliente="LGPD Teste", bot_ativo=True)
    db.add(user)
    db.add(HistoricoConversa(telefone_usuario=tel, mensagem_cliente="oi", resposta_bot="olá",
                             origem="bot"))
    db.commit()
    if atendente_id:
        db.add(NotaInterna(telefone_usuario=tel, atendente_id=atendente_id, texto="nota"))
        label = Label(nome=f"lgpd-{tel[-4:]}", cor="#ff0000")
        db.add(label)
        db.commit()
        db.execute(usuario_labels.insert().values(telefone_usuario=tel, label_id=label.id))
        db.commit()
    return user


def test_pedido_seta_flag_e_pede_confirmacao(client, db):
    tel = "5538555580001"
    _setup_cliente_com_dados(db, tel)
    _msg(client, tel, "quero apagar meus dados", "wamid.lgpd.1")

    user = db.query(Usuario).filter_by(telefone=tel).first()
    db.refresh(user)
    assert user is not None  # NÃO apagou ainda
    assert user.exclusao_solicitada_em is not None
    confirmacao = db.query(HistoricoConversa).filter_by(
        telefone_usuario=tel, intencao="lgpd_confirmar").first()
    assert confirmacao is not None
    assert "APAGAR" in confirmacao.resposta_bot


def test_confirmacao_apaga_tudo_e_publica_sse(client, db, atendente_teste, monkeypatch):
    import api.webhook as wh

    eventos = []
    monkeypatch.setattr(wh.notificador, "publicar", lambda ev: eventos.append(ev))

    tel = "5538555580002"
    _setup_cliente_com_dados(db, tel, atendente_id=atendente_teste.id)
    _msg(client, tel, "apagar meus dados", "wamid.lgpd.2a")
    _msg(client, tel, "APAGAR", "wamid.lgpd.2b")

    assert db.query(Usuario).filter_by(telefone=tel).first() is None
    assert db.query(HistoricoConversa).filter_by(telefone_usuario=tel).count() == 0
    assert db.query(NotaInterna).filter_by(telefone_usuario=tel).count() == 0
    assert db.execute(
        usuario_labels.select().where(usuario_labels.c.telefone_usuario == tel)
    ).first() is None
    assert any(e["tipo"] == "cliente_apagado" and e["telefone"] == tel for e in eventos)


def test_confirmacao_minuscula_tambem_vale(client, db):
    tel = "5538555580003"
    _setup_cliente_com_dados(db, tel)
    _msg(client, tel, "pode deletar minha conta", "wamid.lgpd.3a")
    _msg(client, tel, "apagar", "wamid.lgpd.3b")
    assert db.query(Usuario).filter_by(telefone=tel).first() is None


def test_outro_texto_cancela_pedido(client, db):
    tel = "5538555580004"
    _setup_cliente_com_dados(db, tel)
    _msg(client, tel, "apagar meus dados", "wamid.lgpd.4a")
    _msg(client, tel, "pensando melhor, deixa", "wamid.lgpd.4b")

    user = db.query(Usuario).filter_by(telefone=tel).first()
    db.refresh(user)
    assert user is not None
    assert user.exclusao_solicitada_em is None  # cancelado


def test_janela_expirada_cancela(client, db):
    tel = "5538555580005"
    user = _setup_cliente_com_dados(db, tel)
    user.exclusao_solicitada_em = datetime.now(timezone.utc) - timedelta(minutes=11)
    db.commit()
    _msg(client, tel, "APAGAR", "wamid.lgpd.5")

    user = db.query(Usuario).filter_by(telefone=tel).first()
    assert user is not None  # janela venceu — não apagou
    db.refresh(user)
    assert user.exclusao_solicitada_em is None


def test_pergunta_informativa_nao_dispara_exclusao(client, db):
    """'política de privacidade' cai na canônica informativa, não seta flag."""
    tel = "5538555580006"
    _setup_cliente_com_dados(db, tel)
    _msg(client, tel, "qual a política de privacidade de vocês?", "wamid.lgpd.6")

    user = db.query(Usuario).filter_by(telefone=tel).first()
    db.refresh(user)
    assert user.exclusao_solicitada_em is None


def test_regex_exclusao_nao_casa_frases_soltas():
    from core.respostas_canonicas import REGEX_LGPD_EXCLUSAO

    assert not REGEX_LGPD_EXCLUSAO.search("quero apagar a luz do salão")
    assert not REGEX_LGPD_EXCLUSAO.search("como excluo um horário no app?")
    assert REGEX_LGPD_EXCLUSAO.search("quero apagar meus dados")
    assert REGEX_LGPD_EXCLUSAO.search("exclua minha conta por favor")
    assert REGEX_LGPD_EXCLUSAO.search("remover meu cadastro")
