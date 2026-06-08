"""
Testes do Sprint A (P0 da auditoria de prontidão para produção):
- LGPD: canônica "apagar meus dados" + DELETE /admin/cliente/{telefone}
- Horário: FAQ canônica lê da tabela `horarios` (fonte única) + endpoints admin
- Deploy: /health testa o banco
- Token: alerta distinto em 401 no envio à Meta
"""
import logging
import pytest


# ----------------------------------------------------------------------------
# P0-1 — LGPD
# ----------------------------------------------------------------------------
def test_canonica_apagar_dados_casa():
    from core.respostas_canonicas import detectar_resposta_canonica, RESPOSTA_APAGAR_DADOS
    assert detectar_resposta_canonica("quero apagar meus dados") == RESPOSTA_APAGAR_DADOS
    assert detectar_resposta_canonica("como funciona a LGPD de vocês?") == RESPOSTA_APAGAR_DADOS
    assert detectar_resposta_canonica("podem excluir meu cadastro?") == RESPOSTA_APAGAR_DADOS


def test_canonica_apagar_dados_nao_casa_conversa_normal():
    from core.respostas_canonicas import detectar_resposta_canonica, RESPOSTA_APAGAR_DADOS
    assert detectar_resposta_canonica("quero cortar o cabelo") != RESPOSTA_APAGAR_DADOS
    assert detectar_resposta_canonica("qual o preço do corte?") != RESPOSTA_APAGAR_DADOS


def test_boas_vindas_tem_nota_privacidade():
    from api.webhook import MENSAGEM_BOAS_VINDAS
    assert "apagar meus dados" in MENSAGEM_BOAS_VINDAS
    assert "🔒" in MENSAGEM_BOAS_VINDAS


def test_apagar_cliente_lgpd_apaga_tudo(client, auth_headers, db):
    from db.models import Usuario, HistoricoConversa
    db.add(Usuario(telefone="5538999998888", nome_cliente="Apagar Me", bot_ativo=True))
    db.add(HistoricoConversa(telefone_usuario="5538999998888", mensagem_cliente="oi", origem="cliente"))
    db.commit()
    r = client.delete("/admin/cliente/5538999998888", headers=auth_headers)
    assert r.status_code == 204
    assert db.query(Usuario).filter_by(telefone="5538999998888").first() is None
    assert db.query(HistoricoConversa).filter_by(telefone_usuario="5538999998888").count() == 0


def test_apagar_cliente_inexistente_404(client, auth_headers):
    assert client.delete("/admin/cliente/0000000", headers=auth_headers).status_code == 404


def test_apagar_cliente_sem_auth_401(client):
    assert client.delete("/admin/cliente/5538999998888").status_code == 401


# ----------------------------------------------------------------------------
# P0-4 — Horário fonte única (FAQ canônica lê do banco)
# ----------------------------------------------------------------------------
def test_horario_canonico_fallback_quando_banco_vazio(db):
    """Banco sem horários → reproduz exatamente o hardcode antigo (sem regressão)."""
    from core.respostas_canonicas import detectar_resposta_canonica
    r = detectar_resposta_canonica("qual o horário de funcionamento?", db)
    assert "14:00 às 21:00" in r  # valor do fallback _CORPO_HORARIO


def test_horario_canonico_reflete_banco(db):
    """Com horários no banco, a canônica responde os valores do banco, não o hardcode."""
    from core.respostas_canonicas import detectar_resposta_canonica
    from db.models import Horario
    db.add(Horario(dia_semana=0, abertura="10:00", fechamento="20:00", fechado=False))
    db.add(Horario(dia_semana=6, fechado=True))
    db.commit()
    r = detectar_resposta_canonica("qual o horário?", db)
    assert "Segunda: 10:00 às 20:00" in r
    assert "Domingo: fechado" in r
    assert "14:00 às 21:00" not in r  # não é mais o hardcode


def test_admin_horarios_get_e_patch(client, auth_headers, db):
    # PATCH cria/edita um dia
    r = client.patch("/admin/horarios/0", json={"abertura": "08:00", "fechamento": "19:00", "fechado": False}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["abertura"] == "08:00" and r.json()["fechamento"] == "19:00"
    # GET reflete
    g = client.get("/admin/horarios", headers=auth_headers)
    assert g.status_code == 200
    dias = {d["dia_semana"]: d for d in g.json()}
    assert dias[0]["abertura"] == "08:00"
    assert len(g.json()) == 7


def test_admin_horarios_validacao(client, auth_headers):
    # dia fora de 0-6 → 400
    assert client.patch("/admin/horarios/9", json={"fechado": True}, headers=auth_headers).status_code == 400
    # formato de hora inválido → 422 (Pydantic pattern)
    assert client.patch("/admin/horarios/1", json={"abertura": "8h"}, headers=auth_headers).status_code == 422


def test_admin_horarios_sem_auth_401(client):
    assert client.get("/admin/horarios").status_code == 401


def test_invalidar_cache_horarios():
    import services.ai_service as ai
    ai._cache_horarios["data"] = {"x": 1}
    ai._cache_horarios["expira_em"] = 9e9
    ai.invalidar_cache_horarios()
    assert ai._cache_horarios["data"] is None
    assert ai._cache_horarios["expira_em"] == 0.0


# ----------------------------------------------------------------------------
# P0-3 — /health
# ----------------------------------------------------------------------------
def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert "timestamp" in body


# ----------------------------------------------------------------------------
# P0-2 — alerta distinto em 401 (token vencido)
# ----------------------------------------------------------------------------
def test_whatsapp_401_loga_alerta_distinto(monkeypatch, caplog):
    import services.whatsapp as wa

    class _Resp401:
        status_code = 401
        text = '{"error":{"message":"token expired"}}'
        headers = {}
        def json(self):
            return {}

    monkeypatch.setattr(wa.requests, "post", lambda *a, **k: _Resp401())
    sender = wa.WhatsAppSender()
    with caplog.at_level(logging.ERROR):
        ok, wamid = sender._post_com_retry({"x": 1}, "5538999990000", "texto")
    assert ok is False and wamid is None
    assert "EXPIRADO" in caplog.text or "401" in caplog.text
