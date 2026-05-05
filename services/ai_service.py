import os
import json
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
from sqlalchemy.orm import joinedload
from core.prompts import SYSTEM_PROMPT_BARBEARIA
from db.models import Servico, Barbeiro

class AIService:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.getenv("NVIDIA_API_KEY")
        )
        self.model_name = "meta/llama-3.1-70b-instruct"

    def processar_intencao(self, db_session, historico_mensagens, mensagem_atual, nome_cliente=None):
        try:
            # 1. Busca no Banco — ORDER BY garante ordem estável; joinedload evita N+1 queries
            servicos = db_session.query(Servico).order_by(Servico.categoria, Servico.id).all()
            barbeiros = (
                db_session.query(Barbeiro)
                .options(joinedload(Barbeiro.servicos))
                .order_by(Barbeiro.id)
                .all()
            )

            # 2. Formatação dos Serviços agrupados por categoria (determinístico, sem inferência da IA)
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

            # 3. Formatação dos Barbeiros
            lista_barbeiros = []
            for b in barbeiros:
                nomes_servicos = [servico.nome_servico for servico in b.servicos]
                str_servicos_do_barbeiro = ", ".join(nomes_servicos) if nomes_servicos else "Nenhum serviço cadastrado"
                lista_barbeiros.append(f"{b.nome} ({b.dias_trabalho}) -> Especializa-se em: {str_servicos_do_barbeiro}")
            str_barbeiros = "\n".join(lista_barbeiros) if lista_barbeiros else "Nenhum barbeiro encontrado."

            # 4. Injeção no Prompt
            system_instruction = SYSTEM_PROMPT_BARBEARIA.format(
                lista_servicos_do_banco=str_servicos,
                lista_barbeiros_do_banco=str_barbeiros
            )

            # 5. Montagem do payload
            messages_payload = [{"role": "system", "content": system_instruction}]

            # Nome do cliente como mensagem de sistema — não contamina a voz do usuário
            if nome_cliente:
                messages_payload.append({
                    "role": "system",
                    "content": f"O cliente atual se chama '{nome_cliente}'. Use o nome para personalizar o atendimento quando apropriado."
                })

            for msg in historico_mensagens:
                role = "assistant" if msg.get("role") in ["bot", "model", "assistant"] else "user"
                messages_payload.append({"role": role, "content": msg.get("content", "")})

            messages_payload.append({"role": "user", "content": mensagem_atual})

            # 6. Chamada à API
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages_payload,
                temperature=0.2,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )

            # 7. Parse e Retorno
            response_text = completion.choices[0].message.content.strip()
            print(f"[DEBUG IA RAW] {repr(response_text[:300])}")

            if response_text.startswith("```json"):
                response_text = response_text[7:]
            elif response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            dados = json.loads(response_text)

            # Suporte a resposta encapsulada ex: {"choices": [{"message": {"content": "{...}"}}]}
            if "intencao" not in dados and "choices" in dados:
                inner = dados["choices"][0]["message"]["content"]
                dados = json.loads(inner) if isinstance(inner, str) else inner

            return {
                "intencao": dados.get("intencao", "tirar_duvida"),
                "resposta_sugerida": dados.get("resposta_sugerida", "Erro interno. Como posso ajudar?")
            }

        except json.JSONDecodeError as e:
            print(f"[ERRO JSON NVIDIA] Falha ao processar saida da IA: {e}")
            log_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "erro_ia_debug.txt"))
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(f"[ERRO JSON] {e}\nTexto recebido: {response_text if 'response_text' in dir() else 'N/A'}")
            return {
                "intencao": "transbordo_falha",
                "resposta_sugerida": "Estou enfrentando uma instabilidade. Só um instante, estou conectando você à recepção para continuarmos."
            }
        except Exception as e:
            erro_msg = f"[ERRO AI SERVICE NVIDIA] {e}"
            print(erro_msg)
            log_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "erro_ia_debug.txt"))
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(erro_msg)
            return {
                "intencao": "transbordo_falha",
                "resposta_sugerida": "Tivemos um pequeno erro de comunicação. Aguarde um minuto e já te atendo!"
            }
