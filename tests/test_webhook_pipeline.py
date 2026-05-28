"""
Testes do pipeline de processamento de mensagens do webhook.
Cobre: dedup, rate limit, saudação pura, FAQ canônica, handoff por falha de IA.
"""
import json
import pytest
from db.models import MensagemProcessada, Usuario, HistoricoConversa
from tests.conftest import _montar_payload_webhook


# ============================================================
# C-04: Deduplicação por message_id
# ============================================================

def test_dedup_mesma_message_id_processa_uma_vez(client, db):
    """C-04: POST /webhook com mesmo message_id enviado 2x processa apenas 1x."""
    payload = _montar_payload_webhook("5538911110001", "oi", message_id="dedup-test-001")

    # Primeiro envio
    resp1 = client.post("/webhook", json=payload)
    assert resp1.status_code == 200

    # Segundo envio com mesmo message_id
    resp2 = client.post("/webhook", json=payload)
    assert resp2.status_code == 200

    # Deve haver exatamente 1 registro de dedupe
    registros = db.query(MensagemProcessada).filter(
        MensagemProcessada.message_id == "dedup-test-001"
    ).count()
    assert registros == 1


def test_ja_processada_true_para_id_existente(db):
    """_ja_processada retorna True para message_id já registrado."""
    from api.webhook import _ja_processada
    db.add(MensagemProcessada(message_id="existente-123"))
    db.commit()
    assert _ja_processada(db, "existente-123") is True


def test_ja_processada_false_para_novo_id(db):
    """_ja_processada retorna False (e registra) para message_id novo."""
    from api.webhook import _ja_processada
    resultado = _ja_processada(db, "novo-456")
    assert resultado is False
    # Deve ter sido registrado
    assert db.query(MensagemProcessada).filter(
        MensagemProcessada.message_id == "novo-456"
    ).count() == 1


# ============================================================
# Rate limit
# ============================================================

def test_rate_limit_drop_apos_10_mensagens(monkeypatch):
    """Rate limit descarta mensagens além do limite de 10/min para o mesmo telefone."""
    import time
    from api.webhook import _janela_rate_limit, _excedeu_rate_limit, RATE_LIMIT_MSGS_POR_MINUTO

    tel = "5538922229999"
    # Limpa estado para este telefone
    _janela_rate_limit.pop(tel, None)

    agora = time.time()
    monkeypatch.setattr(time, "time", lambda: agora)

    # Enche a janela
    for _ in range(RATE_LIMIT_MSGS_POR_MINUTO):
        resultado = _excedeu_rate_limit(tel)
        assert resultado is False, "As primeiras N mensagens não devem exceder o limite"

    # Próxima deve exceder
    assert _excedeu_rate_limit(tel) is True

    # Cleanup
    _janela_rate_limit.pop(tel, None)


# ============================================================
# Saudação pura → menu sem IA
# ============================================================

def test_e_saudacao_pura_detecta_oi():
    """_e_saudacao_pura deve identificar 'oi' como saudação."""
    from api.webhook import _e_saudacao_pura
    assert _e_saudacao_pura("oi") is True
    assert _e_saudacao_pura("Olá!") is True
    assert _e_saudacao_pura("bom dia") is True
    assert _e_saudacao_pura("eai mano") is True


def test_e_saudacao_pura_nao_detecta_pergunta():
    """_e_saudacao_pura não deve casar mensagens com intenção."""
    from api.webhook import _e_saudacao_pura
    assert _e_saudacao_pura("oi qual o horário?") is False
    assert _e_saudacao_pura("quero cortar o cabelo") is False


def test_saudacao_pura_nao_chama_ia(client, db, monkeypatch):
    """Saudação pura com histórico existente retorna menu sem chamar _chamar_llm."""
    chamadas_ia = []

    import services.ai_service as _ai_mod
    monkeypatch.setattr(
        _ai_mod.AIService,
        "_chamar_llm",
        lambda self, messages: chamadas_ia.append(messages) or (_ for _ in ()).throw(AssertionError("IA não deve ser chamada")),
    )

    tel = "5538933330001"
    # Cria usuario com histórico para não cair no fluxo de "primeiro contato"
    user = Usuario(telefone=tel, nome_cliente="Carlos", bot_ativo=True)
    db.add(user)
    db.commit()
    hist = HistoricoConversa(
        telefone_usuario=tel,
        mensagem_cliente="anterior",
        resposta_bot="Resposta anterior",
        origem="bot",
    )
    db.add(hist)
    db.commit()

    payload = _montar_payload_webhook(tel, "oi", message_id="sauda-001", nome="Carlos")
    resp = client.post("/webhook", json=payload)
    assert resp.status_code == 200
    assert len(chamadas_ia) == 0


# ============================================================
# FAQ canônica determinística
# ============================================================

def test_detectar_resposta_canonica_horario():
    """FAQ canônica detecta perguntas de horário."""
    from core.respostas_canonicas import detectar_resposta_canonica
    resp = detectar_resposta_canonica("qual o horário de vocês?")
    assert resp is not None
    assert "horário" in resp.lower() or "segunda" in resp.lower()


def test_detectar_resposta_canonica_endereco():
    """FAQ canônica detecta perguntas de endereço."""
    from core.respostas_canonicas import detectar_resposta_canonica
    resp = detectar_resposta_canonica("onde fica a barbearia?")
    assert resp is not None
    assert "Unaí" in resp or "endereço" in resp.lower() or "Zaida" in resp


def test_detectar_resposta_canonica_agendamento():
    """FAQ canônica detecta perguntas de agendamento com frases do padrão regex."""
    from core.respostas_canonicas import detectar_resposta_canonica
    # "quero agendar" casa com o padrão de agendamento
    resp = detectar_resposta_canonica("quero agendar")
    assert resp is not None
    assert "AppBarber" in resp or "appbarber" in resp.lower() or "app" in resp.lower()

    # "como agendar" também deve casar (padrão: como\s+(eu\s+)?agend...)
    resp2 = detectar_resposta_canonica("como agendar o corte?")
    assert resp2 is not None


def test_detectar_resposta_canonica_none_para_desconhecida():
    """FAQ canônica retorna None para pergunta fora do escopo."""
    from core.respostas_canonicas import detectar_resposta_canonica
    resp = detectar_resposta_canonica("qual o significado da vida?")
    assert resp is None


# ============================================================
# H-02: Handoff por transbordo_falha (JSON inválido da IA)
# ============================================================

def test_handoff_transbordo_falha_json_invalido(client, db, monkeypatch):
    """H-02: quando a IA retorna JSON inválido, intencao=transbordo_falha é acionada.
    Em modo bot_only: bot continua ativo e envia mensagem de erro (não há atendente).
    """
    import services.ai_service as _ai_mod

    class _FakeChoiceInvalido:
        finish_reason = "stop"  # completion.choices[0].finish_reason

        class _FakeMsg:
            content = "isso não é json válido {{{"
        message = _FakeMsg()

    class _FakeCompletionInvalido:
        choices = [_FakeChoiceInvalido()]

    monkeypatch.setattr(
        _ai_mod.AIService,
        "_chamar_llm",
        lambda self, messages: _FakeCompletionInvalido(),
    )

    tel = "5538944440001"
    user = Usuario(telefone=tel, nome_cliente="JSON Test", bot_ativo=True)
    db.add(user)
    db.commit()

    # Cria histórico para não cair em primeiro contato
    hist = HistoricoConversa(
        telefone_usuario=tel,
        mensagem_cliente="msg anterior",
        resposta_bot="resposta anterior",
        origem="bot",
    )
    db.add(hist)
    db.commit()

    payload = _montar_payload_webhook(tel, "pergunta complexa fora do FAQ", message_id="hh02-001")
    resp = client.post("/webhook", json=payload)
    assert resp.status_code == 200

    # O histórico deve ter registrado a resposta de fallback
    db.refresh(user)
    historico = db.query(HistoricoConversa).filter(
        HistoricoConversa.telefone_usuario == tel
    ).order_by(HistoricoConversa.id.desc()).first()

    # Em modo bot_only: bot continua ativo, resposta de erro enviada
    assert historico is not None
    assert historico.intencao == "transbordo_falha"


def test_processamento_ia_retorna_resposta_correta(client, db):
    """IA com mock válido processa mensagem e grava no histórico."""
    tel = "5538955550001"
    user = Usuario(telefone=tel, nome_cliente="AI Test", bot_ativo=True)
    db.add(user)
    db.commit()

    # Histórico necessário para não cair em primeiro contato
    db.add(HistoricoConversa(
        telefone_usuario=tel,
        mensagem_cliente="anterior",
        resposta_bot="anterior",
        origem="bot",
    ))
    db.commit()

    payload = _montar_payload_webhook(tel, "quero saber sobre barba", message_id="ai-test-001")
    resp = client.post("/webhook", json=payload)
    assert resp.status_code == 200

    historico = db.query(HistoricoConversa).filter(
        HistoricoConversa.telefone_usuario == tel,
        HistoricoConversa.mensagem_cliente == "quero saber sobre barba",
    ).first()

    assert historico is not None
    assert historico.resposta_bot == "Resposta de teste."
