"""
Testes das melhorias do modo híbrido (H1-H8).

H1: POST /admin/refresh — renovação deslizante do JWT.
H2: RBAC — endpoints de gestão exigem role='admin'.
H3: notificador asyncio — publicação de thread sync entregue no event loop.
H5: bulk 'atribuir' valida destino existente e ativo.
H6: GC do rate limit de login.
"""
import threading
import time

import pytest

from api.auth import criar_token, hash_senha
from db.models import Atendente, Usuario


# ---------------------------------------------------------------- H2: RBAC

def test_atendente_comum_nao_cria_atendente(client, auth_headers_comum):
    resp = client.post("/admin/atendentes", headers=auth_headers_comum,
                       json={"nome": "X", "usuario_login": "novologin", "senha": "senha12345"})
    assert resp.status_code == 403


def test_atendente_comum_nao_desativa_atendente(client, auth_headers_comum, atendente_teste):
    resp = client.patch(f"/admin/atendentes/{atendente_teste.id}/desativar", headers=auth_headers_comum)
    assert resp.status_code == 403


def test_atendente_comum_nao_edita_horario(client, auth_headers_comum):
    resp = client.patch("/admin/horarios/0", headers=auth_headers_comum, json={"fechado": True})
    assert resp.status_code == 403


def test_atendente_comum_nao_apaga_cliente(client, auth_headers_comum, usuario_teste):
    resp = client.delete(f"/admin/cliente/{usuario_teste.telefone}", headers=auth_headers_comum)
    assert resp.status_code == 403


def test_admin_cria_atendente_normalmente(client, auth_headers):
    resp = client.post("/admin/atendentes", headers=auth_headers,
                       json={"nome": "Novo", "usuario_login": "novook", "senha": "senha12345"})
    assert resp.status_code == 201


def test_login_devolve_role(client, atendente_teste):
    resp = client.post("/admin/login", json={"usuario_login": "teste", "senha": "senha123"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


def test_atendente_comum_pode_atender_normalmente(client, auth_headers_comum, usuario_teste):
    """RBAC não pode atrapalhar o trabalho normal: assumir conversa continua livre."""
    resp = client.post(f"/admin/assumir/{usuario_teste.telefone}", headers=auth_headers_comum)
    assert resp.status_code == 200


# ---------------------------------------------------------------- H1: refresh

def test_refresh_devolve_token_novo_utilizavel(client, auth_headers):
    resp = client.post("/admin/refresh", headers=auth_headers)
    assert resp.status_code == 200
    novo = resp.json()["token"]
    assert novo
    # Token novo funciona em endpoint autenticado
    resp2 = client.get("/admin/atendentes", headers={"Authorization": f"Bearer {novo}"})
    assert resp2.status_code == 200


def test_refresh_sem_token_retorna_401(client):
    resp = client.post("/admin/refresh")
    assert resp.status_code == 401


def test_refresh_de_atendente_desativado_retorna_401(client, db, atendente_comum):
    headers = {"Authorization": f"Bearer {criar_token(atendente_comum)}"}
    atendente_comum.ativo = False
    db.commit()
    resp = client.post("/admin/refresh", headers=headers)
    assert resp.status_code == 401


def test_refresh_recusa_sessao_alem_do_teto(client, db, atendente_teste):
    from api.auth import SESSAO_MAX_HORAS

    sess_antiga = int(time.time()) - (SESSAO_MAX_HORAS * 3600 + 60)
    headers = {"Authorization": f"Bearer {criar_token(atendente_teste, sess=sess_antiga)}"}
    resp = client.post("/admin/refresh", headers=headers)
    assert resp.status_code == 401
    assert "teto" in resp.json()["detail"].lower() or "login" in resp.json()["detail"].lower()


# ---------------------------------------------------------------- H5: bulk atribuir

def test_bulk_atribuir_destino_inexistente_400(client, auth_headers, usuario_teste):
    resp = client.post("/admin/conversas/bulk", headers=auth_headers,
                       json={"acao": "atribuir", "telefones": [usuario_teste.telefone],
                             "parametros": {"atendente_id": 99999}})
    assert resp.status_code == 400


def test_bulk_atribuir_destino_inativo_400(client, db, auth_headers, usuario_teste):
    inativo = Atendente(nome="Inativo", usuario_login="inativo1", senha_hash=hash_senha("senha123"),
                        role="atendente", ativo=False)
    db.add(inativo)
    db.commit()
    db.refresh(inativo)
    resp = client.post("/admin/conversas/bulk", headers=auth_headers,
                       json={"acao": "atribuir", "telefones": [usuario_teste.telefone],
                             "parametros": {"atendente_id": inativo.id}})
    assert resp.status_code == 400


def test_bulk_atribuir_destino_valido_funciona(client, db, auth_headers, atendente_comum, usuario_teste):
    resp = client.post("/admin/conversas/bulk", headers=auth_headers,
                       json={"acao": "atribuir", "telefones": [usuario_teste.telefone],
                             "parametros": {"atendente_id": atendente_comum.id}})
    assert resp.status_code == 200
    assert usuario_teste.telefone in resp.json()["sucesso"]


# ---------------------------------------------------------------- H6: GC do rate limit

def test_login_rate_limit_gc_remove_ips_antigos():
    from api import auth

    auth._login_tentativas.clear()
    agora = time.time()
    for i in range(150):
        auth._login_tentativas[f"10.0.0.{i}"] = [agora - 3600]  # fora da janela
    auth.login_rate_limited("10.9.9.9")
    assert len(auth._login_tentativas) < 150
    auth._login_tentativas.clear()


# ---------------------------------------------------------------- H3: notificador asyncio

def test_notificador_entrega_de_thread_sync_para_loop():
    import asyncio

    from services.notificador import Notificador

    n = Notificador()
    recebidos = []

    async def cenario():
        n.set_loop(asyncio.get_running_loop())
        q = n.assinar()

        # Publica de uma THREAD (como as background tasks fazem em produção)
        t = threading.Thread(target=n.publicar, args=({"tipo": "teste", "x": 1},))
        t.start()
        t.join()

        evento = await asyncio.wait_for(q.get(), timeout=2)
        recebidos.append(evento)
        n.desassinar(q)

    asyncio.run(cenario())
    assert recebidos == [{"tipo": "teste", "x": 1}]


def test_notificador_sem_loop_e_noop_seguro():
    from services.notificador import Notificador

    n = Notificador()
    n.publicar({"tipo": "descartado"})  # não deve levantar


def test_notificador_stream_emite_evento_e_formato_sse():
    import asyncio

    from services.notificador import Notificador

    n = Notificador()
    linhas = []

    async def cenario():
        n.set_loop(asyncio.get_running_loop())
        q = n.assinar()
        n.publicar({"tipo": "ping"})
        gen = n.stream(q)
        linha = await asyncio.wait_for(gen.__anext__(), timeout=2)
        linhas.append(linha)
        await gen.aclose()

    asyncio.run(cenario())
    assert linhas[0].startswith("data: ")
    assert '"tipo": "ping"' in linhas[0]
    assert linhas[0].endswith("\n\n")
