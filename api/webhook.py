import os
import re
import time
import hmac
import hashlib
import logging
import threading
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from db.database import get_db, SessionLocal
from db.models import Usuario, HistoricoConversa, MensagemProcessada
from services.whatsapp import WhatsAppSender, extrair_informacoes_mensagem
from services.ai_service import AIService
from core.respostas_canonicas import detectar_resposta_canonica

log = logging.getLogger("barbearia.webhook")

META_APP_SECRET = os.getenv("META_APP_SECRET", "").encode("utf-8")
ADMIN_PHONES = {p.strip() for p in os.getenv("ADMIN_PHONES", "").split(",") if p.strip()}
BOT_REATIVAR_APOS_HORAS = int(os.getenv("BOT_REATIVAR_APOS_HORAS", "24"))
RATE_LIMIT_MSGS_POR_MINUTO = int(os.getenv("RATE_LIMIT_MSGS_POR_MINUTO", "10"))


def _validar_assinatura_meta(raw_body: bytes, header_signature: str | None) -> bool:
    """Verifica HMAC-SHA256 de payload Meta. Sem META_APP_SECRET configurado, devolve True (modo dev)."""
    if not META_APP_SECRET:
        log.warning("META_APP_SECRET não configurado - assinatura webhook não verificada (modo dev).")
        return True
    if not header_signature or not header_signature.startswith("sha256="):
        return False
    esperado = hmac.new(META_APP_SECRET, raw_body, hashlib.sha256).hexdigest()
    recebido = header_signature.split("=", 1)[1]
    return hmac.compare_digest(esperado, recebido)

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

# Locks por telefone com TTL: limpa entradas antigas pra evitar crescimento ilimitado.
_locks_por_telefone: dict[str, tuple[threading.Lock, float]] = {}
_meta_lock = threading.Lock()
_LOCK_TTL_SEGUNDOS = 1800  # 30min sem uso → lock descartado

# Rate limit por telefone: deque de timestamps das últimas mensagens.
_janela_rate_limit: dict[str, list[float]] = {}
_rate_lock = threading.Lock()
_DEDUPE_TTL_SEGUNDOS = 600  # cobre retries da Meta

def _ja_processada(db: Session, message_id: str) -> bool:
    """
    Dedupe persistente em DB. Sobrevive a restart do servidor.
    True se message_id já foi processado; caso contrário registra e devolve False.
    """
    if not message_id:
        return False
    try:
        existente = db.query(MensagemProcessada).filter(MensagemProcessada.message_id == message_id).first()
        if existente:
            return True
        db.add(MensagemProcessada(message_id=message_id))
        db.commit()

        # Limpeza oportunista: 1% das chamadas remove registros expirados.
        import random
        if random.random() < 0.01:
            limite = datetime.now(timezone.utc) - timedelta(seconds=_DEDUPE_TTL_SEGUNDOS * 2)
            db.query(MensagemProcessada).filter(MensagemProcessada.processada_em < limite).delete()
            db.commit()
        return False
    except Exception:
        log.exception("Erro no dedupe DB - permitindo passagem.")
        db.rollback()
        return False


def _excedeu_rate_limit(telefone: str) -> bool:
    """True se o telefone enviou mais de RATE_LIMIT_MSGS_POR_MINUTO mensagens nos últimos 60s."""
    agora = time.time()
    with _rate_lock:
        janela = _janela_rate_limit.setdefault(telefone, [])
        janela[:] = [t for t in janela if agora - t < 60]
        if len(janela) >= RATE_LIMIT_MSGS_POR_MINUTO:
            return True
        janela.append(agora)
        # Limpeza periódica do dict inteiro
        if len(_janela_rate_limit) > 1000:
            inativos = [k for k, v in _janela_rate_limit.items() if not v or agora - v[-1] > 300]
            for k in inativos:
                del _janela_rate_limit[k]
        return False


def _lock_do_telefone(telefone: str) -> threading.Lock:
    """Lock por telefone com TTL: entradas inativas há mais de 30min são descartadas."""
    agora = time.time()
    with _meta_lock:
        # Limpeza oportunista
        expirados = [tel for tel, (_, ts) in _locks_por_telefone.items() if agora - ts > _LOCK_TTL_SEGUNDOS]
        for tel in expirados:
            del _locks_por_telefone[tel]

        existente = _locks_por_telefone.get(telefone)
        if existente:
            _locks_por_telefone[telefone] = (existente[0], agora)
            return existente[0]
        novo = threading.Lock()
        _locks_por_telefone[telefone] = (novo, agora)
        return novo


def _verificar_e_reativar_bot(db: Session, user: Usuario) -> bool:
    """
    Se bot foi desativado há mais de BOT_REATIVAR_APOS_HORAS, reativa automaticamente.
    Devolve True se bot está ativo após verificação.
    """
    if user.bot_ativo:
        return True
    if not user.bot_desativado_em:
        return False
    desativado_em = user.bot_desativado_em
    if desativado_em.tzinfo is None:
        desativado_em = desativado_em.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - desativado_em > timedelta(hours=BOT_REATIVAR_APOS_HORAS):
        user.bot_ativo = True
        user.bot_desativado_em = None
        db.commit()
        log.info("Bot reativado automaticamente para %s após %sh.", user.telefone, BOT_REATIVAR_APOS_HORAS)
        return True
    return False


def _desativar_bot(db: Session, user: Usuario):
    """Desativa bot e marca timestamp para reativação automática."""
    user.bot_ativo = False
    user.bot_desativado_em = datetime.now(timezone.utc)
    db.commit()

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

        # Janela de contexto: últimas 15 trocas. Mais memória sem inflar tokens demais.
        historico = db.query(HistoricoConversa).filter(
            HistoricoConversa.telefone_usuario == telefone
        ).order_by(HistoricoConversa.criado_em.desc()).limit(15).all()

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

        # FAQ canônico: horário, endereço, agendamento, pagamento, estrutura.
        # Bypass de IA → custo zero, zero alucinação, formato sempre idêntico.
        resposta_canonica = detectar_resposta_canonica(texto_cliente)
        if resposta_canonica:
            novo_historico = HistoricoConversa(
                telefone_usuario=telefone,
                mensagem_cliente=texto_cliente,
                resposta_bot=resposta_canonica,
            )
            db.add(novo_historico)
            db.commit()
            texto_envio = re.sub(r"<\s*br\s*/?\s*>", "\n", resposta_canonica, flags=re.IGNORECASE).strip()
            whatsapp.enviar_mensagem_texto(telefone, texto_envio)
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

        # Poda automática: mantém últimos 50 registros por usuário (janela do contexto = 15).
        contagem = db.query(HistoricoConversa).filter(
            HistoricoConversa.telefone_usuario == telefone
        ).count()
        if contagem > 50:
            ids_manter = [
                row.id for row in
                db.query(HistoricoConversa.id)
                .filter(HistoricoConversa.telefone_usuario == telefone)
                .order_by(HistoricoConversa.criado_em.desc())
                .limit(50)
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

        log.debug("Envio WhatsApp (%d chars) para %s", len(resposta_texto), telefone)

        if intencao == "chamar_recepcao" or intencao == "transbordo_falha":
            _desativar_bot(db, user)
            whatsapp.enviar_mensagem_texto(telefone, resposta_texto)
            return

        whatsapp.enviar_mensagem_texto(telefone, resposta_texto)

    finally:
        db.close()



@router.post("/webhook")
async def receive_message(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    if not _validar_assinatura_meta(raw_body, signature):
        log.error("Assinatura Meta inválida - request rejeitado.")
        raise HTTPException(status_code=403, detail="Assinatura inválida")

    import json as _json
    try:
        body = _json.loads(raw_body)
    except _json.JSONDecodeError:
        return {"status": "ok"}

    telefone, texto_cliente, nome_cliente, message_id = extrair_informacoes_mensagem(body)

    if not telefone or not texto_cliente:
        return {"status": "ok"}

    # Dedupe persistente: Meta retransmite quando não recebe ACK rápido. Sem isso, cliente
    # recebe resposta duplicada. Persistido em DB → sobrevive a restart.
    if message_id and _ja_processada(db, message_id):
        log.info("Dedupe: message_id %s já processado, ignorando retransmissão.", message_id)
        return {"status": "ok"}

    if str(texto_cliente).startswith("MÍDIA_"):
        background_tasks.add_task(
            whatsapp.enviar_mensagem_texto,
            telefone,
            "🤖 Desculpe, mas eu ainda sou um bot aprendendo e não consigo ouvir áudios nem ler fotos. Em que posso te ajudar escrevendo?"
        )
        return {"status": "ok"}

    # Rate limit: protege contra flood (DoS / fatura inflada).
    if _excedeu_rate_limit(telefone):
        log.warning("Rate limit excedido para %s.", telefone)
        return {"status": "ok"}

    user = db.query(Usuario).filter(Usuario.telefone == telefone).first()
    if not user:
        user = Usuario(telefone=telefone, nome_cliente=nome_cliente, bot_ativo=True)
        db.add(user)
        db.commit()
        db.refresh(user)
    elif nome_cliente and user.nome_cliente != nome_cliente:
        user.nome_cliente = nome_cliente
        db.commit()

    # !reiniciar: comando de admin. Cliente comum não pode limpar próprio histórico.
    if str(texto_cliente).strip().lower() == "!reiniciar":
        if telefone not in ADMIN_PHONES:
            log.warning("Tentativa de !reiniciar por telefone não-admin: %s", telefone)
            return {"status": "ok"}
        user.bot_ativo = True
        user.bot_desativado_em = None
        db.query(HistoricoConversa).filter(HistoricoConversa.telefone_usuario == telefone).delete()
        db.commit()
        whatsapp.enviar_mensagem_texto(telefone, "🤖 Bot reiniciado por admin. Memória limpa.")
        return {"status": "ok"}

    # Reativação automática do bot após N horas sem atividade humana.
    bot_ativo = _verificar_e_reativar_bot(db, user)
    if not bot_ativo:
        log.info("Mensagem ignorada: bot desativado para %s (transbordo humano em curso).", telefone)
        return {"status": "ok"}

    if texto_cliente == "🙋 Falar c/ Recepção":
        _desativar_bot(db, user)
        whatsapp.enviar_mensagem_texto(telefone, "Tudo bem! Estou te direcionando para a nossa recepção real. Pode mandar sua dúvida aqui que um atendente vai assumir!")
        return {"status": "ok"}

    log.info("Enfileirando IA: %s → %r", telefone, texto_cliente[:80])
    background_tasks.add_task(tarefa_em_segundo_plano_ia, telefone, texto_cliente)

    return {"status": "ok"}
