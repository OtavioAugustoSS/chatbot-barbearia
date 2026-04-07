import os
import json
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
from core.prompts import SYSTEM_PROMPT_BARBEARIA
from db.models import Servico, Barbeiro

class AIService:
    def __init__(self):
        # Configura o cliente da NVIDIA NIM usando o SDK da OpenAI
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.getenv("NVIDIA_API_KEY")
        )
        # O Llama 3.1 70B é excepcionalmente inteligente para JSON e conversas.
        self.model_name = "meta/llama-3.1-70b-instruct"
    
    def processar_intencao(self, db_session, historico_mensagens, mensagem_atual):
        """
        Busca o contexto atualizado do banco de dados, gera o prompt do sistema
        e processa a intenção e resposta do usuário usando a API da NVIDIA.
        """
        try:
            # 1. Busca no Banco: Recupera todos os serviços e barbeiros
            servicos = db_session.query(Servico).all()
            barbeiros = db_session.query(Barbeiro).all()

            # 2. Formatação dos Serviços
            lista_servicos = []
            for s in servicos:
                lista_servicos.append(
                    f"{s.nome_servico}: {s.descricao} | R$ {s.preco:.2f} | {s.tempo_estimado_minutos}min"
                )
            str_servicos = "\n".join(lista_servicos)

            # Formatação dos Barbeiros
            lista_barbeiros = []
            for b in barbeiros:
                nomes_servicos = [servico.nome_servico for servico in b.servicos]
                if nomes_servicos:
                    str_servicos_do_barbeiro = ", ".join(nomes_servicos)
                else:
                    str_servicos_do_barbeiro = "Nenhum serviço cadastrado"
                
                lista_barbeiros.append(f"{b.nome} ({b.dias_trabalho}) -> Especializa-se em: {str_servicos_do_barbeiro}")
            
            str_barbeiros = "\n".join(lista_barbeiros)

            # 3. Injeção no Prompt
            system_instruction = SYSTEM_PROMPT_BARBEARIA.format(
                lista_servicos_do_banco=str_servicos if str_servicos else "Nenhum serviço encontrado.",
                lista_barbeiros_do_banco=str_barbeiros if str_barbeiros else "Nenhum barbeiro encontrado."
            )

            # 4. Formatação de mensagens no padrão OpenAI/NVIDIA
            messages_payload = [{"role": "system", "content": system_instruction}]
            
            # Adiciona o histórico
            for msg in historico_mensagens:
                role = "assistant" if msg.get("role") in ["bot", "model", "assistant"] else "user"
                content = msg.get("content", "")
                messages_payload.append({"role": role, "content": content})
                
            # Adiciona a mensagem atual
            messages_payload.append({"role": "user", "content": mensagem_atual})

            # 5. Chamada à API
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages_payload,
                temperature=0.2,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            # 6. Parse e Retorno
            response_text = completion.choices[0].message.content
            dados = json.loads(response_text)
            
            return {
                "intencao": dados.get("intencao", "tirar_duvida"),
                "resposta_sugerida": dados.get("resposta_sugerida", "Erro interno. Como posso ajudar?"),
                "botoes": dados.get("botoes", [])
            }

        except json.JSONDecodeError as e:
            print(f"[ERRO JSON NVIDIA] Falha ao processar saida da IA: {e}")
            return {
                "intencao": "transbordo_falha",
                "resposta_sugerida": "Estou enfrentando uma instabilidade. Só um instante, estou conectando você à recepção para continuarmos.",
                "botoes": []
            }
        except Exception as e:
            erro_msg = f"[ERRO AI SERVICE NVIDIA] {e}"
            print(erro_msg)
            with open("erro_ia_debug.txt", "w", encoding="utf-8") as f:
                f.write(erro_msg)
            return {
                "intencao": "transbordo_falha",
                "resposta_sugerida": "Tivemos um pequeno erro de comunicação. Aguarde um minuto e já te atendo!",
                "botoes": []
            }
