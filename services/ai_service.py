import os
import re
import json
import time
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
load_dotenv()

import openai
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from sqlalchemy.orm import joinedload
from core.prompts import SYSTEM_PROMPT_BARBEARIA, ANCORA_ANTI_DRIFT
from core.config import MODO_HIBRIDO
from db.models import Servico, Barbeiro, Horario

log = logging.getLogger("barbearia.ai")

INTENCOES_VALIDAS = {"tirar_duvida", "chamar_recepcao", "transbordo_falha"}

# Frases proibidas: IA não pode prometer agendamento. Se aparecer, força redirect AppBarber.
_REGEX_AGENDAMENTO_PROIBIDO = re.compile(
    r"\b(marquei|agendei|reservei|confirmei seu? hor[aá]rio|seu hor[aá]rio (est[aá]|foi) (marcado|agendado|confirmado|reservado)|"
    r"j[aá] (marquei|agendei|reservei)|posso (marcar|agendar|reservar) (para|pra) (voc[eê]|ti)|"
    r"vou (marcar|agendar|reservar) (para|pra) (voc[eê]|ti))\b",
    re.IGNORECASE,
)
_FRASE_REDIRECT_APPBARBER = (
    "Para agendamentos, acesse nosso aplicativo oficial: https://sites.appbarber.com.br/bolshoi"
)

# Brasil é UTC-3 fixo (sem horário de verão desde 2019). Offset hardcoded
# evita dependência de tzdata em Windows e elimina ambiguidade.
_TZ_BR = timezone(timedelta(hours=-3), name="America/Sao_Paulo")
_DIAS_PT = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
_MESES_PT = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]

# Horários por dia da semana. weekday(): 0=segunda ... 6=domingo.
# (abre, fecha) em minutos desde 00:00. None = fechado.
# ATENÇÃO: estes valores agora vivem na tabela `horarios` do banco de dados.
# Populados via scripts/seed_horarios.py. Este dict é usado APENAS como fallback
# caso a tabela esteja vazia (ex.: primeiro boot antes do seed).
_HORARIOS = {
    0: (14 * 60, 21 * 60),       # segunda
    1: (9 * 60, 21 * 60),        # terça
    2: (9 * 60, 21 * 60),        # quarta
    3: (9 * 60, 21 * 60),        # quinta
    4: (9 * 60, 21 * 60),        # sexta
    5: (9 * 60, 18 * 60),        # sábado
    6: None,                     # domingo
}


def _horario_para_minutos(horario_str: str) -> int:
    """Converte 'HH:MM' em minutos desde 00:00."""
    h, m = horario_str.split(":")
    return int(h) * 60 + int(m)


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


def _carregar_horarios_db() -> dict:
    """Retorna dict {dia_semana: Horario} consultando o banco. Retorna {} em caso de erro."""
    from db.database import SessionLocal
    db = SessionLocal()
    try:
        registros = db.query(Horario).all()
        return {r.dia_semana: r for r in registros}
    except Exception as e:
        log.warning("Falha ao carregar horarios do banco, usando fallback hardcoded: %s", e)
        return {}
    finally:
        db.close()


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

    if usar_db:
        reg_hoje = horarios_db.get(agora.weekday())
        if reg_hoje is None or reg_hoje.fechado or reg_hoje.abertura is None:
            nome_dia = _DIAS_PT[agora.weekday()]
            status = f"FECHADA hoje ({nome_dia})."
        else:
            abre = _horario_para_minutos(reg_hoje.abertura)
            fecha = _horario_para_minutos(reg_hoje.fechamento)
            if minutos_agora < abre:
                status = f"FECHADA agora. Abre hoje às {reg_hoje.abertura} e fecha às {reg_hoje.fechamento}."
            elif minutos_agora >= fecha:
                status = f"FECHADA agora (já passou das {reg_hoje.fechamento} de hoje)."
            else:
                status = f"ABERTA agora. Fecha hoje às {reg_hoje.fechamento}."
    else:
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


class AIService:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.getenv("NVIDIA_API_KEY")
        )
        self.model_name = "meta/llama-3.1-70b-instruct"
        # Cache simples de serviços/barbeiros (mudam raramente; revalida a cada N segundos).
        self._cache_db = {"data": None, "expira_em": 0.0}
        self._cache_ttl_segundos = 300  # 5 min

    def _carregar_dados_db(self, db_session):
        """Cache de serviços/barbeiros formatados. Evita 4 queries SQL por mensagem."""
        agora = time.time()
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
            return (
                f"✂️ {s.nome_servico} — R$ {s.preco:.2f}"
                f"  | ref: dura {s.tempo_estimado_minutos}min; desc: {s.descricao}"
            )

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
        self._cache_db = {"data": dados, "expira_em": agora + self._cache_ttl_segundos}
        return dados

    def invalidar_cache_db(self):
        """Chamar após mutação em Servico/Barbeiro pra forçar revalidação."""
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

    def _validar_resposta(self, dados: dict) -> dict:
        """Sanitiza resposta da IA: enum válido + bloqueio de promessas de agendamento."""
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

        return {"intencao": intencao, "resposta_sugerida": resposta}

    def processar_intencao(self, db_session, historico_mensagens, mensagem_atual, nome_cliente=None):
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

            # Anti-drift: a cada >=6 mensagens, injeta âncora antes da pergunta atual.
            # Reforça regras críticas que tendem a se diluir em conversas longas.
            if len(historico_mensagens) >= 6:
                messages_payload.append({"role": "system", "content": ANCORA_ANTI_DRIFT})

            messages_payload.append({"role": "user", "content": mensagem_atual})

            t0 = time.time()
            completion = self._chamar_llm(messages_payload)
            elapsed = time.time() - t0
            log.info("IA completion ok em %.2fs (msgs=%d)", elapsed, len(messages_payload))

            response_text = completion.choices[0].message.content.strip()
            log.debug("IA raw response: %s", response_text[:300])

            if response_text.startswith("```json"):
                response_text = response_text[7:]
            elif response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            dados = json.loads(response_text)

            if "intencao" not in dados and "choices" in dados:
                inner = dados["choices"][0]["message"]["content"]
                dados = json.loads(inner) if isinstance(inner, str) else inner

            return self._validar_resposta(dados)

        except json.JSONDecodeError as e:
            log.error("Falha ao parsear JSON da IA: %s", e)
            self._registrar_erro_debug(f"[ERRO JSON] {e}\nTexto recebido: {response_text if 'response_text' in dir() else 'N/A'}")
            return {
                "intencao": "transbordo_falha",
                "resposta_sugerida": "Estou enfrentando uma instabilidade. Só um instante, estou conectando você à recepção para continuarmos."
            }
        except Exception as e:
            log.exception("Erro inesperado em processar_intencao")
            self._registrar_erro_debug(f"[ERRO AI SERVICE NVIDIA] {e}")
            return {
                "intencao": "transbordo_falha",
                "resposta_sugerida": "Tivemos um pequeno erro de comunicação. Aguarde um minuto e já te atendo!"
            }

    @staticmethod
    def _registrar_erro_debug(mensagem: str):
        """Append de erro com timestamp em erro_ia_debug.txt (não sobrescreve histórico)."""
        log_path = os.path.normpath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "erro_ia_debug.txt")
        )
        timestamp = datetime.now(timezone.utc).isoformat()
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n[{timestamp}] {mensagem}\n")
        except OSError:
            pass
