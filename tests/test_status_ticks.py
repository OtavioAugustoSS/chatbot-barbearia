"""
Rodada 2 — ciclo de vida de status de mensagem (ticks).

Cobre: delivered, failed, monotonicidade (out-of-order), múltiplos statuses num
payload, retry da race wamid, SSE mensagem_lida e wamid na resposta do /enviar.
"""
import pytest

from db.models import HistoricoConversa, Usuario
from tests.conftest import _montar_payload_webhook


def _payload_status(*status_items):
    """Payload Meta com um ou mais statuses: [(wamid, status, telefone), ...]."""
    return {"object": "whatsapp_business_account", "entry": [{"id": "e", "changes": [{"value": {
        "messaging_product": "whatsapp", "metadata": {"phone_number_id": "0"},
        "statuses": [
            {"id": w, "status": s, "recipient_id": t, "timestamp": "1700000000"}
            for (w, s, t) in status_items
        ],
    }, "field": "messages"}]}]}


def _criar_msg_bot(db, telefone, wamid, entregue=True, lida=None):
    u = db.query(Usuario).filter_by(telefone=telefone).first()
    if not u:
        db.add(Usuario(telefone=telefone, nome_cliente="Cli", bot_ativo=True))
        db.commit()
    h = HistoricoConversa(
        telefone_usuario=telefone, mensagem_cliente=None, resposta_bot="resp",
        origem="bot", entregue=entregue, lida=lida, wamid=wamid,
    )
    db.add(h)
    db.commit()
    db.refresh(h)
    return h


def test_delivered_marca_entregue_nao_lida(client, db):
    h = _criar_msg_bot(db, "5538555560001", "wamid.t.delivered")
    r = client.post("/webhook", json=_payload_status(("wamid.t.delivered", "delivered", h.telefone_usuario)))
    assert r.status_code == 200
    db.refresh(h)
    assert h.entregue is True
    assert h.lida is False


def test_failed_marca_nao_entregue(client, db):
    h = _criar_msg_bot(db, "5538555560002", "wamid.t.failed")
    r = client.post("/webhook", json=_payload_status(("wamid.t.failed", "failed", h.telefone_usuario)))
    assert r.status_code == 200
    db.refresh(h)
    assert h.entregue is False


def test_delivered_fora_de_ordem_nao_rebaixa_lida(client, db):
    """read chega primeiro; um delivered retransmitido NÃO pode voltar lida para False."""
    h = _criar_msg_bot(db, "5538555560003", "wamid.t.ooo")
    tel = h.telefone_usuario
    client.post("/webhook", json=_payload_status(("wamid.t.ooo", "read", tel)))
    client.post("/webhook", json=_payload_status(("wamid.t.ooo", "delivered", tel)))
    db.refresh(h)
    assert h.lida is True
    assert h.entregue is True


def test_failed_apos_read_ignorado(client, db):
    h = _criar_msg_bot(db, "5538555560004", "wamid.t.failread")
    tel = h.telefone_usuario
    client.post("/webhook", json=_payload_status(("wamid.t.failread", "read", tel)))
    client.post("/webhook", json=_payload_status(("wamid.t.failread", "failed", tel)))
    db.refresh(h)
    assert h.lida is True
    assert h.entregue is True


def test_multiplos_statuses_no_mesmo_payload(client, db):
    h1 = _criar_msg_bot(db, "5538555560005", "wamid.t.m1")
    h2 = _criar_msg_bot(db, "5538555560005", "wamid.t.m2")
    r = client.post("/webhook", json=_payload_status(
        ("wamid.t.m1", "delivered", "5538555560005"),
        ("wamid.t.m2", "read", "5538555560005"),
    ))
    assert r.status_code == 200
    db.refresh(h1)
    db.refresh(h2)
    assert (h1.entregue, h1.lida) == (True, False)
    assert (h2.entregue, h2.lida) == (True, True)


def test_status_nao_casa_linha_de_mensagem_do_cliente(client, db):
    """Guard D1: a coluna wamid também guarda o id de mensagens DO CLIENTE —
    um status simulado não pode flipar essas linhas (não têm tick)."""
    tel = "5538555560006"
    db.add(Usuario(telefone=tel, nome_cliente="Cli", bot_ativo=True))
    h = HistoricoConversa(telefone_usuario=tel, mensagem_cliente="oi", resposta_bot=None,
                          origem="cliente", wamid="wamid.t.cliente")
    db.add(h)
    db.commit()
    client.post("/webhook", json=_payload_status(("wamid.t.cliente", "read", tel)))
    db.refresh(h)
    assert h.lida is None  # intocada


def test_retry_encontra_wamid_gravado_depois(client, db, monkeypatch):
    """Race T4: o status chega antes do UPDATE do wamid — a segunda query
    (após o retry) deve encontrar. Simulado gravando o wamid durante o sleep."""
    import api.webhook as wh

    h = _criar_msg_bot(db, "5538555560007", None)  # ainda sem wamid

    def _sleep_grava_wamid(_segundos):
        h.wamid = "wamid.t.race"
        db.commit()

    monkeypatch.setattr(wh, "_STATUS_RETRY_DELAY_S", 0.001)
    monkeypatch.setattr(wh.time, "sleep", _sleep_grava_wamid)
    r = client.post("/webhook", json=_payload_status(("wamid.t.race", "read", h.telefone_usuario)))
    assert r.status_code == 200
    db.refresh(h)
    assert h.lida is True


def test_sse_mensagem_lida_publicado_com_failed(client, db, monkeypatch):
    import api.webhook as wh

    eventos = []
    monkeypatch.setattr(wh.notificador, "publicar", lambda ev: eventos.append(ev))
    h = _criar_msg_bot(db, "5538555560008", "wamid.t.sse")
    client.post("/webhook", json=_payload_status(("wamid.t.sse", "failed", h.telefone_usuario)))
    tipos = [(e["tipo"], e.get("status")) for e in eventos]
    assert ("mensagem_lida", "failed") in tipos


def test_enviar_retorna_wamid_e_sse_inclui(client, db, auth_headers, usuario_teste, atendente_teste, monkeypatch):
    import api.admin as adm

    eventos = []
    monkeypatch.setattr(adm.notificador, "publicar", lambda ev: eventos.append(ev))
    # atendente precisa ser dono da conversa
    usuario_teste.atendente_id = atendente_teste.id
    usuario_teste.bot_ativo = False
    db.commit()
    r = client.post(f"/admin/enviar/{usuario_teste.telefone}", headers=auth_headers,
                    json={"texto": "olá!"})
    assert r.status_code == 200
    body = r.json()
    assert body["wamid"] == "wamid.test123"  # mock do conftest
    novas = [e for e in eventos if e["tipo"] == "nova_mensagem"]
    assert novas and novas[0]["wamid"] == "wamid.test123"


def test_enviar_e_registrar_publica_wamid_no_sse(client, db, monkeypatch):
    """Mensagens do BOT (menus/canônicas) também carregam wamid no SSE."""
    import api.webhook as wh

    eventos = []
    monkeypatch.setattr(wh.notificador, "publicar", lambda ev: eventos.append(ev))
    tel = "5538555560009"
    payload = _montar_payload_webhook(tel, "oi", message_id="wamid.in.sse1")
    client.post("/webhook", json=payload)
    novas = [e for e in eventos if e["tipo"] == "nova_mensagem" and e["origem"] == "bot"]
    assert novas
    assert all(e.get("wamid") for e in novas)
