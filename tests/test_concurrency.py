"""
Testes de concorrência na lógica de assumir conversa.
H-03/C-01: dois atendentes não podem assumir a mesma conversa.

Como TestClient é síncrono, simulamos a corrida em sequência:
  1. Primeiro request (200): atendente_id é setado.
  2. Segundo request (409): UPDATE condicional (WHERE atendente_id IS NULL) retorna 0 afetadas.

A atomicidade real (dois SELECTs simultâneos vendo atendente_id=NULL) é coberta pela
lógica `afetadas==0` em admin.py (linha ~476) — o UPDATE condicional garante que
apenas um processo vence mesmo com race condition no nível do banco.
"""
import pytest
from db.models import Usuario, Atendente
from api.auth import hash_senha, criar_token


@pytest.fixture()
def segundo_atendente(db):
    """Segundo atendente para simular dois usuários concorrentes."""
    atendente = Atendente(
        nome="Segundo Atendente",
        usuario_login="segundo",
        senha_hash=hash_senha("senha456"),
        ativo=True,
    )
    db.add(atendente)
    db.commit()
    db.refresh(atendente)
    return atendente


@pytest.fixture()
def segundo_token(segundo_atendente):
    return criar_token(segundo_atendente)


@pytest.fixture()
def segundo_auth(segundo_token):
    return {"Authorization": f"Bearer {segundo_token}"}


def test_assumir_sequencial_primeiro_ok_segundo_409(
    client, auth_headers, segundo_auth, usuario_teste
):
    """C-01: primeiro atendente assume (200); segundo recebe 409."""
    tel = usuario_teste.telefone

    # Primeiro atendente assume
    resp1 = client.post(f"/admin/assumir/{tel}", headers=auth_headers)
    assert resp1.status_code == 200, f"Esperado 200, recebido {resp1.status_code}: {resp1.text}"

    # Segundo atendente tenta assumir a mesma conversa
    resp2 = client.post(f"/admin/assumir/{tel}", headers=segundo_auth)
    assert resp2.status_code == 409, f"Esperado 409, recebido {resp2.status_code}: {resp2.text}"


def test_forcando_path_afetadas_zero(client, auth_headers, segundo_auth, db, usuario_teste):
    """
    Força o path de corrida atômica: simula que o primeiro atendente assumiu
    diretamente no banco (sem passar pelo endpoint), depois o segundo tenta assumir.
    O UPDATE condicional (WHERE atendente_id IS NULL) deve retornar 0 afetadas → 409.
    """
    from datetime import datetime, timezone

    tel = usuario_teste.telefone

    # Simula que outro atendente já setou atendente_id diretamente no banco
    # (equivale a vencer a corrida por fora do endpoint)
    db.query(Usuario).filter(Usuario.telefone == tel).update(
        {"atendente_id": 9999},  # ID fictício de outro atendente
        synchronize_session=False,
    )
    db.commit()

    # Segundo atendente tenta assumir via endpoint
    resp = client.post(f"/admin/assumir/{tel}", headers=segundo_auth)
    # Deve receber 409 — a conversa já tem dono
    assert resp.status_code == 409, f"Esperado 409, recebido {resp.status_code}: {resp.text}"


def test_devolver_e_reassumir_funciona(client, auth_headers, segundo_auth, usuario_teste):
    """
    Fluxo completo: assume → devolve → segundo atendente consegue assumir.
    Verifica que devolver libera o lock de atendente_id corretamente.
    """
    tel = usuario_teste.telefone

    # Primeiro assume
    resp = client.post(f"/admin/assumir/{tel}", headers=auth_headers)
    assert resp.status_code == 200

    # Devolve
    resp = client.post(f"/admin/devolver/{tel}", headers=auth_headers)
    assert resp.status_code == 200

    # Segundo atendente agora consegue assumir
    resp = client.post(f"/admin/assumir/{tel}", headers=segundo_auth)
    assert resp.status_code == 200, f"Esperado 200 após devolver, recebido {resp.status_code}: {resp.text}"
