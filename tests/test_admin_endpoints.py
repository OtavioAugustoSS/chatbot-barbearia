"""
Testes dos endpoints do dashboard admin (modo híbrido).
Cobre: login, auth, conversas, assumir, devolver, labels, notas.
"""
import pytest
from db.models import Usuario, Label, NotaInterna


# ============================================================
# Login
# ============================================================

def test_login_ok(client, atendente_teste):
    """Login com credenciais corretas retorna token e dados do atendente."""
    resp = client.post("/admin/login", json={"usuario_login": "teste", "senha": "senha123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["nome"] == "Atendente Teste"
    assert data["atendente_id"] == atendente_teste.id


def test_login_senha_errada(client, atendente_teste):
    """Login com senha errada retorna 401."""
    resp = client.post("/admin/login", json={"usuario_login": "teste", "senha": "errada"})
    assert resp.status_code == 401


def test_login_usuario_inexistente(client):
    """Login com usuário que não existe retorna 401."""
    resp = client.post("/admin/login", json={"usuario_login": "naoexiste", "senha": "qualquer"})
    assert resp.status_code == 401


# ============================================================
# A-01: GET /admin/conversas — autenticação
# ============================================================

def test_conversas_sem_token_retorna_401(client):
    """A-01: GET /admin/conversas sem Bearer token retorna 401."""
    resp = client.get("/admin/conversas")
    assert resp.status_code == 401


def test_conversas_com_token_retorna_200(client, auth_headers, atendente_teste):
    """GET /admin/conversas com token válido retorna 200 com envelope de paginação."""
    resp = client.get("/admin/conversas", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data


def test_conversas_lista_usuario(client, auth_headers, usuario_teste):
    """GET /admin/conversas lista usuário cadastrado no banco."""
    resp = client.get("/admin/conversas", headers=auth_headers)
    assert resp.status_code == 200
    telefones = [item["telefone"] for item in resp.json()["items"]]
    assert usuario_teste.telefone in telefones


# ============================================================
# Assumir / Devolver
# ============================================================

def test_assumir_conversa_livre(client, auth_headers, atendente_teste, usuario_teste, db):
    """POST /admin/assumir/{tel} em conversa sem atendente seta atendente_id."""
    resp = client.post(f"/admin/assumir/{usuario_teste.telefone}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["atendente_id"] == atendente_teste.id

    # Confirma no banco
    db.refresh(usuario_teste)
    assert usuario_teste.atendente_id == atendente_teste.id
    assert usuario_teste.bot_ativo is False


def test_assumir_ja_minha_conversa_retorna_400(client, auth_headers, atendente_teste, usuario_teste, db):
    """POST /admin/assumir quando já sou o dono retorna 400."""
    # Primeiro assume
    client.post(f"/admin/assumir/{usuario_teste.telefone}", headers=auth_headers)
    # Tenta assumir de novo
    resp = client.post(f"/admin/assumir/{usuario_teste.telefone}", headers=auth_headers)
    assert resp.status_code == 400


def test_devolver_reseta_estado(client, auth_headers, atendente_teste, usuario_teste, db):
    """POST /admin/devolver/{tel} libera conversa para o bot."""
    # Assume primeiro
    client.post(f"/admin/assumir/{usuario_teste.telefone}", headers=auth_headers)
    # Devolve
    resp = client.post(f"/admin/devolver/{usuario_teste.telefone}", headers=auth_headers)
    assert resp.status_code == 200

    db.refresh(usuario_teste)
    assert usuario_teste.atendente_id is None
    assert usuario_teste.bot_ativo is True


# ============================================================
# Labels
# ============================================================

def test_criar_label(client, auth_headers):
    """POST /admin/labels cria label com nome e cor válidos."""
    resp = client.post(
        "/admin/labels",
        json={"nome": "urgente", "cor": "#FF0000", "descricao": "Caso urgente"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["nome"] == "urgente"
    assert data["cor"] == "#FF0000"


def test_listar_labels(client, auth_headers, db):
    """GET /admin/labels retorna labels ativas."""
    db.add(Label(nome="vip", cor="#FFD700"))
    db.commit()

    resp = client.get("/admin/labels", headers=auth_headers)
    assert resp.status_code == 200
    nomes = [l["nome"] for l in resp.json()]
    assert "vip" in nomes


# ============================================================
# Notas internas
# ============================================================

def test_criar_nota(client, auth_headers, atendente_teste, usuario_teste):
    """POST /admin/notas/{tel} cria nota interna para a conversa."""
    resp = client.post(
        f"/admin/notas/{usuario_teste.telefone}",
        json={"texto": "Cliente solicitou prioridade."},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["ok"] is True
    assert "id" in data


def test_listar_notas(client, auth_headers, atendente_teste, usuario_teste, db):
    """GET /admin/notas/{tel} retorna envelope com notas da conversa."""
    db.add(NotaInterna(
        telefone_usuario=usuario_teste.telefone,
        atendente_id=atendente_teste.id,
        texto="Nota de teste",
    ))
    db.commit()

    resp = client.get(f"/admin/notas/{usuario_teste.telefone}", headers=auth_headers)
    assert resp.status_code == 200
    envelope = resp.json()
    assert "items" in envelope
    assert any(n["texto"] == "Nota de teste" for n in envelope["items"])
