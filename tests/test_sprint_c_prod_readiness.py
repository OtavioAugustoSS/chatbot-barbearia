"""
Sprint C — testes de qualidade/escala (P2 + P1 restantes).

Cobre:
- P2-6: saudação pura com emoji ("oi 👋") cai no menu, não na IA.
- P2-7: verify-token do webhook sem fallback hardcoded.
- P1-6: cliente é notificado quando o lock estoura (não mais descarte silencioso).
- P2-3: script scripts/limpeza.py purga dedupe antigo (e respeita --dry-run).
- P2-4: dependência morta google-generativeai removida do requirements.txt.
"""
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock

import pytest

import api.webhook as webhook


# ---------------------------------------------------------------------------
# P2-6 — saudação pura com emoji
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("texto,esperado", [
    ("oi \U0001F44B", True),          # "oi 👋" — o caso do bug
    ("olá!", True),
    ("bom dia \U0001F600", True),     # "bom dia 😀"
    ("fala mano", True),
    ("\U0001F44B", False),            # só emoji, sem palavra de saudação
    ("oi tudo bem? quero agendar", False),
    ("quero cortar o cabelo amanha", False),
])
def test_saudacao_pura_com_emoji(texto, esperado):
    assert webhook._e_saudacao_pura(texto) is esperado


# ---------------------------------------------------------------------------
# P2-7 — verify-token sem fallback hardcoded
# ---------------------------------------------------------------------------
def test_verify_token_default_antigo_nao_autentica(client, monkeypatch):
    """O default removido ("barbearia_bot_123") não pode mais passar no handshake."""
    monkeypatch.setattr(webhook, "VERIFY_TOKEN", "segredo-real-do-dono")
    r = client.get("/webhook", params={
        "hub.mode": "subscribe",
        "hub.verify_token": "barbearia_bot_123",
        "hub.challenge": "42",
    })
    assert r.status_code == 403


def test_verify_token_correto_passa(client, monkeypatch):
    monkeypatch.setattr(webhook, "VERIFY_TOKEN", "segredo-real-do-dono")
    r = client.get("/webhook", params={
        "hub.mode": "subscribe",
        "hub.verify_token": "segredo-real-do-dono",
        "hub.challenge": "42",
    })
    assert r.status_code == 200
    assert r.text == "42"


def test_verify_token_vazio_rejeita_tudo(client, monkeypatch):
    """Sem WEBHOOK_VERIFY_TOKEN configurado, qualquer handshake é 403."""
    monkeypatch.setattr(webhook, "VERIFY_TOKEN", "")
    r = client.get("/webhook", params={
        "hub.mode": "subscribe",
        "hub.verify_token": "",
        "hub.challenge": "42",
    })
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# P1-6 — notifica cliente quando o lock estoura
# ---------------------------------------------------------------------------
def test_lock_timeout_notifica_cliente(monkeypatch):
    class _LockFalso:
        def acquire(self, timeout=None):
            return False  # simula starvation: lock nunca adquirido

        def release(self):
            pass

    monkeypatch.setattr(webhook, "_lock_do_telefone", lambda tel: _LockFalso())
    enviado = Mock(return_value=(True, "wamid.x"))
    monkeypatch.setattr(webhook.whatsapp, "enviar_mensagem_texto", enviado)

    webhook.tarefa_em_segundo_plano_ia("5538999990001", "oi")

    enviado.assert_called_once()
    numero, texto = enviado.call_args.args
    assert numero == "5538999990001"
    assert "anterior" in texto.lower() or "instante" in texto.lower()


# ---------------------------------------------------------------------------
# P2-3 — script de limpeza
# ---------------------------------------------------------------------------
def _semear_dedupe(db, idade_dias_lista):
    from db.models import MensagemProcessada
    agora = datetime.now(timezone.utc)
    for i, dias in enumerate(idade_dias_lista):
        db.add(MensagemProcessada(
            message_id=f"msg{i}",
            processada_em=agora - timedelta(days=dias),
        ))
    db.commit()
    return agora


def test_limpeza_purga_dedupe_antigo(db):
    import scripts.limpeza as limpeza
    from db.models import MensagemProcessada

    agora = _semear_dedupe(db, [5, 3, 0])  # 2 velhos, 1 recente
    limite = agora - timedelta(days=2)
    n = limpeza._purgar(db, MensagemProcessada, MensagemProcessada.processada_em, limite, dry_run=False)
    assert n == 2
    restantes = db.query(MensagemProcessada).all()
    assert len(restantes) == 1
    assert restantes[0].message_id == "msg2"


def test_limpeza_dry_run_nao_deleta(db):
    import scripts.limpeza as limpeza
    from db.models import MensagemProcessada

    agora = _semear_dedupe(db, [5])
    limite = agora - timedelta(days=2)
    n = limpeza._purgar(db, MensagemProcessada, MensagemProcessada.processada_em, limite, dry_run=True)
    assert n == 1
    assert db.query(MensagemProcessada).count() == 1  # dry-run não deleta


# ---------------------------------------------------------------------------
# P2-4 — dependência morta removida
# ---------------------------------------------------------------------------
def test_requirements_sem_google_generativeai():
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(raiz, "requirements.txt"), encoding="utf-8") as f:
        conteudo = f.read()
    assert "google-generativeai" not in conteudo
