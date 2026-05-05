import os
import re
import time
import threading
from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from db.database import get_db, SessionLocal
from db.models import Usuario, HistoricoConversa
from services.whatsapp import WhatsAppSender, extrair_informacoes_mensagem
from services.ai_service import AIService

MENSAGEM_BOAS_VINDAS = (
    "Olá, seja muito bem-vindo à Barbearia Bolshoi! 💈\n"
    "Eu sou o seu assistente virtual.\n\n"
    "Para agilizarmos seu atendimento, pode me consultar diretamente sobre:\n"
    "✂️ Nossos Serviços e Preços\n"
    "👨‍🎨 Nossa Equipe de Barbeiros\n"
    "📅 Agendamento de Horários\n"
    "📍 Localização e Funcionamento\n"
    "❓ Dúvidas Frequentes\n\n"
    "Em que posso ser útil hoje?"
)

MENSAGEM_MENU_REPETIDO = (
    "Claro! Posso te ajudar com:\n\n"
    "✂️ Nossos Serviços e Preços\n"
    "👨‍🎨 Nossa Equipe de Barbeiros\n"
    "📅 Agendamento de Horários\n"
    "📍 Localização e Funcionamento\n"
    "❓ Dúvidas Frequentes\n\n"
    "Sobre qual desses tópicos você gostaria de saber?"
)

# Detecta pedidos do menu de capacidades (sem usar a IA, garante padrão visual fixo).
_PADROES_PEDIDO_MENU = re.compile(
    r"\b("
    r"menu|"
    r"opc[oõ]es|opções|"
    r"o\s*que\s+(voc[eê]|vc|tu)\s+(faz|pode|consegue|sabe)|"
    r"o\s*que\s+(voc[eê]|vc|tu)?\s*(pode|consegue)\s+(fazer|me\s+ajudar)|"
    r"em\s+que\s+(pode|consegue)\s+(me\s+)?ajudar|"
    r"como\s+(voc[eê]|vc|tu)\s+(funciona|pode\s+ajudar)|"
    r"o\s*que\s+(voc[eê]|vc|tu)\s+oferece|"
    r"capacidades|"
    r"t[oó]picos"
    r")\b",
    re.IGNORECASE,
)

def _e_pedido_de_menu(texto: str) -> bool:
    """Detecta se o cliente está pedindo de novo o menu/lista de capacidades do bot."""
    return bool(_PADROES_PEDIDO_MENU.search(texto))

router = APIRouter()
whatsapp = WhatsAppSender()
ai_service = AIService()

# Garante processamento sequencial por usuário: evita que duas mensagens
# rápidas do mesmo telefone sejam processadas em paralelo e gerem respostas
# fora de ordem ou com histórico duplicado.
_locks_por_telefone: dict[str, threading.Lock] = {}
_meta_lock = threading.Lock()

# Dedupe de message.id da Meta — quando a Meta acha que não recebeu o ACK
# rápido o suficiente, ela RETRANSMITE o webhook com o mesmo message.id.
# Sem dedupe, isso gera múltiplas respostas para a mesma mensagem do cliente.
_mensagens_processadas: dict[str, float] = {}
_dedupe_lock = threading.Lock()
_DEDUPE_TTL_SEGUNDOS = 600  # 10 minutos é suficiente para cobrir todos os retries da Meta

def _ja_processada(message_id: str) -> bool:
    """True se message_id já foi processada nos últimos 10 min. Caso contrário, registra e retorna False."""
    agora = time.time()
    with _dedupe_lock:
        # Limpa entradas antigas (cheap, roda por chamada)
        expirados = [mid for mid, ts in _mensagens_processadas.items() if agora - ts > _DEDUPE_TTL_SEGUNDOS]
        for mid in expirados:
            del _mensagens_processadas[mid]

        if message_id in _mensagens_processadas:
            return True
        _mensagens_processadas[message_id] = agora
        return False

def _lock_do_telefone(telefone: str) -> threading.Lock:
    with _meta_lock:
        if telefone not in _locks_por_telefone:
            _locks_por_telefone[telefone] = threading.Lock()
        return _locks_por_telefone[telefone]

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
    with _lock_do_telefone(telefone):
        _processar_mensagem(telefone, texto_cliente)

def _processar_mensagem(telefone: str, texto_cliente: str):
    db = SessionLocal()
    try:
        # Puxamos o usuario no DB dessa sessão avulsa
        user = db.query(Usuario).filter(Usuario.telefone == telefone).first()
        if not user or not user.bot_ativo:
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
                # Injeta na IA com \n para leitura limpa, não com <br>
                contexto_mensagens.append({"role": "model", "content": h.resposta_bot.replace("<br>", "\n")})

        # Primeiro contato (histórico vazio) → SEMPRE entrega o menu de onboarding,
        # independentemente do que o cliente digitou. A IA só assume a partir da 2ª mensagem.
        if not historico:
            novo_historico = HistoricoConversa(
                telefone_usuario=telefone,
                mensagem_cliente=texto_cliente,
                resposta_bot=MENSAGEM_BOAS_VINDAS.replace("\n", "<br>")
            )
            db.add(novo_historico)
            db.commit()
            whatsapp.enviar_mensagem_texto(telefone, MENSAGEM_BOAS_VINDAS)
            return

        # Cliente pedindo o menu/capacidades de novo → texto fixo (mesmo padrão visual da boas-vindas).
        # Evita que a IA regenere o menu com emojis e palavras diferentes a cada pedido.
        if _e_pedido_de_menu(texto_cliente):
            novo_historico = HistoricoConversa(
                telefone_usuario=telefone,
                mensagem_cliente=texto_cliente,
                resposta_bot=MENSAGEM_MENU_REPETIDO.replace("\n", "<br>")
            )
            db.add(novo_historico)
            db.commit()
            whatsapp.enviar_mensagem_texto(telefone, MENSAGEM_MENU_REPETIDO)
            return

        # Processar IA Pesada
        resultado_ia = ai_service.processar_intencao(db, contexto_mensagens, texto_cliente, user.nome_cliente)
        intencao = resultado_ia.get("intencao")
        
        resposta_bruta = resultado_ia.get("resposta_sugerida", "Tivemos um problema processando sua solicitação.")

        # Salva no banco com <br> para manter consistência com o contexto que a IA recebe
        novo_historico = HistoricoConversa(
            telefone_usuario=telefone,
            mensagem_cliente=texto_cliente,
            resposta_bot=resposta_bruta
        )
        db.add(novo_historico)
        db.commit()

        # Poda automática: mantém apenas os últimos 20 registros por usuário
        contagem = db.query(HistoricoConversa).filter(
            HistoricoConversa.telefone_usuario == telefone
        ).count()
        if contagem > 20:
            ids_manter = [
                row.id for row in
                db.query(HistoricoConversa.id)
                .filter(HistoricoConversa.telefone_usuario == telefone)
                .order_by(HistoricoConversa.criado_em.desc())
                .limit(20)
                .all()
            ]
            db.query(HistoricoConversa).filter(
                HistoricoConversa.telefone_usuario == telefone,
                ~HistoricoConversa.id.in_(ids_manter)
            ).delete(synchronize_session=False)
            db.commit()

        # Converte <br> para \n apenas na hora do envio ao WhatsApp.
        # A IA às vezes devolve variações como "<BR>", "< br >", "\\n", "<br/>"
        # — normalizamos tudo para \n real para garantir quebra de linha no WhatsApp.
        resposta_texto = resposta_bruta
        resposta_texto = re.sub(r"<\s*br\s*/?\s*>", "\n", resposta_texto, flags=re.IGNORECASE)
        resposta_texto = resposta_texto.replace("\\n", "\n")
        # Colapsa 3+ quebras seguidas em duas (evita bloco com excesso de espaços vazios)
        resposta_texto = re.sub(r"\n{3,}", "\n\n", resposta_texto).strip()

        print(f"[DEBUG ENVIO] Texto final ({len(resposta_texto)} chars): {repr(resposta_texto)}")

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
    telefone, texto_cliente, nome_cliente, message_id = extrair_informacoes_mensagem(body)

    if not telefone or not texto_cliente:
        return {"status": "ok"}

    # Dedupe: a Meta retransmite o webhook quando acha que não recebeu o ACK.
    # Sem isso, o cliente recebe a mesma resposta 2-4 vezes.
    if message_id and _ja_processada(message_id):
        print(f"⏭️  [DEDUPE] message_id {message_id} já processado, ignorando retry da Meta.")
        return {"status": "ok"}

    if str(texto_cliente).startswith("MÍDIA_"):
        background_tasks.add_task(
            whatsapp.enviar_mensagem_texto,
            telefone,
            "🤖 Desculpe, mas eu ainda sou um bot aprendendo e não consigo ouvir áudios nem ler fotos. Em que posso te ajudar escrevendo?"
        )
        return {"status": "ok"}

    # Busca ou Criação de Usuário e Salva o Nome se fornecido
    user = db.query(Usuario).filter(Usuario.telefone == telefone).first()
    if not user:
        user = Usuario(telefone=telefone, nome_cliente=nome_cliente, bot_ativo=True)
        db.add(user)
        db.commit()
        db.refresh(user)
    elif nome_cliente and user.nome_cliente != nome_cliente:
        user.nome_cliente = nome_cliente
        db.commit()

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
