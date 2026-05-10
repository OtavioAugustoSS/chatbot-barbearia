import os
import re
import json
import time
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
from sqlalchemy.orm import joinedload
from core.prompts import SYSTEM_PROMPT_BARBEARIA, ANCORA_ANTI_DRIFT
from db.models import Servico, Barbeiro

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

        servicos = db_session.query(Servico).order_by(Servico.categoria, Servico.id).all()
        barbeiros = (
            db_session.query(Barbeiro)
            .options(joinedload(Barbeiro.servicos))
            .order_by(Barbeiro.id)
            .all()
        )

        def _linha_servico(s):
            return f"✂️ {s.nome_servico}: {s.descricao} | R$ {s.preco:.2f} | {s.tempo_estimado_minutos}min"

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

            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages_payload,
                temperature=0.0,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )

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
