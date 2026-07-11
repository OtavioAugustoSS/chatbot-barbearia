"""
Testes dos bugs corrigidos na revisão geral (B1-B9).

B1: dedup INSERT-first — IntegrityError = duplicada (não bypass).
B4: batch da Meta — todas as mensagens do payload são extraídas.
B5: horário malformado no banco não derruba a IA.
B6: "app"/"aplicativo" sem contexto não dispara canônica de agendamento.
B8: linha de serviço omite campos None.
B9: fonte única de horários gera o mesmo texto canônico.
"""
import pytest

from db.models import MensagemProcessada, Horario, Servico
from api.webhook import _ja_processada
from services.whatsapp import extrair_mensagens
from core.respostas_canonicas import detectar_resposta_canonica, RESPOSTA_AGENDAMENTO


# ---------------------------------------------------------------- B1: dedup

def test_dedup_mensagem_nova_registra_e_libera(db):
    assert _ja_processada(db, "wamid.b1.nova") is False
    assert db.query(MensagemProcessada).filter_by(message_id="wamid.b1.nova").first() is not None


def test_dedup_mensagem_repetida_bloqueia(db):
    assert _ja_processada(db, "wamid.b1.rep") is False
    assert _ja_processada(db, "wamid.b1.rep") is True


def test_dedup_integrity_error_conta_como_duplicada(db):
    """Race de retransmissão: registro já existe (inserido por 'outra thread') —
    o INSERT deste caller sofre IntegrityError e DEVE devolver True (duplicada)."""
    db.add(MensagemProcessada(message_id="wamid.b1.race"))
    db.commit()
    assert _ja_processada(db, "wamid.b1.race") is True


# ---------------------------------------------------------------- B4: batch

def _payload_meta(mensagens: list[dict], nome="Cliente Batch"):
    return {
        "entry": [{
            "changes": [{
                "value": {
                    "contacts": [{"profile": {"name": nome}, "wa_id": "5538988887777"}],
                    "messages": mensagens,
                },
            }],
        }],
    }


def test_extrair_mensagens_batch_completo():
    payload = _payload_meta([
        {"from": "5538988887777", "id": "wamid.m1", "type": "text", "text": {"body": "primeira"}},
        {"from": "5538988887777", "id": "wamid.m2", "type": "text", "text": {"body": "segunda"}},
        {"from": "5538988887777", "id": "wamid.m3", "type": "text", "text": {"body": "terceira"}},
    ])
    extraidas = extrair_mensagens(payload)
    assert [m[1] for m in extraidas] == ["primeira", "segunda", "terceira"]
    assert all(m[0] == "5538988887777" for m in extraidas)
    assert [m[3] for m in extraidas] == ["wamid.m1", "wamid.m2", "wamid.m3"]


def test_extrair_mensagens_item_invalido_nao_derruba_batch():
    payload = _payload_meta([
        {"from": "5538988887777", "id": "wamid.ok1", "type": "text", "text": {"body": "válida"}},
        {"from": None, "id": "wamid.bad", "type": "text", "text": {"body": "sem from"}},
        {"from": "5538988887777", "id": "wamid.ok2", "type": "interactive",
         "interactive": {"type": "list_reply", "list_reply": {"id": "MENU_EQUIPE"}}},
    ])
    extraidas = extrair_mensagens(payload)
    assert [m[1] for m in extraidas] == ["válida", "MENU_EQUIPE"]


def test_webhook_processa_batch_de_duas_mensagens(client, db, mock_externos):
    """POST com 2 mensagens de texto → as duas entram no pipeline (2 dedups gravados)."""
    payload = _payload_meta([
        {"from": "5538977776666", "id": "wamid.batch.a", "type": "text", "text": {"body": "oi"}},
        {"from": "5538977776666", "id": "wamid.batch.b", "type": "text", "text": {"body": "menu"}},
    ])
    resp = client.post("/webhook", json=payload)
    assert resp.status_code == 200
    ids = {m.message_id for m in db.query(MensagemProcessada).all()}
    assert {"wamid.batch.a", "wamid.batch.b"} <= ids


# ---------------------------------------------------------------- B5: horário malformado

def test_horario_malformado_no_banco_nao_derruba_contexto(db, monkeypatch):
    from services import ai_service, horarios

    db.add(Horario(dia_semana=0, abertura="25:99", fechamento="99:00", fechado=False))
    db.commit()

    monkeypatch.setattr(horarios, "_cache_horarios", {"data": None, "expira_em": 0.0})
    # Força o contexto a "hoje = segunda" não é necessário: basta que a função
    # não levante para NENHUM dia — malformado cai no fallback hardcoded.
    registros = {r.dia_semana: r for r in db.query(Horario).all()}
    monkeypatch.setattr(ai_service, "_carregar_horarios_db", lambda: registros)
    contexto = ai_service._construir_contexto_temporal()
    assert "Status da barbearia" in contexto  # não explodiu


def test_horario_para_minutos_valida_formato_e_faixa():
    from services.ai_service import _horario_para_minutos

    assert _horario_para_minutos("09:30") == 570
    for invalido in ("25:99", "9h30", "", "abc", "12:60", None):
        with pytest.raises((ValueError, TypeError)):
            _horario_para_minutos(invalido)


# ---------------------------------------------------------------- B6: falso positivo "app"

def test_app_sem_contexto_nao_dispara_agendamento():
    assert detectar_resposta_canonica("meu aplicativo de banco travou") != RESPOSTA_AGENDAMENTO
    assert detectar_resposta_canonica("o app do meu celular está lento") != RESPOSTA_AGENDAMENTO


def test_app_com_contexto_dispara_agendamento():
    assert detectar_resposta_canonica("como baixo o app de vocês?") == RESPOSTA_AGENDAMENTO
    assert detectar_resposta_canonica("qual o link do aplicativo?") == RESPOSTA_AGENDAMENTO
    assert detectar_resposta_canonica("appbarber") == RESPOSTA_AGENDAMENTO
    assert detectar_resposta_canonica("quero agendar pelo aplicativo") is not None


# ---------------------------------------------------------------- B8: campos None

def test_linha_servico_omite_campos_none(db):
    from services.ai_service import AIService

    # tempo_estimado_minutos é NOT NULL no schema; descricao é o campo anulável.
    db.add(Servico(nome_servico="Combo Teste", preco=70, tempo_estimado_minutos=45,
                   descricao=None, categoria="barbearia", ativo=True))
    db.commit()
    svc = AIService()
    str_servicos, _ = svc._carregar_dados_db(db)
    assert "None" not in str_servicos
    assert "Combo Teste" in str_servicos


# ---------------------------------------------------------------- B9: fonte única

def test_corpo_horario_fallback_identico_ao_texto_historico():
    from services.horarios import corpo_horario_fallback

    assert corpo_horario_fallback() == (
        "*Nosso horário de funcionamento:*<br><br>"
        "Segunda: 14:00 às 21:00<br>"
        "Terça a Sexta: 09:00 às 21:00<br>"
        "Sábado: 09:00 às 18:00<br>"
        "Domingo: fechado"
    )


def test_fallback_minutos_deriva_do_mesmo_calendario():
    from services.horarios import HORARIOS_FALLBACK, fallback_em_minutos

    minutos = fallback_em_minutos()
    assert minutos[0] == (14 * 60, 21 * 60)
    assert minutos[6] is None
    assert set(minutos) == set(HORARIOS_FALLBACK)
