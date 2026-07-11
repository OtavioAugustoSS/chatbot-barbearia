import os
import re
import json
import time
import logging
import threading
import logging.handlers
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
load_dotenv()

import openai
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from sqlalchemy.orm import joinedload
from core.prompts import SYSTEM_PROMPT_BARBEARIA, ANCORA_ANTI_DRIFT
from core import config
from core.config import MODO_HIBRIDO
from db.models import Servico, Barbeiro
from services.circuit_breaker import CircuitBreaker, CircuitOpenError

log = logging.getLogger("barbearia.ai")

INTENCOES_VALIDAS = {"tirar_duvida", "chamar_recepcao", "transbordo_falha"}

# Frases proibidas: IA não pode prometer agendamento. Se aparecer, força redirect AppBarber.
# QW-B3: padrões expandidos para cobrir formas passivas, participio e coloquiais.
_REGEX_AGENDAMENTO_PROIBIDO = re.compile(
    r"\b("
    # Formas ativas diretas (cobertura original)
    r"marquei|agendei|reservei|"
    r"confirmei seu? hor[aá]rio|"
    r"seu hor[aá]rio (est[aá]|foi) (marcado|agendado|confirmado|reservado)|"
    r"j[aá] (marquei|agendei|reservei)|"
    r"posso (marcar|agendar|reservar) (para|pra) (voc[eê]|ti)|"
    r"vou (marcar|agendar|reservar) (para|pra) (voc[eê]|ti)|"
    # QW-B3: formas passivas e coloquiais adicionadas
    r"reserva\s+confirmada|"
    r"agendamento\s+(foi\s+|est[aá]\s+)?(realizado|confirmado|feito|conclu[íi]do)|"
    r"(ficou|est[aá]|foi)\s+(marcad|agendad|confirmad|reservad)[ao]|"
    r"j[aá]\s+(deixei|est[aá]|foi)\s+(marcad|agendad|reservad)[ao]|"
    r"vou\s+(deixar|deixo)\s+(reservad|marcad|agendad)[ao]|"
    r"pode\s+(ir|vir)\s+que\s+(j[aá]\s+)?est[aá]\s+(marcad|agendad|confirmad)[ao]"
    r")\b",
    re.IGNORECASE,
)
_FRASE_REDIRECT_APPBARBER = (
    "Para agendamentos, acesse nosso aplicativo oficial: https://sites.appbarber.com.br/bolshoi"
)

# P1-7: o telefone PESSOAL do Fred só pode ser compartilhado se o cliente PEDIR
# explicitamente (BR-002). Guard determinístico (análogo ao anti-agendamento): se a IA
# vazar o número sem pedido explícito, neutralizamos. Pega variações de (38) 99897-0661.
_REGEX_NUMERO_FRED = re.compile(r"\(?\s*38\s*\)?[\s.\-]*9\s*9897[\s.\-]?0661")
_REGEX_PEDIU_CONTATO_FRED = re.compile(
    r"(telefone|n[uú]mero|contato|whats(app)?|zap|celular)\b.{0,25}\bfred\b|"
    r"\bfred\b.{0,25}(telefone|n[uú]mero|contato|whats(app)?|zap|celular)|"
    r"(falar|chamar|ligar)\s+(com\s+|pra\s+|para\s+)?(o\s+)?fred\b",
    re.IGNORECASE,
)

# Brasil é UTC-3 fixo (sem horário de verão desde 2019). Offset hardcoded
# evita dependência de tzdata em Windows e elimina ambiguidade.
_TZ_BR = timezone(timedelta(hours=-3), name="America/Sao_Paulo")
_DIAS_PT = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
_MESES_PT = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]

# Horários por dia da semana em minutos. weekday(): 0=segunda ... 6=domingo.
# B9: derivado da fonte única services/horarios.py (HORARIOS_FALLBACK) — usado
# APENAS como fallback caso a tabela `horarios` esteja vazia/inacessível.
from services.horarios import (  # noqa: E402
    fallback_em_minutos as _fallback_em_minutos,
    carregar_horarios_db as _carregar_horarios_db,
    invalidar_cache_horarios,
    _cache_horarios,
    _cache_horarios_lock,
)

_HORARIOS = _fallback_em_minutos()


def _horario_para_minutos(horario_str: str) -> int:
    """Converte 'HH:MM' em minutos desde 00:00.

    Levanta ValueError em formato/faixa inválidos — o chamador decide o fallback.
    Sem esta validação, um registro malformado na tabela `horarios` derrubava
    TODA chamada de IA para transbordo_falha.
    """
    if not isinstance(horario_str, str) or not re.fullmatch(r"\d{1,2}:\d{2}", horario_str.strip()):
        raise ValueError(f"Horário malformado: {horario_str!r} (esperado 'HH:MM')")
    h, m = horario_str.strip().split(":")
    h, m = int(h), int(m)
    if h > 23 or m > 59:
        raise ValueError(f"Horário fora de faixa: {horario_str!r}")
    return h * 60 + m


def _formatar_horario_dia(weekday: int, horarios_db: dict | None = None) -> str:
    """Texto curto do horário de um dia da semana.

    Prioridade: horarios_db (Horario objects do banco) → _HORARIOS (fallback hardcoded).
    horarios_db: dict {dia_semana: Horario} ou None.
    """
    if horarios_db and weekday in horarios_db:
        reg = horarios_db[weekday]
        if reg.fechado or reg.abertura is None:
            return "FECHADA"
        return f"das {reg.abertura} às {reg.fechamento}"

    # Fallback: dict hardcoded
    h = _HORARIOS.get(weekday)
    if h is None:
        return "FECHADA"
    abre, fecha = h
    return f"das {abre//60:02d}:{abre%60:02d} às {fecha//60:02d}:{fecha%60:02d}"


# Cache de horários e invalidação: movidos para services/horarios.py (B9).
# Os nomes _cache_horarios/_cache_horarios_lock/invalidar_cache_horarios continuam
# exportados deste módulo (import no topo) para compatibilidade com chamadores
# e testes existentes — apontam para os MESMOS objetos do módulo horarios.


def _construir_contexto_temporal() -> str:
    """
    Mensagem do sistema com data/hora atual (Brasília) e status de funcionamento.
    Inclui horário de hoje, amanhã e depois-amanhã pra IA resolver "amanhã" / etc.
    Reduz alucinação de dia da semana e disponibilidade.

    Horários são consultados da tabela `horarios` no banco de dados.
    Fallback para _HORARIOS hardcoded se a tabela estiver vazia ou inacessível.
    """
    from datetime import timedelta as _td
    agora = datetime.now(_TZ_BR)
    amanha = agora + _td(days=1)
    depois = agora + _td(days=2)

    dia_semana = _DIAS_PT[agora.weekday()]
    data_str = f"{agora.day} de {_MESES_PT[agora.month - 1]} de {agora.year}"
    hora_str = agora.strftime("%H:%M")
    minutos_agora = agora.hour * 60 + agora.minute

    # Carrega horários do banco; fallback silencioso para dict hardcoded se vazio.
    horarios_db = _carregar_horarios_db()
    usar_db = bool(horarios_db)

    status = None
    if usar_db:
        reg_hoje = horarios_db.get(agora.weekday())
        if reg_hoje is None or reg_hoje.fechado or reg_hoje.abertura is None:
            nome_dia = _DIAS_PT[agora.weekday()]
            status = f"FECHADA hoje ({nome_dia})."
        else:
            try:
                abre = _horario_para_minutos(reg_hoje.abertura)
                fecha = _horario_para_minutos(reg_hoje.fechamento)
            except ValueError as e:
                # B5: registro malformado no banco não pode derrubar a IA inteira —
                # cai para o calendário hardcoded e loga para correção manual.
                log.warning("Horário inválido no banco (dia %s): %s — usando fallback hardcoded.",
                            agora.weekday(), e)
                horarios_db = None
            else:
                if minutos_agora < abre:
                    status = f"FECHADA agora. Abre hoje às {reg_hoje.abertura} e fecha às {reg_hoje.fechamento}."
                elif minutos_agora >= fecha:
                    status = f"FECHADA agora (já passou das {reg_hoje.fechamento} de hoje)."
                else:
                    status = f"ABERTA agora. Fecha hoje às {reg_hoje.fechamento}."

    if status is None:
        # Fallback hardcoded
        horario_dia = _HORARIOS[agora.weekday()]
        if horario_dia is None:
            status = "FECHADA hoje (domingo)."
        else:
            abre, fecha = horario_dia
            if minutos_agora < abre:
                status = f"FECHADA agora. Abre hoje às {abre//60:02d}:{abre%60:02d} e fecha às {fecha//60:02d}:{fecha%60:02d}."
            elif minutos_agora >= fecha:
                status = f"FECHADA agora (já passou das {fecha//60:02d}:{fecha%60:02d} de hoje)."
            else:
                status = f"ABERTA agora. Fecha hoje às {fecha//60:02d}:{fecha%60:02d}."

    return (
        "CONTEXTO TEMPORAL — use SEMPRE estes valores ao mencionar dia, hora ou status de funcionamento. "
        "PROIBIDO inventar ou chutar dia da semana.\n"
        f"- Hoje é {dia_semana}, {data_str}.\n"
        f"- Hora atual em Brasília: {hora_str}.\n"
        f"- Status da barbearia neste momento: {status}\n"
        f"- Amanhã ({_DIAS_PT[amanha.weekday()]}): {_formatar_horario_dia(amanha.weekday(), horarios_db)}.\n"
        f"- Depois de amanhã ({_DIAS_PT[depois.weekday()]}): {_formatar_horario_dia(depois.weekday(), horarios_db)}.\n"
        "- Use 'amanhã' / 'depois de amanhã' SEMPRE com o dia correto da semana acima.\n"
        "- Se o cliente perguntar 'até que horas abre hoje?' / 'estão abertos?' / 'que dia é hoje?', "
        "responda usando EXATAMENTE essas informações."
    )


# Resposta determinística usada quando NVIDIA_API_KEY está ausente (modo dev).
# Mantém o contrato {intencao, resposta_sugerida} e o padrão <br> de formatação da IA.
_RESPOSTA_DEMO_IA = (
    "🤖 Estou em *modo demonstração* — a IA (NVIDIA_API_KEY) ainda não foi configurada.<br><br>"
    "Mesmo assim, posso te atender pelos fluxos automáticos: digite *menu* para ver "
    "serviços, preços, equipe, horários e localização.<br><br>"
    "_Em produção, esta pergunta seria respondida pela IA (Llama 3.1 70B)._"
)


class AIService:
    def __init__(self):
        # Cliente criado sob demanda (lazy): sem NVIDIA_API_KEY o construtor do SDK
        # OpenAI levanta exceção, o que derrubava o boot inteiro no import do webhook.
        self._client = None
        self.model_name = "meta/llama-3.1-70b-instruct"
        # P2-1: circuit breaker em volta da chamada ao NIM. Após N falhas consecutivas
        # (cada uma já esgotou os 3 retries do tenacity), abre por N segundos e as
        # mensagens seguintes caem direto no handoff em vez de pendurar ~24s cada.
        self._breaker = CircuitBreaker(
            failure_threshold=config.CB_FAILURE_THRESHOLD,
            reset_timeout=float(config.CB_RESET_TIMEOUT),
            name="nim-llm",
        )
        # Cache simples de serviços/barbeiros (mudam raramente; revalida a cada N segundos).
        self._cache_db = {"data": None, "expira_em": 0.0}
        self._cache_ttl_segundos = 300  # 5 min
        # TD-005: lock único por instância protege _cache_db de race conditions
        # em background tasks concorrentes (FastAPI + threading).
        self._cache_lock = threading.Lock()
        # TD-004: logger com rotação em vez de arquivo plano ilimitado.
        # Singleton compartilhado com o webhook (core/debug_log.py) — um único
        # escritor com rotação para erro_ia_debug.txt.
        from core.debug_log import get_debug_logger

        self._debug_logger = get_debug_logger()

    @property
    def client(self) -> OpenAI:
        """Cliente NVIDIA NIM criado sob demanda — nunca no import do módulo."""
        if self._client is None:
            self._client = OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=config.NVIDIA_API_KEY,
            )
        return self._client

    def _carregar_dados_db(self, db_session):
        """Cache de serviços/barbeiros formatados. Evita 4 queries SQL por mensagem.
        Thread-safe via self._cache_lock (TD-005).
        """
        agora = time.time()
        # Leitura rápida sob lock — evita cache stale em threads concorrentes.
        with self._cache_lock:
            if self._cache_db["data"] and agora < self._cache_db["expira_em"]:
                return self._cache_db["data"]

        servicos = db_session.query(Servico).filter(Servico.ativo == True).order_by(Servico.categoria, Servico.id).all()
        barbeiros = (
            db_session.query(Barbeiro)
            .options(joinedload(Barbeiro.servicos))
            .order_by(Barbeiro.id)
            .all()
        )

        def _linha_servico(s):
            # Formato pensado pra desencorajar copy-paste literal pelo LLM.
            # PRIMÁRIO (sempre mostrar em listas): nome + preço.
            # REFERÊNCIA (só usar se cliente perguntar diretamente sobre o serviço):
            # descrição e duração ficam após " | ref:" e o prompt orienta a NÃO copiar isso em listas.
            # B8: campos None são omitidos — antes a linha imprimia "None" literal.
            ref_partes = []
            if s.tempo_estimado_minutos is not None:
                ref_partes.append(f"dura {s.tempo_estimado_minutos}min")
            if s.descricao:
                ref_partes.append(f"desc: {s.descricao}")
            linha = f"✂️ {s.nome_servico} — R$ {s.preco:.2f}"
            if ref_partes:
                linha += "  | ref: " + "; ".join(ref_partes)
            return linha

        barbearia = [s for s in servicos if s.categoria == "barbearia"]
        estetica = [s for s in servicos if s.categoria == "estetica"]

        partes = []
        if barbearia:
            partes.append("💈 BARBEARIA:\n" + "\n".join(_linha_servico(s) for s in barbearia))
        if estetica:
            partes.append("💆‍♀️ ESTÉTICA:\n" + "\n".join(_linha_servico(s) for s in estetica))
        str_servicos = "\n\n".join(partes) if partes else "Nenhum serviço encontrado."

        lista_barbeiros = []
        for b in barbeiros:
            nomes_servicos = [servico.nome_servico for servico in b.servicos]
            str_servicos_do_barbeiro = ", ".join(nomes_servicos) if nomes_servicos else "Nenhum serviço cadastrado"
            lista_barbeiros.append(f"{b.nome} ({b.dias_trabalho}) -> Especializa-se em: {str_servicos_do_barbeiro}")
        str_barbeiros = "\n".join(lista_barbeiros) if lista_barbeiros else "Nenhum barbeiro encontrado."

        dados = (str_servicos, str_barbeiros)
        with self._cache_lock:
            self._cache_db = {"data": dados, "expira_em": agora + self._cache_ttl_segundos}
        return dados

    def invalidar_cache_db(self):
        """Chamar após mutação em Servico/Barbeiro pra forçar revalidação."""
        with self._cache_lock:
            self._cache_db = {"data": None, "expira_em": 0.0}

    @retry(
        retry=retry_if_exception_type((openai.APITimeoutError, openai.APIConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def _chamar_llm(self, messages):
        return self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.0,
            max_tokens=2048,
            response_format={"type": "json_object"},
            timeout=30,
        )

    def _validar_resposta(self, dados: dict, mensagem_cliente: str = "") -> dict:
        """Sanitiza resposta da IA: enum válido + bloqueio de promessas de agendamento
        + guard do telefone do Fred (BR-002)."""
        intencao = dados.get("intencao", "tirar_duvida")
        if intencao not in INTENCOES_VALIDAS:
            log.warning("Intenção fora do enum (%s) - rebaixando para 'tirar_duvida'.", intencao)
            intencao = "tirar_duvida"

        resposta = dados.get("resposta_sugerida", "")
        if isinstance(resposta, str) and _REGEX_AGENDAMENTO_PROIBIDO.search(resposta):
            log.warning("Resposta da IA prometeu agendamento - sobrescrita com redirect AppBarber.")
            resposta = (
                f"Não realizamos agendamentos pelo chat.<br><br>{_FRASE_REDIRECT_APPBARBER}"
            )

        # P1-7: guard do telefone pessoal do Fred — só compartilha se o cliente PEDIU
        # explicitamente (BR-002). Drift da IA que vaze o número é neutralizado.
        if isinstance(resposta, str) and _REGEX_NUMERO_FRED.search(resposta):
            if not (mensagem_cliente and _REGEX_PEDIU_CONTATO_FRED.search(mensagem_cliente)):
                log.warning("IA incluiu telefone do Fred sem pedido explícito - neutralizado (BR-002).")
                resposta = (
                    "Posso te ajudar com informações da barbearia, nossos serviços e o agendamento "
                    "pelo app. Como posso ajudar?"
                )

        # QW-B2: sanitização técnica contra service description leakage.
        # Remove " | ref: dura Xmin; desc: ..." que pode vazar se o modelo sofrer drift
        # e copiar literalmente o campo de referência injetado no prompt.
        if isinstance(resposta, str):
            resposta = re.sub(r'\s*\|\s*ref:[^\n<]*', '', resposta)

        return {"intencao": intencao, "resposta_sugerida": resposta}

    def processar_intencao(self, db_session, historico_mensagens, mensagem_atual, nome_cliente=None):
        # Modo dev sem NVIDIA_API_KEY: resposta demo determinística no lugar da IA.
        # intencao=tirar_duvida mantém o bot ativo (handoff continua testável pelos
        # fluxos determinísticos de menu, ex.: MENU_RECEPCAO).
        if config.IA_FAKE:
            return {"intencao": "tirar_duvida", "resposta_sugerida": _RESPOSTA_DEMO_IA}
        try:
            str_servicos, str_barbeiros = self._carregar_dados_db(db_session)

            system_instruction = SYSTEM_PROMPT_BARBEARIA.format(
                lista_servicos_do_banco=str_servicos,
                lista_barbeiros_do_banco=str_barbeiros
            )

            messages_payload = [{"role": "system", "content": system_instruction}]

            # Contexto temporal: data/hora real em Brasília + status aberto/fechado.
            # Sem isso, IA chuta dia da semana baseado em texto solto do histórico.
            messages_payload.append({"role": "system", "content": _construir_contexto_temporal()})

            # Modo de operação: IA precisa saber se há atendente humano para oferecer.
            if MODO_HIBRIDO:
                modo_msg = (
                    "MODO_OPERACAO: hibrido — há atendente humano disponível neste canal. "
                    "Quando você não conseguir resolver algo (disponibilidade em tempo real, reclamações, "
                    "casos especiais), pode OFERECER ao cliente falar com a recepção. "
                    "Se o cliente aceitar (responder 'sim', 'pode', 'quero', 'por favor'), use "
                    "intencao=chamar_recepcao. Não force a oferta toda hora — só quando fizer sentido."
                )
            else:
                modo_msg = (
                    "MODO_OPERACAO: bot_only — NÃO há atendente humano disponível neste canal. "
                    "PROIBIDO oferecer 'falar com a recepção', 'transferir para um atendente', "
                    "'aguardar atendimento humano'. Se não souber algo, oriente o cliente a usar "
                    "o app https://sites.appbarber.com.br/bolshoi para agendar/consultar. "
                    "Para falar com o Fred (proprietário), só dê o número se o cliente pedir explicitamente."
                )
            messages_payload.append({"role": "system", "content": modo_msg})

            if nome_cliente:
                messages_payload.append({
                    "role": "system",
                    "content": f"O cliente atual se chama '{nome_cliente}'. Use o nome para personalizar o atendimento quando apropriado."
                })

            for msg in historico_mensagens:
                role = "assistant" if msg.get("role") in ["bot", "model", "assistant"] else "user"
                messages_payload.append({"role": role, "content": msg.get("content", "")})

            # Anti-drift: a cada >=4 mensagens, injeta âncora antes da pergunta atual.
            # QW-B4: threshold reduzido de 6 para 4 — drift já ocorre a partir da 2ª troca
            # em conversas sobre disponibilidade/agendamento. Custo da âncora é ~200 tokens.
            if len(historico_mensagens) >= 4:
                messages_payload.append({"role": "system", "content": ANCORA_ANTI_DRIFT})

            messages_payload.append({"role": "user", "content": mensagem_atual})

            t0 = time.time()
            # P2-1: via circuit breaker — se aberto, levanta CircuitOpenError na hora,
            # que cai no `except Exception` abaixo e aciona o handoff sem esperar retries.
            completion = self._breaker.call(self._chamar_llm, messages_payload)
            elapsed = time.time() - t0
            log.info("IA completion ok em %.2fs (msgs=%d)", elapsed, len(messages_payload))

            # QW-B5: JSON truncado por max_tokens — não adianta tentar parsear.
            if completion.choices[0].finish_reason == "length":
                log.warning(
                    "QW-B5: finish_reason=length — resposta truncada, forçando transbordo_falha. "
                    "Considere aumentar max_tokens ou encurtar o prompt."
                )
                self._registrar_erro_debug("[ERRO JSON TRUNCADO] finish_reason=length")
                return {
                    "intencao": "transbordo_falha",
                    "resposta_sugerida": "Tive um problema técnico momentâneo. Vou conectar você à recepção agora.",
                }

            response_text = completion.choices[0].message.content.strip()
            log.debug("IA raw response: %s", response_text[:300])

            if response_text.startswith("```json"):
                response_text = response_text[7:]
            elif response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            # QW-B1: tenta parse direto primeiro.
            # Se falhar, extrai objeto JSON embutido em texto livre (fallback regex).
            # Cobre: pretty-print sem '{' inicial, JSON com texto antes/depois, JSON após explicação.
            try:
                dados = json.loads(response_text)
            except json.JSONDecodeError:
                # Fallback 1: extrai objeto JSON que contenha as chaves esperadas
                _match = re.search(
                    r'\{[^{}]*"intencao"[^{}]*"resposta_sugerida"[^{}]*\}',
                    response_text,
                    re.DOTALL,
                )
                if _match:
                    try:
                        dados = json.loads(_match.group())
                        log.warning("QW-B1: JSON extraído via regex (fallback 1). Texto bruto: %s", response_text[:200])
                    except json.JSONDecodeError:
                        dados = None
                else:
                    dados = None

                if dados is None:
                    # Fallback 2: extrai qualquer objeto JSON e valida campos obrigatórios
                    _match2 = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if _match2:
                        try:
                            _candidato = json.loads(_match2.group())
                            if "intencao" in _candidato and "resposta_sugerida" in _candidato:
                                dados = _candidato
                                log.warning("QW-B1: JSON extraído via regex (fallback 2). Texto bruto: %s", response_text[:200])
                        except json.JSONDecodeError:
                            pass

                if dados is None:
                    # Esgotou os fallbacks — lança exceção para o except externo tratar
                    raise json.JSONDecodeError(
                        "QW-B1: nenhum objeto JSON válido encontrado após todos os fallbacks",
                        response_text,
                        0,
                    )

            if "intencao" not in dados and "choices" in dados:
                inner = dados["choices"][0]["message"]["content"]
                dados = json.loads(inner) if isinstance(inner, str) else inner

            return self._validar_resposta(dados, mensagem_atual)

        except json.JSONDecodeError as e:
            log.error("Falha ao parsear JSON da IA: %s", e)
            # LGPD: trunca o texto da IA (pode ecoar mensagem do cliente = PII) a 200 chars.
            _trecho = (response_text[:200] if 'response_text' in locals() and response_text else 'N/A')
            self._registrar_erro_debug(f"[ERRO JSON] {e}\nTexto (primeiros 200 chars): {_trecho}")
            return {
                "intencao": "transbordo_falha",
                "resposta_sugerida": "Estou enfrentando uma instabilidade. Só um instante, estou conectando você à recepção para continuarmos."
            }
        except CircuitOpenError as e:
            # P2-1: circuito aberto (NIM em outage) — handoff imediato. O alerta forte
            # já foi logado quando o circuito abriu; aqui não repetimos como erro novo.
            log.warning("[IA DEGRADADA] %s — handoff direto sem esperar retries.", e)
            return {
                "intencao": "transbordo_falha",
                "resposta_sugerida": "Estou com uma instabilidade momentânea. Vou te conectar à recepção para não te deixar esperando."
            }
        except Exception as e:
            # P1-1: alerta DISTINTO e acionável de IA indisponível (após retries) —
            # catchável por monitor de log / Sentry. Handoff (transbordo_falha) é acionado abaixo.
            log.error("[IA INDISPONÍVEL] Falha ao processar intenção (após retries): %s — acionando handoff.", e)
            log.exception("Detalhe do erro em processar_intencao")
            self._registrar_erro_debug(f"[ERRO AI SERVICE NVIDIA] {e}")
            return {
                "intencao": "transbordo_falha",
                "resposta_sugerida": "Tivemos um pequeno erro de comunicação. Aguarde um minuto e já te atendo!"
            }

    def _registrar_erro_debug(self, mensagem: str):
        """Registra erro em erro_ia_debug.txt com rotação automática (TD-004).
        Usa RotatingFileHandler configurado no __init__ (5MB x 3 backups).
        """
        try:
            self._debug_logger.error(mensagem)
        except Exception:
            pass  # Nunca deixar erro de log derrubar o fluxo principal
