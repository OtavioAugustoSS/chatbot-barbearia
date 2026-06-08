"""Fase A (hardening pré-avaliação) — cobertura dos endpoints admin secundários
que estavam sem teste, + os 2 fixes verificados (nome só-espaços, mídia vazia).
"""
import pytest

import services.whatsapp as wa_mod
from db.models import Usuario, Atendente, HistoricoConversa
from api.auth import hash_senha, criar_token


def _atendente(db, login, ativo=True):
    a = Atendente(nome="A " + login, usuario_login=login,
                  senha_hash=hash_senha("senha12345"), ativo=ativo)
    db.add(a); db.commit(); db.refresh(a)
    return a


def _inbox_items(payload):
    return payload if isinstance(payload, list) else payload.get("itens", payload.get("mentions", []))


# ============================== Atendentes ==============================
def test_criar_atendente_ok(client, auth_headers):
    r = client.post("/admin/atendentes",
                    json={"nome": "João", "usuario_login": "joao_novo", "senha": "senha12345"},
                    headers=auth_headers)
    assert r.status_code == 201 and r.json()["usuario_login"] == "joao_novo"


def test_criar_atendente_nome_so_espacos_422(client, auth_headers):
    # FIX: " " passava (min_length=1) e virava "" após strip. Agora 422.
    r = client.post("/admin/atendentes",
                    json={"nome": "   ", "usuario_login": "joao_ws", "senha": "senha12345"},
                    headers=auth_headers)
    assert r.status_code == 422


def test_criar_atendente_login_duplicado_409(client, db, auth_headers):
    _atendente(db, "repetido")
    r = client.post("/admin/atendentes",
                    json={"nome": "Outro", "usuario_login": "repetido", "senha": "senha12345"},
                    headers=auth_headers)
    assert r.status_code == 409


def test_desativar_a_si_mesmo_400(client, atendente_teste, auth_headers):
    r = client.patch(f"/admin/atendentes/{atendente_teste.id}/desativar", headers=auth_headers)
    assert r.status_code == 400


def test_ativar_atendente_idempotente(client, db, auth_headers):
    a = _atendente(db, "paraativar", ativo=False)
    assert client.patch(f"/admin/atendentes/{a.id}/ativar", headers=auth_headers).status_code == 200
    assert client.patch(f"/admin/atendentes/{a.id}/ativar", headers=auth_headers).status_code == 200


def test_listar_atendentes(client, auth_headers):
    r = client.get("/admin/atendentes", headers=auth_headers)
    assert r.status_code == 200 and isinstance(r.json(), list)


# ============================== Mentions ==============================
def test_mention_inbox_e_marcar_lida(client, db, atendente_teste, auth_headers):
    outro = _atendente(db, "mencionado")
    u = Usuario(telefone="5538555550001", nome_cliente="Cli", bot_ativo=True); db.add(u); db.commit()
    r = client.post(f"/admin/notas/{u.telefone}", json={"texto": "confere isso @mencionado"}, headers=auth_headers)
    assert r.status_code == 201
    h_outro = {"Authorization": f"Bearer {criar_token(outro)}"}
    r = client.get("/admin/mentions/inbox", headers=h_outro)
    assert r.status_code == 200
    items = _inbox_items(r.json())
    assert len(items) >= 1
    mid = items[0]["id"]
    assert client.patch(f"/admin/mentions/{mid}/marcar-lida", headers=h_outro).status_code == 200


def test_marcar_mention_de_outro_404(client, db, atendente_teste, auth_headers):
    outro = _atendente(db, "mencionado2")
    u = Usuario(telefone="5538555550002", nome_cliente="Cli", bot_ativo=True); db.add(u); db.commit()
    client.post(f"/admin/notas/{u.telefone}", json={"texto": "oi @mencionado2"}, headers=auth_headers)
    items = _inbox_items(client.get("/admin/mentions/inbox",
                                    headers={"Authorization": f"Bearer {criar_token(outro)}"}).json())
    mid = items[0]["id"]
    # atendente_teste tenta marcar mention que pertence ao 'outro' → rejeitado (403 ou 404)
    r = client.patch(f"/admin/mentions/{mid}/marcar-lida", headers=auth_headers)
    assert r.status_code in (403, 404)


# ============================== Views ==============================
def test_views_crud(client, auth_headers):
    r = client.post("/admin/views", json={"nome": "meus_urgentes", "criterios": {"filtro": "meus"}, "ordem": 0},
                    headers=auth_headers)
    assert r.status_code in (200, 201)
    vid = r.json()["id"]
    assert "meus_urgentes" in client.get("/admin/views", headers=auth_headers).text
    assert client.patch(f"/admin/views/{vid}", json={"ordem": 2}, headers=auth_headers).status_code == 200
    assert client.delete(f"/admin/views/{vid}", headers=auth_headers).status_code in (200, 204)


def test_views_nome_duplicado_409(client, auth_headers):
    client.post("/admin/views", json={"nome": "dup_view", "criterios": {}, "ordem": 0}, headers=auth_headers)
    r = client.post("/admin/views", json={"nome": "dup_view", "criterios": {}, "ordem": 0}, headers=auth_headers)
    assert r.status_code == 409


# ============================== enviar-midia ==============================
@pytest.fixture
def mock_midia(monkeypatch):
    monkeypatch.setattr(wa_mod.WhatsAppSender, "upload_midia_whatsapp", lambda self, *a, **k: "media123")
    monkeypatch.setattr(wa_mod.WhatsAppSender, "enviar_mensagem_midia", lambda self, *a, **k: (True, "wamid.midia"))


def _user_meu(db, tel, atendente_id):
    u = Usuario(telefone=tel, nome_cliente="Cli", bot_ativo=False, atendente_id=atendente_id)
    db.add(u); db.commit()
    return u


def test_enviar_midia_ok(client, db, atendente_teste, auth_headers, mock_midia):
    u = _user_meu(db, "5538555550010", atendente_teste.id)
    r = client.post(f"/admin/enviar-midia/{u.telefone}",
                    files={"file": ("foto.jpg", b"\xff\xd8\xff\xe0jpegbytes", "image/jpeg")},
                    data={"caption": "olha"}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["ok"] is True


def test_enviar_midia_vazia_400(client, db, atendente_teste, auth_headers, mock_midia):
    u = _user_meu(db, "5538555550011", atendente_teste.id)
    r = client.post(f"/admin/enviar-midia/{u.telefone}",
                    files={"file": ("vazio.jpg", b"", "image/jpeg")}, headers=auth_headers)
    assert r.status_code == 400  # FIX: arquivo vazio


def test_enviar_midia_mime_invalido_400(client, db, atendente_teste, auth_headers, mock_midia):
    u = _user_meu(db, "5538555550012", atendente_teste.id)
    r = client.post(f"/admin/enviar-midia/{u.telefone}",
                    files={"file": ("x.exe", b"data", "application/x-msdownload")}, headers=auth_headers)
    assert r.status_code == 400


def test_enviar_midia_usuario_inexistente_404(client, auth_headers, mock_midia):
    r = client.post("/admin/enviar-midia/5538000000999",
                    files={"file": ("foto.jpg", b"jpegdata", "image/jpeg")}, headers=auth_headers)
    assert r.status_code == 404


def test_enviar_midia_conversa_de_outro_403(client, db, atendente_teste, auth_headers, mock_midia):
    outro = _atendente(db, "donomidia")
    u = _user_meu(db, "5538555550013", outro.id)
    r = client.post(f"/admin/enviar-midia/{u.telefone}",
                    files={"file": ("foto.jpg", b"jpegdata", "image/jpeg")}, headers=auth_headers)
    assert r.status_code == 403


# ============================== tag ==============================
def test_tag_valida(client, db, auth_headers):
    u = Usuario(telefone="5538555550020", nome_cliente="Cli", bot_ativo=True); db.add(u); db.commit()
    assert client.patch(f"/admin/conversa/{u.telefone}/tag", json={"tag": "resolvido"}, headers=auth_headers).status_code == 200


def test_tag_invalida_400(client, db, auth_headers):
    u = Usuario(telefone="5538555550021", nome_cliente="Cli", bot_ativo=True); db.add(u); db.commit()
    assert client.patch(f"/admin/conversa/{u.telefone}/tag", json={"tag": "qualquer_coisa"}, headers=auth_headers).status_code == 400


def test_tag_inexistente_404(client, auth_headers):
    assert client.patch("/admin/conversa/5538000000999/tag", json={"tag": "resolvido"}, headers=auth_headers).status_code == 404


# ============================== cliente/info ==============================
def test_cliente_info_ok(client, db, auth_headers):
    u = Usuario(telefone="5538555550030", nome_cliente="Cli", bot_ativo=True); db.add(u); db.commit()
    assert client.get(f"/admin/cliente/{u.telefone}/info", headers=auth_headers).status_code == 200


def test_cliente_info_inexistente_404(client, auth_headers):
    assert client.get("/admin/cliente/5538000000999/info", headers=auth_headers).status_code == 404


# ============================== devolver silent ==============================
def test_devolver_silent_nao_envia(client, db, atendente_teste, auth_headers, monkeypatch):
    import api.admin as admin_mod
    enviados = []
    monkeypatch.setattr(admin_mod.whatsapp, "enviar_mensagem_texto",
                        lambda numero, texto: (enviados.append(1) or (True, "w")))
    u = Usuario(telefone="5538555550040", nome_cliente="Cli", bot_ativo=False,
                atendente_id=atendente_teste.id, aguardando_humano=False)
    db.add(u); db.commit()
    r = client.post(f"/admin/devolver/{u.telefone}?silent=true", headers=auth_headers)
    assert r.status_code == 200
    assert enviados == []  # modo silencioso não envia ao cliente


# ============================== status updates (webhook) ==============================
def _payload_status(wamid, status, telefone):
    return {"object": "whatsapp_business_account", "entry": [{"id": "e", "changes": [{"value": {
        "messaging_product": "whatsapp", "metadata": {"phone_number_id": "0"},
        "statuses": [{"id": wamid, "status": status, "recipient_id": telefone, "timestamp": "1700000000"}],
    }, "field": "messages"}]}]}


def test_status_update_marca_lida(client, db):
    u = Usuario(telefone="5538555550050", nome_cliente="Cli", bot_ativo=True); db.add(u); db.commit()
    db.add(HistoricoConversa(telefone_usuario=u.telefone, mensagem_cliente=None, resposta_bot="oi",
                             origem="bot", wamid="wamid.status1")); db.commit()
    r = client.post("/webhook", json=_payload_status("wamid.status1", "read", u.telefone))
    assert r.status_code == 200
    db.expire_all()
    h = db.query(HistoricoConversa).filter_by(wamid="wamid.status1").first()
    assert h.lida is True and h.entregue is True


def test_status_update_wamid_desconhecido_ignora(client, db):
    r = client.post("/webhook", json=_payload_status("wamid.naoexiste", "read", "5538x"))
    assert r.status_code == 200  # ignora silenciosamente, sem erro
