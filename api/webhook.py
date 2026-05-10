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
from services.notificador import notificador
from core.respostas_canonicas import detectar_resposta_canonica
from core.config import MODO_HIBRIDO, MODO_BOT_ONLY

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


def _montar_saudacao(nome_cliente: str | None) -> str:
    """
    Resposta determinística para saudações puras. Personaliza com primeiro nome
    quando o WhatsApp entregou nome do cliente; senão usa abertura genérica.
    Sem IA, sem variação — formato idêntico em toda chamada.
    """
    primeiro = ""
    if nome_cliente:
        partes = nome_cliente.strip().split()
        if partes:
            primeiro = partes[0]
    abertura = f"Olá, {primeiro}! " if primeiro else "Olá! "
    return (
        f"{abertura}Posso te ajudar com:\n\n"
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


# Saudações puras (mensagem inteira é só cumprimento, sem pergunta específica).
# Regex ancorado em ^...$ para garantir match completo. Casos como
# "oi qual o horário?" NÃO casam (porque "qual" não é saudação) — caem
# em respostas_canonicas ou IA, evitando perda de intenção.
_TOKEN_SAUDACAO = (
    r"(?:"
    r"oi+e?|oii+|ol[aá]+|ei+|hey+|hi+|hello+|"
    r"opa+|op[ae]+|eae+|e\s*ae+|aee+|"
    r"e\s*a[ií]+|iai+|fala+|"
    r"salve+|al[oôó]+|"
    r"bom\s+dia|boa\s+tarde|boa\s+noite|bnoite|btarde|bdia|"
    r"tudo\s+(?:bem|bom|certo|tranquilo|tranquilao|joia|jóia|na\s+paz)|"
    r"td\s+(?:bem|bom|certo)|"
    r"blz|beleza|tranquil[ao]|de\s+boa|"
    r"como\s+(?:vai|est[aá]|voc[eê]\s+est[aá]|t[aá]|tem\s+passado)"
    r")"
)
# Vocativos/modificadores informais (PT-BR coloquial). Aparecem APÓS uma saudação:
# "eai meu fi", "salve mano", "opa fera", "oi tio", "fala chefe", etc.
_TOKEN_MODIFICADOR = (
    r"(?:"
    r"meu\s+(?:fi|fih|filho|irm[aã]o|amigo|querido|nego|chap[ae]|chapa)|"
    r"mano|man[ao]|fera|fer[ao]|par[çc]a|parsa|brother|bro|"
    r"irm[aã]o|irm[aã]os|amigo|amig[ao]|amigão|amigaum|"
    r"querid[ao]|nego|n[eé]ga|v[eé]i|v[eé]io|v[eé]ia|"
    r"cara|tio|tia|chefe|chefia|rapaz|rapaziada|"
    r"gente|galera|tropa|moç[ao]|bonit[ao]|"
    r"garot[ao]|menin[ao]|maluc[ao]|"
    r"fi|fih"
    r")"
)
# Saudação pura: começa com greeting, opcionalmente seguido de mais greetings ou
# modificadores. Pega "eai meu fi", "fala mano", "salve fera" etc.
_PADRAO_SAUDACAO = re.compile(
    rf"^[\s,!?.]*{_TOKEN_SAUDACAO}(?:[\s,!?.]+(?:{_TOKEN_SAUDACAO}|{_TOKEN_MODIFICADOR}))*[\s,!?.]*$",
    re.IGNORECASE,
)


def _e_saudacao_pura(texto: str) -> bool:
    """
    True se a mensagem é apenas saudação (sem pergunta/intenção adicional).
    Limita a 60 caracteres para evitar regex match em frases longas atípicas.
    """
    if not texto or len(texto) > 60:
        return False
    return bool(_PADRAO_SAUDACAO.match(texto))

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

    Modo híbrido: NUNCA reativa se há atendente humano dono da conversa
    (atendente_id setado) ou se o cliente está aguardando atendimento humano
    na fila. Atendente precisa devolver explicitamente via /admin/devolver.
    """
    if user.bot_ativo:
        return True
    # Modo híbrido: bot só volta por ação explícita do atendente.
    if MODO_HIBRIDO and (user.atendente_id is not None or user.aguardando_humano):
        return False
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


def _normalizar_texto_envio(texto: str) -> str:
    """Converte <br> e \\n literais em quebra real, colapsa quebras seguidas."""
    t = re.sub(r"<\s*br\s*/?\s*>", "\n", texto, flags=re.IGNORECASE)
    t = t.replace("\\n", "\n")
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def _enviar_e_registrar(
    db: Session,
    user: Usuario,
    mensagem_cliente: str | None,
    resposta_texto: str,
    origem: str = "bot",
    atendente_id: int | None = None,
) -> bool:
    """
    Salva uma entrada de HistoricoConversa, envia ao WhatsApp via Meta API,
    atualiza coluna `entregue` (True/False) e publica evento SSE com status.

    Retorna True se Meta aceitou a mensagem, False caso contrário.
    Use sempre que o BOT ou ATENDENTE for enviar uma mensagem ao cliente.
    """
    hist = HistoricoConversa(
        telefone_usuario=user.telefone,
        mensagem_cliente=mensagem_cliente,
        resposta_bot=resposta_texto,
        origem=origem,
        atendente_id=atendente_id,
        entregue=None,
    )
    db.add(hist)
    db.commit()

    texto_envio = _normalizar_texto_envio(resposta_texto)
    ok = whatsapp.enviar_mensagem_texto(user.telefone, texto_envio)

    hist.entregue = bool(ok)
    db.commit()

    _notificar_dashboard(user.telefone, user.nome_cliente, resposta_texto, origem, entregue=bool(ok))
    return bool(ok)


def _notificar_dashboard(telefone: str, nome: str | None, texto: str, origem: str, entregue: bool | None = None):
    """
    Publica evento SSE no notificador para o dashboard atualizar em tempo real.
    No-op em modo bot_only (não há dashboard). Origem: 'bot' | 'humano' | 'cliente'.
    `entregue`: True/False pra mensagens saindo (bot/humano), None pra mensagem do cliente.
    """
    if not MODO_HIBRIDO:
        return
    try:
        notificador.publicar({
            "tipo": "nova_mensagem",
            "telefone": telefone,
            "nome": nome,
            "texto": texto,
            "origem": origem,
            "entregue": entregue,
        })
    except Exception:
        log.exception("Falha ao publicar evento SSE para %s", telefone)

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
        if not user:
            return
        # Modo híbrido: se entre o enfileiramento e este ponto o bot foi desativado
        # (atendente assumiu, transbordo), abortamos a IA mas preservamos a mensagem
        # do cliente no histórico para o atendente ver.
        if MODO_HIBRIDO and (not user.bot_ativo or user.atendente_id is not None):
            log.info("Modo híbrido: bot inativo ou atendente assumiu %s; persistindo msg para painel.", telefone)
            db.add(HistoricoConversa(
                telefone_usuario=telefone,
                mensagem_cliente=texto_cliente,
                resposta_bot=None,
                origem="cliente",
            ))
            db.commit()
            notificador.publicar({
                "tipo": "nova_mensagem",
                "telefone": telefone,
                "nome": user.nome_cliente,
                "texto": texto_cliente,
                "origem": "cliente",
            })
            return
        if not user.bot_ativo:
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
            _enviar_e_registrar(db, user, texto_cliente, MENSAGEM_BOAS_VINDAS.replace("\n", "<br>"), origem="bot")
            return

        # Cliente pedindo o menu/capacidades de novo → texto fixo (mesmo padrão visual da boas-vindas).
        # Evita que a IA regenere o menu com emojis e palavras diferentes a cada pedido.
        if _e_pedido_de_menu(texto_cliente):
            _enviar_e_registrar(db, user, texto_cliente, MENSAGEM_MENU_REPETIDO.replace("\n", "<br>"), origem="bot")
            return

        # Saudação pura (oi, eai, bom dia…) sem pergunta acoplada → resposta fixa
        # com primeiro nome do cliente. Evita que a IA gere variações casuais.
        if _e_saudacao_pura(texto_cliente):
            mensagem_saudacao = _montar_saudacao(user.nome_cliente)
            _enviar_e_registrar(db, user, texto_cliente, mensagem_saudacao.replace("\n", "<br>"), origem="bot")
            return

        # FAQ canônico: horário, endereço, agendamento, pagamento, estrutura.
        # Bypass de IA → custo zero, zero alucinação, formato sempre idêntico.
        resposta_canonica = detectar_resposta_canonica(texto_cliente)
        if resposta_canonica:
            _enviar_e_registrar(db, user, texto_cliente, resposta_canonica, origem="bot")
            return

        # Processar IA Pesada
        resultado_ia = ai_service.processar_intencao(db, contexto_mensagens, texto_cliente, user.nome_cliente)
        intencao = resultado_ia.get("intencao")

        resposta_bruta = resultado_ia.get("resposta_sugerida", "Tivemos um problema processando sua solicitação.")

        # Modo híbrido: durante a chamada da IA (vários segundos) um atendente pode
        # ter assumido a conversa. Re-checa antes de gravar/enviar para não atropelar.
        if MODO_HIBRIDO:
            db.refresh(user)
            if user.atendente_id is not None or not user.bot_ativo:
                log.info("Atendente assumiu %s durante chamada IA; descartando resposta.", telefone)
                return

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

        log.debug("Envio WhatsApp (%d chars) para %s", len(resposta_bruta), telefone)

        if intencao == "chamar_recepcao" or intencao == "transbordo_falha":
            if MODO_BOT_ONLY:
                # Sem atendente humano nesse modo. Substitui a resposta da IA
                # (que prometeria "transferindo pra recepção") por orientação real.
                # Bot CONTINUA ativo — não há ninguém pra assumir.
                if intencao == "transbordo_falha":
                    resposta_texto = (
                        "Tive um problema técnico processando sua mensagem. 😕\n\n"
                        "Pode tentar reformular sua dúvida? Posso te ajudar com:\n"
                        "✂️ Serviços e preços\n"
                        "👨‍🎨 Equipe\n"
                        "📅 Agendamento\n"
                        "📍 Localização e horários"
                    )
                else:
                    resposta_texto = (
                        "No momento o atendimento humano não está disponível por aqui. 🤖\n\n"
                        "Mas posso te ajudar com dúvidas sobre serviços, equipe, horários e localização — é só me perguntar.\n\n"
                        "Para agendar, use nosso app: https://sites.appbarber.com.br/bolshoi"
                    )
                _enviar_e_registrar(db, user, texto_cliente, resposta_texto, origem="bot")
                return
            # MODO_HIBRIDO: desativa bot e marca fila pra atendente humano assumir.
            _desativar_bot(db, user)
            user.aguardando_humano = True
            user.transbordo_em = datetime.now(timezone.utc)
            db.commit()
            notificador.publicar({
                "tipo": "novo_transbordo",
                "telefone": telefone,
                "nome": user.nome_cliente,
                "motivo": intencao,
            })
            _enviar_e_registrar(db, user, texto_cliente, resposta_bruta, origem="bot")
            return

        _enviar_e_registrar(db, user, texto_cliente, resposta_bruta, origem="bot")

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
        if MODO_HIBRIDO:
            # Persiste mensagem do cliente para o atendente ver no dashboard.
            # Não respondemos nada — atendente humano que decide.
            db.add(HistoricoConversa(
                telefone_usuario=telefone,
                mensagem_cliente=texto_cliente,
                resposta_bot=None,
                origem="cliente",
            ))
            db.commit()
            notificador.publicar({
                "tipo": "nova_mensagem",
                "telefone": telefone,
                "nome": user.nome_cliente,
                "texto": texto_cliente,
                "origem": "cliente",
            })
            log.info("Modo híbrido: msg de %s persistida para atendimento humano.", telefone)
        else:
            log.info("Mensagem ignorada: bot desativado para %s (modo bot_only).", telefone)
        return {"status": "ok"}

    if texto_cliente == "🙋 Falar c/ Recepção":
        if MODO_HIBRIDO:
            _desativar_bot(db, user)
            user.aguardando_humano = True
            user.transbordo_em = datetime.now(timezone.utc)
            db.commit()
            notificador.publicar({
                "tipo": "novo_transbordo",
                "telefone": telefone,
                "nome": user.nome_cliente,
                "motivo": "botao_recepcao",
            })
            whatsapp.enviar_mensagem_texto(telefone, "Tudo bem! Aguarde um momento, um atendente humano vai assumir e responder você em breve. 🙋")
        else:
            # Em bot_only, não há atendente. Bot continua ativo e orienta.
            whatsapp.enviar_mensagem_texto(
                telefone,
                "No momento o atendimento humano não está disponível por aqui. 🤖\n\n"
                "Mas posso te ajudar com dúvidas sobre serviços, equipe, horários e localização — é só me perguntar.\n\n"
                "Para agendar, use nosso app: https://sites.appbarber.com.br/bolshoi"
            )
        return {"status": "ok"}

    log.info("Enfileirando IA: %s → %r", telefone, texto_cliente[:80])
    # Publica evento da mensagem do cliente IMEDIATAMENTE no dashboard (modo
    # híbrido). Sem isso, atendente só veria a mensagem do cliente depois da IA
    # terminar e responder — pode levar segundos. Com esse evento, msg do cliente
    # aparece em tempo real e o atendente pode decidir assumir antes da IA agir.
    _notificar_dashboard(telefone, user.nome_cliente, texto_cliente, "cliente")
    background_tasks.add_task(tarefa_em_segundo_plano_ia, telefone, texto_cliente)

    return {"status": "ok"}
