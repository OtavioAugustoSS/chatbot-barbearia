"""Fase 3 — cobertura dos fluxos de menu interativo + sub-fluxos.

É a UX primária do bot e estava sem teste automatizado. Os fluxos respondem
de forma DETERMINÍSTICA (sem IA); cada teste afirma o tipo de envio
(texto/lista/botões) e o conteúdo canônico — se a IA fosse acionada por engano,
a resposta seria o fake do conftest ("Resposta de teste."), e as asserções de
conteúdo falhariam.
"""
import pytest

import api.webhook as webhook
from db.models import Usuario, HistoricoConversa, Servico, Horario


# ----------------------- helpers de payload Meta -----------------------
def _payload_interativo(telefone, item_id, tipo="list_reply", mid="i1", nome="Cliente"):
    reply_key = "list_reply" if tipo == "list_reply" else "button_reply"
    return {
        "object": "whatsapp_business_account",
        "entry": [{"id": "e", "changes": [{"value": {
            "messaging_product": "whatsapp",
            "metadata": {"display_phone_number": "x", "phone_number_id": "0"},
            "contacts": [{"profile": {"name": nome}, "wa_id": telefone}],
            "messages": [{"from": telefone, "id": mid, "timestamp": "1700000000",
                          "type": "interactive",
                          "interactive": {"type": tipo, reply_key: {"id": item_id, "title": "x"}}}],
        }, "field": "messages"}]}],
    }


def _payload_texto(telefone, texto, mid="t1", nome="Cliente"):
    return {
        "object": "whatsapp_business_account",
        "entry": [{"id": "e", "changes": [{"value": {
            "messaging_product": "whatsapp",
            "metadata": {"display_phone_number": "x", "phone_number_id": "0"},
            "contacts": [{"profile": {"name": nome}, "wa_id": telefone}],
            "messages": [{"from": telefone, "id": mid, "timestamp": "1700000000",
                          "type": "text", "text": {"body": texto}}],
        }, "field": "messages"}]}],
    }


@pytest.fixture
def spy(monkeypatch):
    """Espia o que o bot envia. Patcha a INSTÂNCIA (precede o mock de classe do conftest)."""
    enviados = []
    monkeypatch.setattr(webhook.whatsapp, "enviar_mensagem_texto",
                        lambda numero, texto: (enviados.append(("texto", texto)) or (True, "w")))
    monkeypatch.setattr(webhook.whatsapp, "enviar_lista_interativa",
                        lambda **kw: (enviados.append(("lista", kw.get("body_text", ""))) or (True, "w")))
    monkeypatch.setattr(webhook.whatsapp, "enviar_botoes_resposta",
                        lambda **kw: (enviados.append(("botoes", kw.get("body_text", ""))) or (True, "w")))
    return enviados


def _kinds(env):
    return [k for k, _ in env]


def _blob(env):
    return " ".join(t for _, t in env).lower()


def _seed_user(db, telefone, com_historico=False, bot_ativo=True):
    db.add(Usuario(telefone=telefone, nome_cliente="Cliente", bot_ativo=bot_ativo))
    db.commit()
    if com_historico:
        db.add(HistoricoConversa(telefone_usuario=telefone, mensagem_cliente="oi",
                                 resposta_bot="menu", origem="bot"))
        db.commit()


# ----------------------------- 1º contato -----------------------------
def test_primeiro_contato_envia_menu_lista(client, db, spy):
    tel = "5538000000001"
    _seed_user(db, tel, com_historico=False)
    r = client.post("/webhook", json=_payload_texto(tel, "oi quero saber dos serviços", "p1"))
    assert r.status_code == 200
    assert "lista" in _kinds(spy)


# -------------------- itens de menu → resposta canônica --------------------
def test_menu_horario_local_responde_canonica(client, db, spy):
    tel = "5538000000002"
    _seed_user(db, tel, com_historico=True)
    r = client.post("/webhook", json=_payload_interativo(tel, "MENU_HORARIO_LOCAL", "list_reply", "p2"))
    assert r.status_code == 200
    assert "texto" in _kinds(spy)
    assert "hor" in _blob(spy)  # horário/funcionamento


def test_menu_pagamento_responde_canonica(client, db, spy):
    tel = "5538000000003"
    _seed_user(db, tel, com_historico=True)
    r = client.post("/webhook", json=_payload_interativo(tel, "MENU_PAGAMENTO", "list_reply", "p3"))
    assert r.status_code == 200
    assert "texto" in _kinds(spy)
    assert "pix" in _blob(spy) or "pagamento" in _blob(spy) or "cart" in _blob(spy)


def test_menu_agendamento_redireciona_appbarber(client, db, spy):
    tel = "5538000000004"
    _seed_user(db, tel, com_historico=True)
    r = client.post("/webhook", json=_payload_interativo(tel, "MENU_AGENDAMENTO", "list_reply", "p4"))
    assert r.status_code == 200
    assert len(spy) > 0
    assert "appbarber" in _blob(spy)  # nunca agenda — sempre redireciona


# ------------------------ sub-fluxos de serviços ------------------------
def test_menu_servicos_abre_subflow_categorias(client, db, spy):
    tel = "5538000000005"
    _seed_user(db, tel, com_historico=True)
    db.add(Servico(nome_servico="Corte", preco=40, tempo_estimado_minutos=30, categoria="barbearia", ativo=True))
    db.commit()
    r = client.post("/webhook", json=_payload_interativo(tel, "MENU_SERVICOS_PRECO", "list_reply", "p5"))
    assert r.status_code == 200
    assert "botoes" in _kinds(spy) or "lista" in _kinds(spy)


def test_sub_serv_barbearia_lista_servicos(client, db, spy):
    tel = "5538000000006"
    _seed_user(db, tel, com_historico=True)
    db.add(Servico(nome_servico="Corte Degradê", preco=45, tempo_estimado_minutos=40, categoria="barbearia", ativo=True))
    db.commit()
    r = client.post("/webhook", json=_payload_interativo(tel, "SUB_SERV_BARBEARIA", "button_reply", "p6"))
    assert r.status_code == 200
    assert "degrad" in _blob(spy) or "corte" in _blob(spy)


def test_sub_voltar_menu_reabre_lista(client, db, spy):
    tel = "5538000000007"
    _seed_user(db, tel, com_historico=True)
    r = client.post("/webhook", json=_payload_interativo(tel, "SUB_VOLTAR_MENU", "button_reply", "p7"))
    assert r.status_code == 200
    assert "lista" in _kinds(spy)


# ----------------------- pedido de menu por texto -----------------------
def test_pedido_de_menu_texto_abre_lista(client, db, spy):
    tel = "5538000000008"
    _seed_user(db, tel, com_historico=True)
    r = client.post("/webhook", json=_payload_texto(tel, "menu", "p8"))
    assert r.status_code == 200
    assert "lista" in _kinds(spy)


# ----------------------- handoff via MENU_RECEPCAO -----------------------
def test_menu_recepcao_aciona_handoff(client, db, spy):
    tel = "5538000000009"
    _seed_user(db, tel, com_historico=True, bot_ativo=True)
    r = client.post("/webhook", json=_payload_interativo(tel, "MENU_RECEPCAO", "list_reply", "p9"))
    assert r.status_code == 200
    db.expire_all()
    u = db.query(Usuario).filter(Usuario.telefone == tel).first()
    assert u.bot_ativo is False  # handoff desativou o bot


# ----------- canônica de horário lê do banco via webhook (fix P0-4) -----------
def test_canonica_horario_le_do_banco_via_webhook(client, db, spy):
    tel = "5538000000010"
    _seed_user(db, tel, com_historico=True)
    for d in range(7):
        db.add(Horario(dia_semana=d, abertura=("07:07" if d == 0 else "09:00"),
                       fechamento="21:00", fechado=False))
    db.commit()
    r = client.post("/webhook", json=_payload_texto(tel, "qual o horario de funcionamento?", "p10"))
    assert r.status_code == 200
    assert "07:07" in _blob(spy)  # veio da tabela horarios, não do fallback hardcoded
