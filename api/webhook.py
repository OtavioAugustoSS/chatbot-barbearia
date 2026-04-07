import os
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Usuario, HistoricoConversa
from services.whatsapp import WhatsAppSender, extrair_informacoes_mensagem
from services.ai_service import AIService

router = APIRouter()
whatsapp = WhatsAppSender()
ai_service = AIService()

# Puxe do .env ou mantenha um genérico por padrão de validação do Facebook
VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "barbearia_bot_123")

@router.get("/webhook")
async def verify_webhook(request: Request):
    """ Rota oficial para o Facebook garantir que nós somos donos deste endpoint """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            # O FB requere que você retorne exatamente a string em texto-plano, não em JSON
            return PlainTextResponse(challenge)
            
    raise HTTPException(status_code=403, detail="Token inválido")

@router.post("/webhook")
async def receive_message(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    telefone, texto_cliente = extrair_informacoes_mensagem(body)
    
    # 1. Validação inicial e Bloqueio de mídia
    if not telefone or not texto_cliente:
        return {"status": "ok"} # Reconhecer mensagens mudas e evitar loops

    if str(texto_cliente).startswith("MÍDIA_"):
        whatsapp.enviar_mensagem_texto(telefone, "🤖 Desculpe, mas eu ainda sou um bot aprendendo e não consigo ouvir áudios nem ler fotos. Em que posso te ajudar escrevendo?")
        return {"status": "ok"}

    # 2. Busca ou Criação de Usuário
    user = db.query(Usuario).filter(Usuario.telefone == telefone).first()
    if not user:
        user = Usuario(telefone=telefone, bot_ativo=True)
        db.add(user)
        db.commit()
        db.refresh(user)

    # 3. Trava Humana (Transbordo)
    if not user.bot_ativo:
        # Comando secreto para destrancar o bot nos testes
        if str(texto_cliente).strip().lower() == "!reiniciar":
            user.bot_ativo = True
            db.commit()
            whatsapp.enviar_mensagem_texto(telefone, "🤖 Bot manual destravado! Meu cérebro foi religado pelo Administrador. Como posso ajudar?")
            return {"status": "ok"}
        
        # Se a IA desligou, significa que o atendente já puxou a conversa
        return {"status": "ok", "detail": "Bot está inativo para este usuário. Interação manual assumida."}

    # 4. Interação direta por Botões (Bypass da IA)
    if texto_cliente == "btn_agendar":
        whatsapp.enviar_mensagem_texto(telefone, "Perfeito! Para agendar o seu horário online agora mesmo, acesse o nosso aplicativo: [LINK_DO_APPBARBER]")
        return {"status": "ok"}
        
    if texto_cliente == "btn_humano":
        user.bot_ativo = False
        db.commit()
        whatsapp.enviar_mensagem_texto(telefone, "Tudo bem! Estou te direcionando para a nossa recepção real. Aguarde só um diazinho que já chegam até você!")
        return {"status": "ok"}

    # 5. Processamento de NLP (Inteligência Artificial)
    # Puxar o histórico
    historico = db.query(HistoricoConversa).filter(
        HistoricoConversa.telefone_usuario == telefone
    ).order_by(HistoricoConversa.criado_em.desc()).limit(5).all()
    
    # Inverte do mais antigo pro mais novo para enviar pro ChatGPT/Gemini
    historico.reverse()
    
    contexto_mensagens = []
    for h in historico:
        if h.mensagem_cliente:
            contexto_mensagens.append({"role": "user", "content": h.mensagem_cliente})
        if h.resposta_bot:
            contexto_mensagens.append({"role": "model", "content": h.resposta_bot})

    # Analisar com Gemini
    resultado_ia = ai_service.processar_intencao(db, contexto_mensagens, texto_cliente)
    intencao = resultado_ia.get("intencao")
    resposta_texto = resultado_ia.get("resposta_sugerida", "Erro ao gerar resposta.")

    # 6. Salvar interações no Banco
    novo_historico = HistoricoConversa(
        telefone_usuario=telefone,
        mensagem_cliente=texto_cliente,
        resposta_bot=resposta_texto
    )
    db.add(novo_historico)
    db.commit()

    # 7. Roteamento de Resposta Baseado no JSON da API
    if intencao == "falar_com_humano" or intencao == "transbordo_falha":
        user.bot_ativo = False
        db.commit()
        whatsapp.enviar_mensagem_texto(telefone, resposta_texto)
        return {"status": "ok"}

    if intencao == "agendar_horario":
        # A própria IA já gerou a resposta de agendamento usando o System Prompt!
        whatsapp.enviar_mensagem_texto(telefone, resposta_texto)
        return {"status": "ok"}
        
    # Default: "tirar_duvida", "saudacao", encampar com botões de Call To Action
    botoes_apelo_acao = [
        {"type": "reply", "reply": {"id": "btn_agendar", "title": "Agendar Horário"}},
        {"type": "reply", "reply": {"id": "btn_humano", "title": "Falar c/ Recepção"}}
    ]
    whatsapp.enviar_mensagem_botoes(telefone, f"{resposta_texto}\n\nComo deseja prosseguir?", botoes_apelo_acao)
    
    return {"status": "ok"}
