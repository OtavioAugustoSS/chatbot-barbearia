import os
import json
import google.generativeai as genai
from core.prompts import SYSTEM_PROMPT_BARBEARIA
from db.models import Servico, Barbeiro

# Configura a chave de API do Gemini lendo diretamente do ambiente (.env carregado no main)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

class AIService:
    def __init__(self):
        # Configura o modelo. A versão 2.0-flash é a versão atual da API.
        # Mantém rapidez para chat e alta qualidade no parse JSON.
        self.model_name = "gemini-2.0-flash"
    
    def processar_intencao(self, db_session, historico_mensagens, mensagem_atual):
        """
        Busca o contexto atualizado do banco de dados, gera o prompt do sistema
        e processa a intenção e resposta do usuário usando a API do Gemini.
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

            # Formatação dos Barbeiros (usando a tabela associativa / relationship)
            lista_barbeiros = []
            for b in barbeiros:
                # O relacionamento `b.servicos` já mapeia os objetos Servico vinculados
                nomes_servicos = [servico.nome_servico for servico in b.servicos]
                
                # Formata a string baseada na lista de serviços
                if nomes_servicos:
                    str_servicos_do_barbeiro = ", ".join(nomes_servicos)
                else:
                    str_servicos_do_barbeiro = "Nenhum serviço cadastrado"
                
                lista_barbeiros.append(f"{b.nome} ({b.dias_trabalho}) -> Especializa-se em: {str_servicos_do_barbeiro}")
            
            str_barbeiros = "\n".join(lista_barbeiros)

            # 3. Injeção no Prompt: Usa o .format para colocar os textos onde temos as chaves
            system_instruction = SYSTEM_PROMPT_BARBEARIA.format(
                lista_servicos_do_banco=str_servicos if str_servicos else "Nenhum serviço encontrado.",
                lista_barbeiros_do_banco=str_barbeiros if str_barbeiros else "Nenhum barbeiro encontrado."
            )

            # 4. Chamada da API: Instancia o modelo forçando JSON e o System Prompt
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_instruction,
                generation_config={"response_mime_type": "application/json"}
            )
            
            # Formata histórico_mensagens. Assume-se que seja um formato padrão que o seu sistema de 
            # rotas/histórico envia: [{"role": "user", "content": "olá"}]
            # O Gemini requere [{"role": "user", "parts": ["olá"]}] e 'model' para si mesmo.
            formato_historico = []
            for msg in historico_mensagens:
                # O papel do bot para o gemini é 'model'
                papel = "model" if msg.get("role") in ["bot", "model", "assistant"] else "user"
                formato_historico.append({
                    "role": papel,
                    "parts": [msg.get("content", "")]
                })
            
            # Inicia o chat enviando o histórico
            chat = model.start_chat(history=formato_historico)
            
            # Envia a mensagem atual do usuário
            response = chat.send_message(mensagem_atual)
            
            # 5. Parse e Retorno: Lê a resposta crua e transforma nativamente no JSON dicionário base
            dados = json.loads(response.text)
            
            return {
                "intencao": dados.get("intencao", "falar_com_humano"),
                "resposta_sugerida": dados.get("resposta_sugerida", "Irei te passar para o suporte.")
            }

        except json.JSONDecodeError as e:
            # Forçar falha segura caso o JSON venha mal formatado (Apesar da chave response_mime_type proteger bem sobre isso)
            print(f"[ERRO JSON Gemini] Falha ao processar saida da IA: {e}")
            return {
                "intencao": "transbordo_falha",
                "resposta_sugerida": "Estou enfrentando uma instabilidade. Só um instante, estou conectando você à recepção para continuarmos."
            }
        except Exception as e:
            # Qualquer outra exceção genérica da API offline, timeout, ou erro de sessão DB
            print(f"[ERRO AI SERVICE] {e}")
            return {
                "intencao": "transbordo_falha",
                "resposta_sugerida": "Tivemos um pequeno erro de comunicação. Aguarde um minuto e já te atendo!"
            }
