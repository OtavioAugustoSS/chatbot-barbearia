"""
Testes do Sprint B (P1 da auditoria de prontidão para produção):
- Guard determinístico do telefone do Fred (BR-002 / P1-7)
- Reabertura de conversa resolved/snoozed reativa o bot sem operador (P1-5)
- Cobertura de /admin/enviar e /admin/conversas/bulk (P1-9)
"""


def _payload_webhook(telefone, texto, message_id):
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "e1",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "55999990000", "phone_number_id": "000"},
                    "contacts": [{"profile": {"name": "Cliente"}, "wa_id": telefone}],
                    "messages": [{
                        "from": telefone, "id": message_id, "timestamp": "1700000000",
                        "type": "text", "text": {"body": texto},
                    }],
                },
                "field": "messages",
            }],
        }],
    }


# ----------------------------------------------------------------------------
# P1-7 — guard do telefone do Fred
# ----------------------------------------------------------------------------
def test_guard_fred_neutraliza_sem_pedido():
    from services.ai_service import AIService
    svc = AIService()
    dados = {"intencao": "tirar_duvida", "resposta_sugerida": "O telefone do Fred é (38) 99897-0661, pode ligar."}
    out = svc._validar_resposta(dados, mensagem_cliente="qual o horário de vocês?")
    assert "99897" not in out["resposta_sugerida"]


def test_guard_fred_permite_com_pedido_explicito():
    from services.ai_service import AIService
    svc = AIService()
    dados = {"intencao": "tirar_duvida", "resposta_sugerida": "Claro! O telefone do Fred é (38) 99897-0661."}
    out = svc._validar_resposta(dados, mensagem_cliente="me passa o telefone do Fred")
    assert "99897" in out["resposta_sugerida"]


def test_guard_fred_nao_afeta_resposta_normal():
    from services.ai_service import AIService
    svc = AIService()
    dados = {"intencao": "tirar_duvida", "resposta_sugerida": "Nosso corte sai por R$ 40. Como posso ajudar?"}
    out = svc._validar_resposta(dados, mensagem_cliente="qual o preço do corte?")
    assert out["resposta_sugerida"] == "Nosso corte sai por R$ 40. Como posso ajudar?"


# ----------------------------------------------------------------------------
# P1-5 — reabertura de conversa resolved reativa o bot
# ----------------------------------------------------------------------------
def test_reabertura_resolved_reativa_bot(client, db):
    from db.models import Usuario
    db.add(Usuario(
        telefone="5538900000001", nome_cliente="X",
        bot_ativo=False, atendente_id=None, status_conversa="resolved",
    ))
    db.commit()
    r = client.post("/webhook", json=_payload_webhook("5538900000001", "oi de novo", "reopen001"))
    assert r.status_code == 200
    db.expire_all()
    u = db.query(Usuario).filter_by(telefone="5538900000001").first()
    assert u.status_conversa == "open"
    assert u.bot_ativo is True


def test_reabertura_nao_rouba_conversa_de_operador(client, db, atendente_teste):
    """Se há operador ativo, reabrir NÃO reativa o bot (operador mantém o controle)."""
    from db.models import Usuario
    db.add(Usuario(
        telefone="5538900000009", nome_cliente="Y",
        bot_ativo=False, atendente_id=atendente_teste.id, status_conversa="resolved",
    ))
    db.commit()
    r = client.post("/webhook", json=_payload_webhook("5538900000009", "voltei", "reopen009"))
    assert r.status_code == 200
    db.expire_all()
    u = db.query(Usuario).filter_by(telefone="5538900000009").first()
    assert u.status_conversa == "open"
    assert u.bot_ativo is False  # operador mantém o controle


# ----------------------------------------------------------------------------
# P1-9 — cobertura de /admin/enviar e /admin/conversas/bulk
# ----------------------------------------------------------------------------
def test_enviar_mensagem_ok(client, auth_headers, db, atendente_teste):
    from db.models import Usuario
    db.add(Usuario(telefone="5538900000002", nome_cliente="Y", bot_ativo=False, atendente_id=atendente_teste.id, status_conversa="open"))
    db.commit()
    r = client.post("/admin/enviar/5538900000002", json={"texto": "Olá, tudo bem?"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_enviar_sem_auth_401(client):
    assert client.post("/admin/enviar/5538900000002", json={"texto": "oi"}).status_code == 401


def test_enviar_conversa_de_outro_403(client, auth_headers, db):
    from db.models import Usuario
    db.add(Usuario(telefone="5538900000003", nome_cliente="Z", bot_ativo=False, atendente_id=99999, status_conversa="open"))
    db.commit()
    r = client.post("/admin/enviar/5538900000003", json={"texto": "oi"}, headers=auth_headers)
    assert r.status_code == 403


def test_bulk_resolver_ok(client, auth_headers, db, atendente_teste):
    from db.models import Usuario
    db.add(Usuario(telefone="5538900000004", atendente_id=atendente_teste.id, status_conversa="open"))
    db.commit()
    r = client.post(
        "/admin/conversas/bulk",
        json={"telefones": ["5538900000004"], "acao": "resolver", "parametros": {}},
        headers=auth_headers,
    )
    assert r.status_code == 200
    db.expire_all()
    u = db.query(Usuario).filter_by(telefone="5538900000004").first()
    assert u.status_conversa == "resolved"
