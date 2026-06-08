"""Fase 3 — cobertura de endpoints admin core que estavam sem teste:
máquina de status, transferência, bulk (além de resolver), canned CRUD,
label edit/delete, nota edit/delete.
"""
import pytest
from datetime import datetime, timezone, timedelta

from db.models import Usuario, Atendente, Label
from api.auth import hash_senha


@pytest.fixture
def user_aberto(db):
    u = Usuario(telefone="5538777770001", nome_cliente="Cli", bot_ativo=True, status_conversa="open")
    db.add(u); db.commit()
    return u


def _outro_atendente(db, login="outro1"):
    a = Atendente(nome="Outro", usuario_login=login, senha_hash=hash_senha("senha12345"), ativo=True)
    db.add(a); db.commit(); db.refresh(a)
    return a


# ----------------------------- máquina de status -----------------------------
def test_status_open_para_resolved(client, db, auth_headers, user_aberto):
    r = client.patch(f"/admin/conversa/{user_aberto.telefone}/status",
                     json={"status": "resolved"}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["status"] == "resolved"
    db.expire_all()
    u = db.query(Usuario).filter_by(telefone=user_aberto.telefone).first()
    assert u.status_conversa == "resolved" and u.resolved_em is not None


def test_status_snoozed_exige_data_futura(client, db, auth_headers, user_aberto):
    tel = user_aberto.telefone
    r = client.patch(f"/admin/conversa/{tel}/status", json={"status": "snoozed"}, headers=auth_headers)
    assert r.status_code == 400  # falta snoozed_until
    passado = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    r = client.patch(f"/admin/conversa/{tel}/status",
                     json={"status": "snoozed", "snoozed_until": passado}, headers=auth_headers)
    assert r.status_code == 400  # data no passado
    futuro = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    r = client.patch(f"/admin/conversa/{tel}/status",
                     json={"status": "snoozed", "snoozed_until": futuro}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["status"] == "snoozed"


def test_status_reabrir_resolved_limpa_marcadores(client, db, auth_headers, user_aberto):
    tel = user_aberto.telefone
    client.patch(f"/admin/conversa/{tel}/status", json={"status": "resolved"}, headers=auth_headers)
    r = client.patch(f"/admin/conversa/{tel}/status", json={"status": "open"}, headers=auth_headers)
    assert r.status_code == 200
    db.expire_all()
    u = db.query(Usuario).filter_by(telefone=tel).first()
    assert u.status_conversa == "open" and u.resolved_em is None


def test_status_conversa_inexistente_404(client, auth_headers):
    r = client.patch("/admin/conversa/5538000000999/status",
                     json={"status": "open"}, headers=auth_headers)
    assert r.status_code == 404


# ------------------------------- transferência -------------------------------
def test_transferir_para_outro_atendente(client, db, atendente_teste, auth_headers):
    outro = _outro_atendente(db, "outrotransf")
    u = Usuario(telefone="5538777770002", nome_cliente="Cli", bot_ativo=False, atendente_id=atendente_teste.id)
    db.add(u); db.commit()
    r = client.post(f"/admin/conversa/{u.telefone}/atribuir",
                    json={"atendente_id": outro.id}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["atendente_id"] == outro.id
    db.expire_all()
    assert db.query(Usuario).filter_by(telefone=u.telefone).first().atendente_id == outro.id


def test_transferir_sem_ser_dono_403(client, db, atendente_teste, auth_headers):
    outro = _outro_atendente(db, "outrodono")
    u = Usuario(telefone="5538777770003", nome_cliente="Cli", bot_ativo=False, atendente_id=outro.id)
    db.add(u); db.commit()
    r = client.post(f"/admin/conversa/{u.telefone}/atribuir",
                    json={"atendente_id": atendente_teste.id}, headers=auth_headers)
    assert r.status_code == 403


# --------------------------- bulk (além de resolver) ---------------------------
def test_bulk_atribuir(client, db, atendente_teste, auth_headers):
    u1 = Usuario(telefone="5538777770010", nome_cliente="A", bot_ativo=True)
    u2 = Usuario(telefone="5538777770011", nome_cliente="B", bot_ativo=True)
    db.add_all([u1, u2]); db.commit()
    r = client.post("/admin/conversas/bulk",
                    json={"telefones": [u1.telefone, u2.telefone], "acao": "atribuir",
                          "parametros": {"atendente_id": atendente_teste.id}},
                    headers=auth_headers)
    assert r.status_code == 200
    db.expire_all()
    assert db.query(Usuario).filter_by(telefone=u1.telefone).first().atendente_id == atendente_teste.id


def test_bulk_snooze(client, db, auth_headers):
    u = Usuario(telefone="5538777770012", nome_cliente="C", bot_ativo=True)
    db.add(u); db.commit()
    futuro = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
    r = client.post("/admin/conversas/bulk",
                    json={"telefones": [u.telefone], "acao": "snooze",
                          "parametros": {"snoozed_until": futuro}},
                    headers=auth_headers)
    assert r.status_code == 200
    db.expire_all()
    assert db.query(Usuario).filter_by(telefone=u.telefone).first().status_conversa == "snoozed"


def test_bulk_label_add(client, db, auth_headers):
    lab = Label(nome="vip", cor="#ff0000"); db.add(lab); db.commit(); db.refresh(lab)
    u = Usuario(telefone="5538777770013", nome_cliente="D", bot_ativo=True); db.add(u); db.commit()
    r = client.post("/admin/conversas/bulk",
                    json={"telefones": [u.telefone], "acao": "label_add",
                          "parametros": {"label_id": lab.id}},
                    headers=auth_headers)
    assert r.status_code == 200


# -------------------------------- canned CRUD --------------------------------
def test_canned_crud(client, auth_headers):
    r = client.post("/admin/canned", json={"atalho": "/oi", "texto": "Olá!", "escopo": "pessoal"},
                    headers=auth_headers)
    assert r.status_code == 201
    cid = r.json()["id"]
    r = client.get("/admin/canned", headers=auth_headers)
    assert r.status_code == 200 and "/oi" in r.text
    r = client.patch(f"/admin/canned/{cid}", json={"texto": "Olá, tudo bem?"}, headers=auth_headers)
    assert r.status_code == 200
    r = client.delete(f"/admin/canned/{cid}", headers=auth_headers)
    assert r.status_code == 204


# ----------------------------- label edit/delete -----------------------------
def test_label_edit_delete(client, db, auth_headers):
    lab = Label(nome="urgente", cor="#00ff00"); db.add(lab); db.commit(); db.refresh(lab)
    r = client.patch(f"/admin/labels/{lab.id}", json={"cor": "#0000ff"}, headers=auth_headers)
    assert r.status_code == 200
    r = client.delete(f"/admin/labels/{lab.id}", headers=auth_headers)
    assert r.status_code == 204


# ------------------------------ nota edit/delete ------------------------------
def test_nota_edit_delete(client, db, auth_headers):
    u = Usuario(telefone="5538777770020", nome_cliente="E", bot_ativo=True); db.add(u); db.commit()
    r = client.post(f"/admin/notas/{u.telefone}", json={"texto": "nota original"}, headers=auth_headers)
    assert r.status_code == 201
    nid = r.json()["id"]
    r = client.patch(f"/admin/notas/{nid}", json={"texto": "nota editada"}, headers=auth_headers)
    assert r.status_code == 200
    r = client.delete(f"/admin/notas/{nid}", headers=auth_headers)
    assert r.status_code == 204
