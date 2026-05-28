"""
Casos [AUTO] do TEST_PLAN não cobertos pelos testes principais.
Referência: .claude/wiki/qa/TEST_PLAN.md

Cobre: A-02, A-04, H-05, V-04, V-06, C-05, R-04, normalização de texto.
"""
import os
import time
import json
import pytest
from datetime import datetime, timedelta, timezone

from db.models import Atendente, Usuario, HistoricoConversa
from api.auth import hash_senha, criar_token
from tests.conftest import _montar_payload_webhook


# ============================================================
# A-02: token expirado retorna 401
# ============================================================

def test_token_expirado_retorna_401(client, atendente_teste):
    """A-02: JWT expirado deve retornar 401, não 200."""
    from jose import jwt as _jwt
    payload = {
        "sub": str(atendente_teste.id),
        "login": atendente_teste.usuario_login,
        "nome": atendente_teste.nome,
        # exp no passado
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        "iat": datetime.now(timezone.utc) - timedelta(minutes=2),
    }
    token_expirado = _jwt.encode(payload, os.environ["JWT_SECRET"], algorithm="HS256")
    resp = client.get("/admin/conversas", headers={"Authorization": f"Bearer {token_expirado}"})
    assert resp.status_code == 401


# ============================================================
# A-04: rate limit de login (5 tentativas / 60s)
# ============================================================

def test_login_rate_limit_apos_5_tentativas(client, atendente_teste, monkeypatch):
    """A-04: após 5 tentativas erradas do mesmo IP, 6ª retorna 429."""
    from api import auth as _auth_mod
    # Limpa o dict de tentativas para o IP de teste
    _auth_mod._login_tentativas.clear()

    for i in range(5):
        resp = client.post("/admin/login", json={"usuario_login": "teste", "senha": "errada"})
        assert resp.status_code == 401

    # 6ª tentativa deve bater no rate limit
    resp = client.post("/admin/login", json={"usuario_login": "teste", "senha": "errada"})
    assert resp.status_code == 429

    _auth_mod._login_tentativas.clear()


# ============================================================
# H-05: atendente B não pode devolver conversa de A
# ============================================================

def test_devolver_conversa_de_outro_atendente_falha(client, auth_headers, db):
    """H-05: atendente B não consegue devolver conversa assumida por atendente A."""
    # Cria segundo atendente
    atendente_b = Atendente(
        nome="Atendente B",
        usuario_login="atendb",
        senha_hash=hash_senha("senha999"),
        ativo=True,
    )
    db.add(atendente_b)
    db.commit()
    db.refresh(atendente_b)
    token_b = criar_token(atendente_b)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Cria usuário e atendente A assume
    user = Usuario(telefone="5538900010001", nome_cliente="Cliente H05", bot_ativo=True)
    db.add(user)
    db.commit()

    # A assume
    resp = client.post(f"/admin/assumir/{user.telefone}", headers=auth_headers)
    assert resp.status_code == 200

    # B tenta devolver — deve falhar (UPDATE condicional WHERE atendente_id=B.id → 0 afetadas)
    resp_b = client.post(f"/admin/devolver/{user.telefone}", headers=headers_b)
    # Espera 404 (cliente não encontrado como sendo de B) ou 400/403
    assert resp_b.status_code in (400, 403, 404, 409)


# ============================================================
# V-04: HMAC webhook — sem assinatura quando META_APP_SECRET vazio = aceita (dev mode)
# ============================================================

def test_webhook_sem_assinatura_aceita_em_dev_mode(client, db):
    """V-04 (parte dev): sem META_APP_SECRET, webhook aceita POST sem assinatura."""
    # META_APP_SECRET está vazio (setado no conftest)
    payload = _montar_payload_webhook("5538911100001", "oi", message_id="v04-001")
    resp = client.post("/webhook", json=payload)
    assert resp.status_code == 200


def test_webhook_com_assinatura_invalida_quando_secret_setado(client, monkeypatch):
    """V-04 (parte prod): com META_APP_SECRET setado, assinatura inválida → 403."""
    import api.webhook as _wh_mod
    monkeypatch.setattr(_wh_mod, "META_APP_SECRET", b"secret-de-teste")

    payload = _montar_payload_webhook("5538911100002", "oi", message_id="v04-002")
    resp = client.post(
        "/webhook",
        json=payload,
        headers={"X-Hub-Signature-256": "sha256=invalida"},
    )
    assert resp.status_code == 403


# ============================================================
# V-06: endpoints não vazam senha_hash nem JWT_SECRET
# ============================================================

def test_login_nao_vaza_senha_hash(client, atendente_teste):
    """V-06: resposta de login não inclui senha_hash."""
    resp = client.post("/admin/login", json={"usuario_login": "teste", "senha": "senha123"})
    assert resp.status_code == 200
    body = resp.text
    assert "senha_hash" not in body
    assert "$2b$" not in body  # prefixo bcrypt


def test_listar_atendentes_nao_vaza_senha_hash(client, auth_headers, atendente_teste):
    """V-06: GET /admin/atendentes não inclui senha_hash nos dados retornados."""
    resp = client.get("/admin/atendentes", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.text
    assert "senha_hash" not in body
    assert "$2b$" not in body


def test_conversas_nao_vaza_jwt_secret(client, auth_headers, atendente_teste):
    """V-06: resposta de /admin/conversas não contém JWT_SECRET."""
    resp = client.get("/admin/conversas", headers=auth_headers)
    assert resp.status_code == 200
    assert os.environ["JWT_SECRET"] not in resp.text


# ============================================================
# C-05: lock de telefone com timeout (não starvation)
# ============================================================

def test_lock_timeout_nao_bloqueia_apos_timeout(monkeypatch):
    """C-05: _lock_do_telefone retorna lock; acquire com timeout=0 em lock já ocupado retorna False."""
    import threading
    from api.webhook import _lock_do_telefone, _locks_por_telefone

    tel = "5538922200099"
    lock = _lock_do_telefone(tel)
    lock.acquire()
    try:
        # Outro acquire com timeout=0 deve falhar (retorna False), não bloquear
        resultado = lock.acquire(timeout=0)
        assert resultado is False
    finally:
        lock.release()
        _locks_por_telefone.pop(tel, None)


# ============================================================
# R-04: exceção no background task não derruba o processo
# ============================================================

def test_background_task_excecao_capturada(client, db, monkeypatch):
    """R-04: exceção em tarefa_em_segundo_plano_ia é capturada na raiz (ADR-010)."""
    import api.webhook as _wh_mod

    explosoes = []

    def _processar_que_explode(telefone, texto):
        explosoes.append(telefone)
        raise RuntimeError("Exceção simulada R-04")

    monkeypatch.setattr(_wh_mod, "_processar_mensagem", _processar_que_explode)

    tel = "5538900020001"
    user = Usuario(telefone=tel, nome_cliente="R04 Test", bot_ativo=True)
    db.add(user)
    db.commit()

    payload = _montar_payload_webhook(tel, "teste r04", message_id="r04-001")
    # TestClient é síncrono: background task roda inline
    resp = client.post("/webhook", json=payload)
    assert resp.status_code == 200  # Meta sempre recebe 200
    assert tel in explosoes  # confirma que chegou na função


# ============================================================
# Normalização de texto (_normalizar_texto_envio)
# ============================================================

def test_normalizar_texto_converte_br_para_newline():
    """BR-003: <br> é convertido para \n antes do envio."""
    from api.webhook import _normalizar_texto_envio
    assert _normalizar_texto_envio("Linha 1<br>Linha 2") == "Linha 1\nLinha 2"
    assert _normalizar_texto_envio("Linha 1<BR>Linha 2") == "Linha 1\nLinha 2"
    assert _normalizar_texto_envio("Linha 1<br/>Linha 2") == "Linha 1\nLinha 2"


def test_normalizar_texto_colapsa_multiplas_quebras():
    """BR-003: 3+ quebras consecutivas colapsadas em 2."""
    from api.webhook import _normalizar_texto_envio
    resultado = _normalizar_texto_envio("a<br><br><br><br>b")
    assert resultado == "a\n\nb"


def test_normalizar_texto_strip():
    """BR-003: strip nas pontas."""
    from api.webhook import _normalizar_texto_envio
    assert _normalizar_texto_envio("  texto  ") == "texto"
    assert _normalizar_texto_envio("<br>texto<br>") == "texto"


# ============================================================
# FAQ canônica — gap identificado (possível bug)
# ============================================================

# ============================================================
# SEC-01: gate de boot _exigir_meta_secret (função pura)
# ============================================================

def test_exigir_meta_secret_levanta_sem_secret_e_sem_flag():
    """SEC-01: sem META_APP_SECRET e sem ALLOW_UNSIGNED_WEBHOOK=1 → RuntimeError."""
    # Importa a função pura diretamente — não importa main.py completo
    import importlib, types
    # A função é definida em main.py mas podemos testá-la via importação dinâmica
    # APENAS da função, depois que main.py já foi importado pelo conftest via app fixture.
    # O conftest já importou main — buscamos do módulo cacheado.
    import sys
    main_mod = sys.modules.get("main")
    if main_mod is None:
        pytest.skip("main não importado ainda")
    fn = main_mod._exigir_meta_secret
    with pytest.raises(RuntimeError, match="META_APP_SECRET"):
        fn("", "")


def test_exigir_meta_secret_levanta_com_flag_errada():
    """SEC-01: ALLOW_UNSIGNED_WEBHOOK != '1' ainda levanta RuntimeError."""
    import sys
    main_mod = sys.modules.get("main")
    if main_mod is None:
        pytest.skip("main não importado ainda")
    fn = main_mod._exigir_meta_secret
    with pytest.raises(RuntimeError):
        fn("", "true")  # só "1" é aceito
    with pytest.raises(RuntimeError):
        fn("", "yes")


def test_exigir_meta_secret_nao_levanta_com_flag_dev():
    """SEC-01: ALLOW_UNSIGNED_WEBHOOK=1 permite boot sem secret (retorna None)."""
    import sys
    main_mod = sys.modules.get("main")
    if main_mod is None:
        pytest.skip("main não importado ainda")
    fn = main_mod._exigir_meta_secret
    result = fn("", "1")  # deve retornar None, não levantar
    assert result is None


def test_exigir_meta_secret_nao_levanta_com_secret_presente():
    """SEC-01: META_APP_SECRET definido → nenhuma verificação de flag necessária."""
    import sys
    main_mod = sys.modules.get("main")
    if main_mod is None:
        pytest.skip("main não importado ainda")
    fn = main_mod._exigir_meta_secret
    result = fn("meu-secret-real", "")
    assert result is None


def test_faq_gap_como_faco_para_agendar():
    """
    BUG-01 (corrigido): 'como faço para agendar?' agora casa com regex de agendamento.
    Frase natural PT-BR adicionada em core/respostas_canonicas.py.
    """
    from core.respostas_canonicas import detectar_resposta_canonica
    resp = detectar_resposta_canonica("como faço para agendar?")
    assert resp is not None, (
        "BUG-01 REGREDIU: 'como faço para agendar?' não retornou resposta canônica — "
        "verifique se o regex de agendamento ainda contém o padrão 'como faço para agendar'."
    )
