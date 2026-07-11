"""
Rodada 2 — extras: simulador de status (payloads), handoff no histórico,
aviso de mídia cria usuário, role no POST /atendentes.
"""
import pytest

from db.models import HistoricoConversa, Usuario
from tests.conftest import _montar_payload_webhook


# ------------------------------------------------ simulador dev (payloads)

def test_payload_status_do_simulador_compatibilidade():
    """O payload do /dev/api/status precisa ter o shape que o webhook processa."""
    from api.dev_router import _montar_payload_status

    body = _montar_payload_status("wamid.x", "read", "5538999990000")
    value = body["entry"][0]["changes"][0]["value"]
    st = value["statuses"][0]
    assert st["id"] == "wamid.x"
    assert st["status"] == "read"
    assert st["recipient_id"] == "5538999990000"


def test_payload_mensagem_do_simulador_usa_message_id():
    from api.dev_router import _montar_payload_meta

    body = _montar_payload_meta("5538999990000", "Cliente", "oi", "wamid.devsim.abc")
    msg = body["entry"][0]["changes"][0]["value"]["messages"][0]
    assert msg["id"] == "wamid.devsim.abc"
    assert msg["text"]["body"] == "oi"


def test_status_do_simulador_percorre_pipeline_real(client, db):
    """O mesmo shape que o /dev/api/status monta, postado no webhook, atualiza lida."""
    from api.dev_router import _montar_payload_status

    tel = "5538555590001"
    db.add(Usuario(telefone=tel, nome_cliente="Cli", bot_ativo=True))
    db.add(HistoricoConversa(telefone_usuario=tel, resposta_bot="resp", origem="bot",
                             entregue=True, wamid="wamid.dev.sim1"))
    db.commit()
    r = client.post("/webhook", json=_montar_payload_status("wamid.dev.sim1", "read", tel))
    assert r.status_code == 200
    h = db.query(HistoricoConversa).filter_by(wamid="wamid.dev.sim1").first()
    db.refresh(h)
    assert h.lida is True


# ------------------------------------------------ T8: handoff no histórico

def test_handoff_registra_resposta_no_historico(client, db):
    tel = "5538555590002"
    # segunda mensagem (primeiro contato já passou) para cair no gatilho de handoff
    client.post("/webhook", json=_montar_payload_webhook(tel, "oi", message_id="wamid.h.0"))
    client.post("/webhook", json=_montar_payload_webhook(tel, "MENU_RECEPCAO", message_id="wamid.h.1"))

    handoff = db.query(HistoricoConversa).filter(
        HistoricoConversa.telefone_usuario == tel,
        HistoricoConversa.intencao.in_(["handoff_recepcao", "recepcao_bot_only"]),
    ).first()
    assert handoff is not None
    assert handoff.resposta_bot  # a resposta do bot está visível no thread
    assert handoff.wamid  # e tem wamid (ticks funcionam)


# ------------------------------------------------ T8: aviso de mídia

def test_aviso_de_midia_cria_usuario_e_registra(client, db):
    tel = "5538555590003"
    payload = _montar_payload_webhook(tel, "x", message_id="wamid.mid.1")
    msg = payload["entry"][0]["changes"][0]["value"]["messages"][0]
    msg["type"] = "image"
    del msg["text"]

    r = client.post("/webhook", json=payload)
    assert r.status_code == 200
    assert db.query(Usuario).filter_by(telefone=tel).first() is not None
    aviso = db.query(HistoricoConversa).filter_by(
        telefone_usuario=tel, intencao="aviso_midia").first()
    assert aviso is not None


# ------------------------------------------------ B2: role no POST /atendentes

def test_criar_atendente_role_default_e_explicito(client, auth_headers):
    r1 = client.post("/admin/atendentes", headers=auth_headers,
                     json={"nome": "Comum", "usuario_login": "role_comum", "senha": "senha12345"})
    assert r1.status_code == 201
    assert r1.json()["role"] == "atendente"

    r2 = client.post("/admin/atendentes", headers=auth_headers,
                     json={"nome": "Chefe", "usuario_login": "role_chefe", "senha": "senha12345",
                           "role": "admin"})
    assert r2.status_code == 201
    assert r2.json()["role"] == "admin"


def test_criar_atendente_role_invalido_422(client, auth_headers):
    r = client.post("/admin/atendentes", headers=auth_headers,
                    json={"nome": "X", "usuario_login": "role_bad", "senha": "senha12345",
                          "role": "superuser"})
    assert r.status_code == 422
