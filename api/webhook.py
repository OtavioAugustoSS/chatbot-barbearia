import os
import json
from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from db.database import get_db, SessionLocal
from db.models import Usuario, HistoricoConversa
from services.whatsapp import WhatsAppSender, extrair_informacoes_mensagem
from services.ai_service import AIService

router = APIRouter()
whatsapp = WhatsAppSender()
ai_service = AIService()

VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "barbearia_bot_123")

@router.get("/webhook")
async def verify_webhook(request: Request):
    """ Rota oficial para o Facebook garantir que nós somos donos deste endpoint """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return PlainTextResponse(challenge)
            
    raise HTTPException(status_code=403, detail="Token inválido")

def tarefa_em_segundo_plano_ia(telefone: str, texto_cliente: str):
    """ Essa função roda solta no fundo, dando todo tempo do mundo para a IA pensar sem travar o Facebook """
    db = SessionLocal()
    try:
        # Puxamos o usuario no DB dessa sessão avulsa
        user = db.query(Usuario).filter(Usuario.telefone == telefone).first()
        if not user:
            return

        # Puxar o histórico
        historico = db.query(HistoricoConversa).filter(
            HistoricoConversa.telefone_usuario == telefone
        ).order_by(HistoricoConversa.criado_em.desc()).limit(5).all()
        
        historico.reverse()
        
        contexto_mensagens = []
        for h in historico:
            if h.mensagem_cliente:
                contexto_mensagens.append({"role": "user", "content": h.mensagem_cliente})
            if h.resposta_bot:
                contexto_mensagens.append({"role": "model", "content": h.resposta_bot})

        # Processar IA Pesada
        resultado_ia = ai_service.processar_intencao(db, contexto_mensagens, texto_cliente)
        intencao = resultado_ia.get("intencao")
        
        resposta_bruta = resultado_ia.get("resposta_sugerida", "Tivemos um problema processando sua solicitação.")
        resposta_texto = resposta_bruta.replace("<br>", "\n")

        # Salvar interações no Banco
        novo_historico = HistoricoConversa(
            telefone_usuario=telefone,
            mensagem_cliente=texto_cliente,
            resposta_bot=resposta_texto
        )
        db.add(novo_historico)
        db.commit()

        # 8. Roteamento baseado na Intenção
        if intencao == "chamar_recepcao" or intencao == "transbordo_falha":
            user.bot_ativo = False
            db.commit()
            whatsapp.enviar_mensagem_texto(telefone, resposta_texto)
            return

        # Caminho 1: 100% Conversacional. Enviamos direto o texto limpo da IA.
        whatsapp.enviar_mensagem_texto(telefone, resposta_texto)

    finally:
        db.close()


@router.post("/webhook")
async def receive_message(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    body = await request.json()
    telefone, texto_cliente = extrair_informacoes_mensagem(body)
    
    if not telefone or not texto_cliente:
        return {"status": "ok"} 

    if str(texto_cliente).startswith("MÍDIA_"):
        whatsapp.enviar_mensagem_texto(telefone, "🤖 Desculpe, mas eu ainda sou um bot aprendendo e não consigo ouvir áudios nem ler fotos. Em que posso te ajudar escrevendo?")
        return {"status": "ok"}

    # Busca ou Criação de Usuário
    user = db.query(Usuario).filter(Usuario.telefone == telefone).first()
    if not user:
        user = Usuario(telefone=telefone, bot_ativo=True)
        db.add(user)
        db.commit()
        db.refresh(user)

    # 1. Comandos Diretos de Bypass (Resolvemos na hora)
    if str(texto_cliente).strip().lower() == "!reiniciar":
        user.bot_ativo = True
        # Limpar o histórico da IA para o bot esquecer conversas velhas e formatos velhos
        db.query(HistoricoConversa).filter(HistoricoConversa.telefone_usuario == telefone).delete()
        db.commit()
        whatsapp.enviar_mensagem_texto(telefone, "🤖 Bot manual reiniciado! A memória do meu cérebro foi totalmente limpa. Como posso ajudar?")
        return {"status": "ok"}

    # Trava Humana (Transbordo)
    if not user.bot_ativo:
        print(f"🔒 [MSG IGNORADA] Usuário {telefone} está com Trava Humana ativa.")
        return {"status": "ok"}

    # Transbordo pelo Botão
    if texto_cliente == "🙋 Falar c/ Recepção":
        user.bot_ativo = False
        db.commit()
        whatsapp.enviar_mensagem_texto(telefone, "Tudo bem! Estou te direcionando para a nossa recepção real. Pode mandar sua dúvida aqui que um atendente vai assumir!")
        return {"status": "ok"}
    
    # IMPORTANTE: Enviamos a IA para rodar "em segundo plano" 
    # e devolvemos OK imediato para o Facebook parar de duplicar
    print(f"-> Enviando para IA em 2º plano. Mensagem: {telefone} diz '{texto_cliente}'")
    background_tasks.add_task(tarefa_em_segundo_plano_ia, telefone, texto_cliente)
    
    return {"status": "ok"}
