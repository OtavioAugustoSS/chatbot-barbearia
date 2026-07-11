"""
Rodada 2 — read receipts (cliente vê ticks azuis) e contador de não-lidas.
"""
import pytest

from db.models import HistoricoConversa, Usuario
from tests.conftest import _montar_payload_webhook


@pytest.fixture()
def receipts(monkeypatch):
    """Spy sobre marcar_como_lida (substitui o mock inerte do conftest)."""
    import services.whatsapp as wa

    chamadas = []
    monkeypatch.setattr(
        wa.WhatsAppSender, "marcar_como_lida",
        lambda self, message_id, numero: chamadas.append((message_id, numero)) or True,
    )
    return chamadas


def test_bot_ativo_marca_mensagem_como_lida(client, db, receipts):
    tel = "5538555570001"
    client.post("/webhook", json=_montar_payload_webhook(tel, "oi", message_id="wamid.rr.1"))
    assert ("wamid.rr.1", tel) in receipts


def test_bot_inativo_nao_marca_no_recebimento(client, db, receipts):
    tel = "5538555570002"
    db.add(Usuario(telefone=tel, nome_cliente="Cli", bot_ativo=False,
                   aguardando_humano=True))
    db.commit()
    client.post("/webhook", json=_montar_payload_webhook(tel, "alguém aí?", message_id="wamid.rr.2"))
    assert not receipts  # quem marca é o atendente ao abrir a conversa


def test_wamid_do_cliente_persistido_com_bot_inativo(client, db):
    tel = "5538555570003"
    db.add(Usuario(telefone=tel, nome_cliente="Cli", bot_ativo=False, aguardando_humano=True))
    db.commit()
    client.post("/webhook", json=_montar_payload_webhook(tel, "olá", message_id="wamid.rr.3"))
    linha = db.query(HistoricoConversa).filter_by(telefone_usuario=tel, origem="cliente").first()
    assert linha is not None
    assert linha.wamid == "wamid.rr.3"


def test_marcar_lida_envia_receipt_e_zera_contador(client, db, auth_headers, atendente_teste, receipts):
    tel = "5538555570004"
    db.add(Usuario(telefone=tel, nome_cliente="Cli", bot_ativo=False, atendente_id=atendente_teste.id))
    db.add(HistoricoConversa(telefone_usuario=tel, mensagem_cliente="msg 1", origem="cliente",
                             wamid="wamid.rr.4a"))
    db.add(HistoricoConversa(telefone_usuario=tel, mensagem_cliente="msg 2", origem="cliente",
                             wamid="wamid.rr.4b"))
    db.commit()

    r = client.post(f"/admin/conversa/{tel}/marcar-lida", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["marcadas"] == 2
    # Receipt só do wamid MAIS RECENTE (WhatsApp cascateia os anteriores)
    assert receipts == [("wamid.rr.4b", tel)]

    user = db.query(Usuario).filter_by(telefone=tel).first()
    db.refresh(user)
    assert user.ultima_leitura_atendente_em is not None

    # Idempotente: segunda chamada não tem nada novo
    r2 = client.post(f"/admin/conversa/{tel}/marcar-lida", headers=auth_headers)
    assert r2.json()["marcadas"] == 0


def test_marcar_lida_de_conversa_de_outro_atendente_nao_marca(client, db, auth_headers_comum, atendente_teste):
    tel = "5538555570005"
    db.add(Usuario(telefone=tel, nome_cliente="Cli", bot_ativo=False, atendente_id=atendente_teste.id))
    db.add(HistoricoConversa(telefone_usuario=tel, mensagem_cliente="x", origem="cliente", wamid="w1"))
    db.commit()
    # atendente_comum não é o dono → não gera receipt nem zera
    r = client.post(f"/admin/conversa/{tel}/marcar-lida", headers=auth_headers_comum)
    assert r.status_code == 200
    assert r.json()["marcadas"] == 0


def test_conversas_retorna_mensagens_nao_lidas(client, db, auth_headers):
    tel = "5538555570006"
    db.add(Usuario(telefone=tel, nome_cliente="Cli", bot_ativo=False, aguardando_humano=True))
    for i in range(3):
        db.add(HistoricoConversa(telefone_usuario=tel, mensagem_cliente=f"m{i}", origem="cliente"))
    db.commit()

    r = client.get("/admin/conversas?estado=aguardando", headers=auth_headers)
    assert r.status_code == 200
    item = next(c for c in r.json()["items"] if c["telefone"] == tel)
    assert item["mensagens_nao_lidas"] == 3

    # Após marcar-lida, zera
    client.post(f"/admin/conversa/{tel}/marcar-lida", headers=auth_headers)
    r2 = client.get("/admin/conversas?estado=aguardando", headers=auth_headers)
    item2 = next(c for c in r2.json()["items"] if c["telefone"] == tel)
    assert item2["mensagens_nao_lidas"] == 0
