import os
import re
import time
import hmac
import hashlib
import logging
import traceback
import threading
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from db.database import get_db, SessionLocal
from db.models import Usuario, HistoricoConversa, MensagemProcessada, Servico, Barbeiro
from services.whatsapp import WhatsAppSender, extrair_informacoes_mensagem
from services.ai_service import AIService
from services.notificador import notificador
from core.respostas_canonicas import (
    detectar_resposta_canonica,
    RESPOSTA_HORARIO_ENDERECO,
    RESPOSTA_AGENDAMENTO,
    RESPOSTA_AGENDAMENTO_HIBRIDO,
    RESPOSTA_PAGAMENTO,
)
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

FRASE_REATIVACAO_TIMEOUT = (
    "Lamentamos não ter conseguido conectar você com nossa recepção anteriormente. "
    "Estou aqui para te ajudar!"
)

MENSAGEM_BOAS_VINDAS = (
    "Olá, seja bem-vindo(a) à *Barbearia Bolshoi*! 💈\n"
    "Sou o assistente virtual da casa.\n\n"
    "*Posso te ajudar com:*\n\n"
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

    Usado APENAS como fallback de texto plano quando a Interactive List falha.
    Fluxo normal usa _enviar_menu_lista() para entregar lista interativa rica.
    """
    primeiro = ""
    if nome_cliente:
        partes = nome_cliente.strip().split()
        if partes:
            primeiro = partes[0]
    abertura = f"Olá, {primeiro}!" if primeiro else "Olá!"
    return (
        f"{abertura}\n\n"
        "*Posso te ajudar com:*\n\n"
        "✂️ Nossos Serviços e Preços\n"
        "👨‍🎨 Nossa Equipe de Barbeiros\n"
        "📅 Agendamento de Horários\n"
        "📍 Localização e Funcionamento\n"
        "❓ Dúvidas Frequentes\n\n"
        "Sobre qual desses tópicos você gostaria de saber?"
    )


# ============================================================
# Interactive List Menu (substitui menus de texto plano)
# ============================================================

# IDs canônicos dos itens. Recebidos como payload em list_reply.
_MENU_ID_SERVICOS_PRECO = "MENU_SERVICOS_PRECO"
_MENU_ID_EQUIPE = "MENU_EQUIPE"
_MENU_ID_AGENDAMENTO = "MENU_AGENDAMENTO"
_MENU_ID_HORARIO_LOCAL = "MENU_HORARIO_LOCAL"
_MENU_ID_PAGAMENTO = "MENU_PAGAMENTO"
_MENU_ID_RECEPCAO = "MENU_RECEPCAO"

_MENU_IDS = {
    _MENU_ID_SERVICOS_PRECO,
    _MENU_ID_EQUIPE,
    _MENU_ID_AGENDAMENTO,
    _MENU_ID_HORARIO_LOCAL,
    _MENU_ID_PAGAMENTO,
    _MENU_ID_RECEPCAO,
}

# Estrutura da lista para Meta API. Limites verificados:
# row.title ≤24, row.description ≤72, section.title ≤24, max 10 rows.
#
# MODE-AWARE: a função é avaliada em runtime para refletir MODO_HIBRIDO atual.
# - bot_only: 2 seções (Serviços + Informações). Sem "Atendimento" — não há
#             atendente humano nesse modo, prometer um seria quebra de UX.
# - hibrido:  3 seções (Serviços + Informações + Atendimento) com "Falar c/
#             Atendente" mapeado ao handoff para o dashboard /admin.
def _montar_menu_sections() -> list[dict]:
    secoes = [
        {
            "title": "Serviços",
            "rows": [
                {
                    "id": _MENU_ID_SERVICOS_PRECO,
                    "title": "✂️ Serviços e Preços",
                    "description": "Cortes, barba, estética e valores",
                },
                {
                    "id": _MENU_ID_EQUIPE,
                    "title": "👨‍🎨 Nossa Equipe",
                    "description": "Conheça nossos barbeiros e profissionais",
                },
            ],
        },
        {
            "title": "Informações",
            "rows": [
                {
                    "id": _MENU_ID_AGENDAMENTO,
                    "title": "📅 Agendamento",
                    "description": "Como marcar seu horário pelo app",
                },
                {
                    "id": _MENU_ID_HORARIO_LOCAL,
                    "title": "📍 Horários e Endereço",
                    "description": "Funcionamento e onde encontrar a barbearia",
                },
                {
                    "id": _MENU_ID_PAGAMENTO,
                    "title": "💳 Formas de Pagamento",
                    "description": "Dinheiro, Pix, débito e crédito",
                },
            ],
        },
    ]
    if MODO_HIBRIDO:
        secoes.append({
            "title": "Atendimento",
            "rows": [
                {
                    "id": _MENU_ID_RECEPCAO,
                    "title": "🙋 Falar c/ Atendente",
                    "description": "Falar diretamente com um atendente",
                },
            ],
        })
    return secoes

# Itens cuja seleção responde com texto canônico (sem IA) e SEM botões anexados.
# MENU_HORARIO_LOCAL usa RESPOSTA_HORARIO_ENDERECO — versão combinada com UM
# único fechamento (evita duplicação de "Posso ajudar em algo mais?").
# OBS: MENU_AGENDAMENTO NÃO está aqui — é tratado separadamente porque carrega botão extra.
# OBS: MENU_SERVICOS_PRECO e MENU_EQUIPE NÃO estão aqui — abrem sub-fluxo de botões.
_RESPOSTAS_DIRETAS_MENU = {
    _MENU_ID_PAGAMENTO: RESPOSTA_PAGAMENTO,
    _MENU_ID_HORARIO_LOCAL: RESPOSTA_HORARIO_ENDERECO,
}

# ============================================================
# Sub-fluxo de botões (após cliente clicar em MENU_SERVICOS_PRECO / MENU_EQUIPE)
# ============================================================

# IDs canônicos dos botões de sub-fluxo. Recebidos como payload em button_reply.
_SUB_ID_SERV_BARBEARIA = "SUB_SERV_BARBEARIA"
_SUB_ID_SERV_ESTETICA = "SUB_SERV_ESTETICA"
_SUB_ID_EQUIPE_BARBEIROS = "SUB_EQUIPE_BARBEIROS"
_SUB_ID_EQUIPE_ESTETICA = "SUB_EQUIPE_ESTETICA"
_SUB_ID_AGENDAR = "SUB_AGENDAR"
_SUB_ID_VOLTAR_MENU = "SUB_VOLTAR_MENU"
# Botão "Falar c/ Atendente" — só aparece em modo híbrido. Em bot_only nunca
# é exibido (não há atendente humano). Tratado SÍNCRONO em receive_message,
# análogo ao MENU_RECEPCAO legado.
_SUB_ID_FALAR_ATENDENTE = "SUB_FALAR_ATENDENTE"

_SUB_IDS = {
    _SUB_ID_SERV_BARBEARIA,
    _SUB_ID_SERV_ESTETICA,
    _SUB_ID_EQUIPE_BARBEIROS,
    _SUB_ID_EQUIPE_ESTETICA,
    _SUB_ID_AGENDAR,
    _SUB_ID_VOLTAR_MENU,
    _SUB_ID_FALAR_ATENDENTE,
}


def _montar_body_menu(nome_cliente: str | None, primeiro_contato: bool) -> str:
    """Body text da Interactive List. Limite Meta: 1024 chars."""
    primeiro = ""
    if nome_cliente:
        partes = nome_cliente.strip().split()
        if partes:
            primeiro = partes[0]
    if primeiro_contato:
        abertura = f"Olá, {primeiro}! Seja bem-vindo(a) à Barbearia Bolshoi 💈" if primeiro \
            else "Olá! Seja bem-vindo(a) à Barbearia Bolshoi 💈"
        return (
            f"{abertura}\n\n"
            "Sou o assistente virtual da casa. Escolha uma das opções abaixo "
            "ou me envie sua dúvida por mensagem."
        )
    abertura = f"Olá novamente, {primeiro}!" if primeiro else "Olá novamente!"
    return f"{abertura} Escolha uma das opções abaixo ou me envie sua dúvida por mensagem."


def _enviar_menu_lista(db: Session, user: Usuario, texto_cliente_trigger: str | None, primeiro_contato: bool = False) -> bool:
    """
    Envia Interactive List Message ao cliente. Registra no histórico um marcador
    "[MENU INTERATIVO ENVIADO]" como resposta_bot e publica evento SSE.

    Em caso de falha de envio da lista (Meta retornou erro), faz fallback automático
    para texto plano via _enviar_e_registrar() com MENSAGEM_BOAS_VINDAS — garante
    que o cliente sempre receba ALGUMA resposta.
    """
    body = _montar_body_menu(user.nome_cliente, primeiro_contato)
    placeholder_historico = "📋 [MENU INTERATIVO ENVIADO]"

    hist = HistoricoConversa(
        telefone_usuario=user.telefone,
        mensagem_cliente=texto_cliente_trigger,
        resposta_bot=placeholder_historico,
        origem="bot",
        intencao="menu_interativo",
        entregue=None,
    )
    db.add(hist)
    db.commit()

    ok, wamid = whatsapp.enviar_lista_interativa(
        numero=user.telefone,
        body_text=body,
        button_text="Ver opções",
        sections=_montar_menu_sections(),
        header_text="Barbearia Bolshoi 💈",
        footer_text="Toque em Ver opções abaixo",
    )

    if not ok:
        # Fallback: texto plano. Atualiza o registro do histórico, não duplica.
        log.warning("Falha ao enviar lista interativa para %s — caindo para texto plano.", user.telefone)
        fallback_texto = MENSAGEM_BOAS_VINDAS.replace("\n", "<br>") if primeiro_contato \
            else _montar_saudacao(user.nome_cliente).replace("\n", "<br>")
        texto_envio = _normalizar_texto_envio(fallback_texto)
        ok_fallback, wamid_fallback = whatsapp.enviar_mensagem_texto(user.telefone, texto_envio)
        hist.resposta_bot = fallback_texto
        hist.intencao = "menu_fallback_texto"
        hist.entregue = bool(ok_fallback)
        hist.wamid = wamid_fallback
        db.commit()
        _notificar_dashboard(user.telefone, user.nome_cliente, fallback_texto, "bot", entregue=bool(ok_fallback))
        return bool(ok_fallback)

    hist.entregue = True
    hist.wamid = wamid
    db.commit()
    _notificar_dashboard(user.telefone, user.nome_cliente, placeholder_historico, "bot", entregue=True)
    return True


def _executar_handoff_recepcao(db: Session, user: Usuario, motivo: str) -> None:
    """
    Lógica unificada do handoff por solicitação explícita do cliente
    (botão antigo "🙋 Falar c/ Recepção" ou item MENU_RECEPCAO).
    Comportamento depende do modo de operação.
    """
    if MODO_HIBRIDO:
        _desativar_bot(db, user)
        user.aguardando_humano = True
        user.transbordo_em = datetime.now(timezone.utc)
        db.commit()
        notificador.publicar({
            "tipo": "novo_transbordo",
            "telefone": user.telefone,
            "nome": user.nome_cliente,
            "motivo": motivo,
        })
        whatsapp.enviar_mensagem_texto(
            user.telefone,
            "Perfeito! Aguarde um instante — um atendente da nossa recepção "
            "vai assumir o atendimento em breve."
        )  # wamid ignored: handoff message has no associated HistoricoConversa here
    else:
        mensagem_bot_only = (
            "No momento o atendimento por aqui é feito apenas pelo assistente virtual.\n\n"
            "Posso te ajudar com dúvidas sobre *serviços*, *equipe*, *horários* e *localização* — é só me perguntar.\n\n"
            "Para agendar, acesse nosso app:\n"
            "https://sites.appbarber.com.br/bolshoi"
        )
        whatsapp.enviar_mensagem_texto(user.telefone, mensagem_bot_only)  # wamid ignored: bot_only


# ============================================================
# Sub-fluxo determinístico (botões pós-seleção de itens da lista)
# ============================================================

def _registrar_envio_botoes(
    db: Session,
    user: Usuario,
    mensagem_cliente: str | None,
    resposta_texto: str,
    body_botoes: str,
    buttons: list[dict],
    intencao: str,
    header_text: str | None = None,
    footer_text: str | None = None,
) -> bool:
    """
    Helper que:
      1. Salva resposta_texto no histórico (com placeholder de botões anexo).
      2. Envia o texto via Meta API.
      3. Envia os botões (com body_botoes curto, ex: "O que prefere fazer?").
      4. Fallback automático: se botões falharem, manda lista de opções como texto.

    Retorna True se ao menos o texto foi entregue; botões são UX bonus.
    """
    placeholder = f"{resposta_texto}<br><br>[BOTÕES: {' | '.join(b['title'] for b in buttons)}]"

    hist = HistoricoConversa(
        telefone_usuario=user.telefone,
        mensagem_cliente=mensagem_cliente,
        resposta_bot=placeholder,
        origem="bot",
        intencao=intencao,
        entregue=None,
    )
    db.add(hist)
    db.commit()

    texto_envio = _normalizar_texto_envio(resposta_texto)
    ok_texto, wamid = whatsapp.enviar_mensagem_texto(user.telefone, texto_envio)

    ok_botoes, _ = whatsapp.enviar_botoes_resposta(
        numero=user.telefone,
        body_text=body_botoes,
        buttons=buttons,
        header_text=header_text,
        footer_text=footer_text,
    )

    if not ok_botoes:
        # Fallback discreto: lista as opções como texto para o cliente saber o que pode pedir.
        log.warning("Botões falharam para %s — enviando hint textual.", user.telefone)
        hint = "Você pode responder:\n" + "\n".join(f"• {b['title']}" for b in buttons)
        whatsapp.enviar_mensagem_texto(user.telefone, hint)

    hist.entregue = bool(ok_texto)
    hist.wamid = wamid
    db.commit()
    _notificar_dashboard(user.telefone, user.nome_cliente, placeholder, "bot", entregue=bool(ok_texto))
    return bool(ok_texto)


def _enviar_subflow_servicos(db: Session, user: Usuario, texto_cliente_trigger: str) -> None:
    """Cliente clicou em MENU_SERVICOS_PRECO → oferece sub-categorias por botões."""
    body = "Sobre qual categoria você quer saber?"
    buttons = [
        {"id": _SUB_ID_SERV_BARBEARIA, "title": "💈 Barbearia"},
        {"id": _SUB_ID_SERV_ESTETICA, "title": "💆 Estética"},
        {"id": _SUB_ID_AGENDAR, "title": "📅 Agendar"},
    ]
    placeholder = f"[SUB-FLUXO SERVIÇOS] {body}"
    hist = HistoricoConversa(
        telefone_usuario=user.telefone,
        mensagem_cliente=texto_cliente_trigger,
        resposta_bot=placeholder,
        origem="bot",
        intencao="sub_servicos_menu",
        entregue=None,
    )
    db.add(hist)
    db.commit()

    ok, wamid = whatsapp.enviar_botoes_resposta(
        numero=user.telefone,
        body_text=body,
        buttons=buttons,
        header_text="✂️ Serviços e Preços",
    )
    if not ok:
        # Fallback texto: hint para o cliente conseguir prosseguir mesmo sem botões.
        fallback = (
            "*Sobre qual categoria você quer saber?*\n\n"
            "Responda com uma destas opções:\n\n"
            "• Barbearia (cortes, barba e acabamentos)\n"
            "• Estética (procedimentos com a Isabella)\n"
            "• Agendar"
        )
        ok_fb, wamid_fb = whatsapp.enviar_mensagem_texto(user.telefone, fallback)
        hist.resposta_bot = fallback
        hist.intencao = "sub_servicos_fallback"
        hist.entregue = bool(ok_fb)
        hist.wamid = wamid_fb
    else:
        hist.entregue = True
        hist.wamid = wamid
    db.commit()
    _notificar_dashboard(user.telefone, user.nome_cliente, placeholder, "bot", entregue=bool(hist.entregue))


def _enviar_subflow_equipe(db: Session, user: Usuario, texto_cliente_trigger: str) -> None:
    """Cliente clicou em MENU_EQUIPE → oferece sub-categorias por botões."""
    body = "Qual equipe você quer conhecer?"
    buttons = [
        {"id": _SUB_ID_EQUIPE_BARBEIROS, "title": "💈 Barbeiros"},
        {"id": _SUB_ID_EQUIPE_ESTETICA, "title": "💆 Estética"},
        {"id": _SUB_ID_AGENDAR, "title": "📅 Agendar"},
    ]
    placeholder = f"[SUB-FLUXO EQUIPE] {body}"
    hist = HistoricoConversa(
        telefone_usuario=user.telefone,
        mensagem_cliente=texto_cliente_trigger,
        resposta_bot=placeholder,
        origem="bot",
        intencao="sub_equipe_menu",
        entregue=None,
    )
    db.add(hist)
    db.commit()

    ok, wamid = whatsapp.enviar_botoes_resposta(
        numero=user.telefone,
        body_text=body,
        buttons=buttons,
        header_text="👨‍🎨 Nossa Equipe",
    )
    if not ok:
        fallback = (
            "*Qual equipe você quer conhecer?*\n\n"
            "Responda com uma destas opções:\n\n"
            "• Barbeiros\n"
            "• Estética\n"
            "• Agendar"
        )
        ok_fb, wamid_fb = whatsapp.enviar_mensagem_texto(user.telefone, fallback)
        hist.resposta_bot = fallback
        hist.intencao = "sub_equipe_fallback"
        hist.entregue = bool(ok_fb)
        hist.wamid = wamid_fb
    else:
        hist.entregue = True
        hist.wamid = wamid
    db.commit()
    _notificar_dashboard(user.telefone, user.nome_cliente, placeholder, "bot", entregue=bool(hist.entregue))


def _botoes_acao_pos_lista(incluir_voltar: bool = True) -> list[dict]:
    """
    Monta lista de botões padrão para mensagens pós-categoria (serviços/equipe).
    MODE-AWARE:
      - bot_only: [📅 Agendar pelo App] [Menu principal]  (2 botões)
      - hibrido:  [📅 Agendar pelo App] [🙋 Falar c/ Atendente] [Menu principal]  (3 botões, máx Meta)
    Títulos verificados (limite Meta = 20 chars):
      - "📅 Agendar pelo App"   = 19 chars  OK
      - "🙋 Falar c/ Atendente" = 20 chars  OK
      - "Menu principal"     = 16 chars  OK
    """
    botoes = [{"id": _SUB_ID_AGENDAR, "title": "📅 Agendar pelo App"}]
    if MODO_HIBRIDO:
        botoes.append({"id": _SUB_ID_FALAR_ATENDENTE, "title": "🙋 Falar c/ Atendente"})
    if incluir_voltar:
        botoes.append({"id": _SUB_ID_VOLTAR_MENU, "title": "Menu principal"})
    return botoes


def _enviar_agendamento_com_botao_recepcao(db: Session, user: Usuario, texto_cliente_trigger: str) -> None:
    """
    Cliente clicou em MENU_AGENDAMENTO → resposta canônica.
    MODE-AWARE:
      - bot_only: apenas texto puro (RESPOSTA_AGENDAMENTO), sem botão — não há atendente.
      - hibrido:  RESPOSTA_AGENDAMENTO_HIBRIDO + 1 botão "Falar c/ Atendente".
    """
    if MODO_BOT_ONLY:
        _enviar_e_registrar(
            db, user, texto_cliente_trigger,
            RESPOSTA_AGENDAMENTO,
            origem="bot",
            intencao="menu_agendamento",
        )
        return

    # Híbrido: texto com nota suave + botão para chamar atendente humano.
    body_botoes = "Precisa de ajuda para usar o app?"
    buttons = [
        {"id": _SUB_ID_FALAR_ATENDENTE, "title": "🙋 Falar c/ Atendente"},
    ]
    _registrar_envio_botoes(
        db=db,
        user=user,
        mensagem_cliente=texto_cliente_trigger,
        resposta_texto=RESPOSTA_AGENDAMENTO_HIBRIDO,
        body_botoes=body_botoes,
        buttons=buttons,
        intencao="menu_agendamento",
        header_text="📅 Agendamento",
    )


def _listar_servicos_categoria(db: Session, categoria: str) -> str:
    """
    Retorna texto formatado com serviços ativos da categoria (sem chamar IA).
    Categoria: 'barbearia' ou 'estetica'.
    """
    servicos = (
        db.query(Servico)
        .filter(Servico.ativo == True, Servico.categoria == categoria)
        .order_by(Servico.id)
        .all()
    )
    if not servicos:
        return ""
    linhas = []
    for s in servicos:
        try:
            preco_fmt = f"R$ {float(s.preco):.2f}".replace(".", ",")
        except (TypeError, ValueError):
            preco_fmt = "consultar"
        linhas.append(f"✂️ {s.nome_servico} — {preco_fmt}")
    return "<br>".join(linhas)


def _listar_equipe_categoria(db: Session, categoria: str) -> str:
    """
    Retorna texto formatado com profissionais que executam serviços da categoria.
    Categoria: 'barbearia' ou 'estetica'.
    Inclui nome, dias de trabalho e serviços que faz dentro da categoria.
    """
    from sqlalchemy.orm import joinedload
    barbeiros = (
        db.query(Barbeiro)
        .options(joinedload(Barbeiro.servicos))
        .order_by(Barbeiro.id)
        .all()
    )
    blocos = []
    for b in barbeiros:
        servs_categoria = [s for s in b.servicos if s.categoria == categoria and s.ativo]
        if not servs_categoria:
            continue
        nomes_serv = ", ".join(s.nome_servico for s in servs_categoria)
        dias = b.dias_trabalho or "Consulte disponibilidade"
        blocos.append(
            f"👤 *{b.nome}*<br>"
            f"📅 {dias}<br>"
            f"✂️ {nomes_serv}"
        )
    return "<br><br>".join(blocos)


def _enviar_servicos_categoria(db: Session, user: Usuario, categoria: str, texto_cliente_trigger: str) -> None:
    """Resposta determinística com preços da categoria + botões [Agendar] [Voltar]."""
    cabecalho = "💈 *Serviços de Barbearia:*" if categoria == "barbearia" else "💆‍♀️ *Serviços de Estética:*"
    lista = _listar_servicos_categoria(db, categoria)

    if not lista:
        nome_cat = "barbearia" if categoria == "barbearia" else "estética"
        resposta = (
            f"No momento não há serviços de {nome_cat} cadastrados em nosso sistema.<br><br>"
            "Posso te ajudar com algo mais?"
        )
    else:
        resposta = f"{cabecalho}<br><br>{lista}"

    body_botoes = "O que deseja fazer agora?"
    buttons = _botoes_acao_pos_lista(incluir_voltar=True)
    _registrar_envio_botoes(
        db=db,
        user=user,
        mensagem_cliente=texto_cliente_trigger,
        resposta_texto=resposta,
        body_botoes=body_botoes,
        buttons=buttons,
        intencao=f"sub_servicos_{categoria}",
    )


def _enviar_equipe_categoria(db: Session, user: Usuario, categoria: str, texto_cliente_trigger: str) -> None:
    """Resposta determinística com equipe da categoria + botões [Agendar] [Voltar]."""
    cabecalho = "💈 *Nossos Barbeiros:*" if categoria == "barbearia" else "💆‍♀️ *Nossa Equipe de Estética:*"
    lista = _listar_equipe_categoria(db, categoria)

    if not lista:
        nome_cat = "barbeiros" if categoria == "barbearia" else "profissionais de estética"
        resposta = (
            f"No momento não há {nome_cat} cadastrados em nosso sistema.<br><br>"
            "Posso te ajudar com algo mais?"
        )
    else:
        resposta = f"{cabecalho}<br><br>{lista}"

    body_botoes = "O que deseja fazer agora?"
    buttons = _botoes_acao_pos_lista(incluir_voltar=True)
    _registrar_envio_botoes(
        db=db,
        user=user,
        mensagem_cliente=texto_cliente_trigger,
        resposta_texto=resposta,
        body_botoes=body_botoes,
        buttons=buttons,
        intencao=f"sub_equipe_{categoria}",
    )


def _despachar_menu_principal(db: Session, user: Usuario, texto_cliente: str) -> bool:
    """
    Trata seleção de itens da Interactive List principal (MENU_*).
    Retorna True se o item foi tratado aqui (não deve seguir o pipeline).
    """
    if texto_cliente == _MENU_ID_SERVICOS_PRECO:
        _enviar_subflow_servicos(db, user, texto_cliente)
        return True
    if texto_cliente == _MENU_ID_EQUIPE:
        _enviar_subflow_equipe(db, user, texto_cliente)
        return True
    if texto_cliente == _MENU_ID_AGENDAMENTO:
        _enviar_agendamento_com_botao_recepcao(db, user, texto_cliente)
        return True
    if texto_cliente in _RESPOSTAS_DIRETAS_MENU:
        resposta = _RESPOSTAS_DIRETAS_MENU[texto_cliente]
        _enviar_e_registrar(db, user, texto_cliente, resposta, origem="bot", intencao="menu_resposta_direta")
        return True
    return False


def _despachar_subfluxo(db: Session, user: Usuario, texto_cliente: str) -> bool:
    """
    Trata seleção de botões SUB_* (depois do primeiro nível).
    Retorna True se o botão foi tratado aqui.
    """
    if texto_cliente == _SUB_ID_SERV_BARBEARIA:
        _enviar_servicos_categoria(db, user, "barbearia", texto_cliente)
        return True
    if texto_cliente == _SUB_ID_SERV_ESTETICA:
        _enviar_servicos_categoria(db, user, "estetica", texto_cliente)
        return True
    if texto_cliente == _SUB_ID_EQUIPE_BARBEIROS:
        _enviar_equipe_categoria(db, user, "barbearia", texto_cliente)
        return True
    if texto_cliente == _SUB_ID_EQUIPE_ESTETICA:
        _enviar_equipe_categoria(db, user, "estetica", texto_cliente)
        return True
    if texto_cliente == _SUB_ID_AGENDAR:
        # Em híbrido, oferece texto + botão pra falar com atendente; em bot_only,
        # apenas texto canônico puro (sem prometer atendente que não existe).
        if MODO_HIBRIDO:
            body_botoes = "Precisa de ajuda para usar o app?"
            buttons = [
                {"id": _SUB_ID_FALAR_ATENDENTE, "title": "🙋 Falar c/ Atendente"},
            ]
            _registrar_envio_botoes(
                db=db,
                user=user,
                mensagem_cliente=texto_cliente,
                resposta_texto=RESPOSTA_AGENDAMENTO_HIBRIDO,
                body_botoes=body_botoes,
                buttons=buttons,
                intencao="sub_agendar",
                header_text="📅 Agendamento",
            )
        else:
            _enviar_e_registrar(db, user, texto_cliente, RESPOSTA_AGENDAMENTO, origem="bot", intencao="sub_agendar")
        return True
    if texto_cliente == _SUB_ID_VOLTAR_MENU:
        _enviar_menu_lista(db, user, texto_cliente, primeiro_contato=False)
        return True
    return False


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
_DEDUPE_TTL_SEGUNDOS = 3600  # 1h — cobre janela de reenvio da Meta (TD-014)

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
        user.reativado_por_timeout = True
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
    """
    Prepara texto para envio à Meta API:
      1. Converte qualquer variação de <br> (com/sem espaços, <br/>, <BR>) em \n.
      2. Converte "\\n" literal (string escapada vinda da IA) em \n real.
      3. Normaliza CRLF do Windows e CR isolado.
      4. Remove espaços em branco no final de cada linha (causa principal de
         "linhas emendadas" quando a fonte tinha trailing spaces).
      5. Colapsa 3+ quebras consecutivas em apenas 2 (parágrafo simples).
      6. Strip nas pontas.
    Texto resultante tem quebras reais — WhatsApp renderiza corretamente.
    """
    if not texto:
        return ""
    t = re.sub(r"<\s*br\s*/?\s*>", "\n", texto, flags=re.IGNORECASE)
    t = t.replace("\\n", "\n")
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    # Remove espaços/tabs no final de cada linha (preserva indentação intencional no início).
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def _enviar_e_registrar(
    db: Session,
    user: Usuario,
    mensagem_cliente: str | None,
    resposta_texto: str,
    origem: str = "bot",
    atendente_id: int | None = None,
    intencao: str | None = None,
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
        intencao=intencao,
        atendente_id=atendente_id,
        entregue=None,
    )
    db.add(hist)
    db.commit()

    texto_envio = _normalizar_texto_envio(resposta_texto)
    ok, wamid = whatsapp.enviar_mensagem_texto(user.telefone, texto_envio)

    hist.entregue = bool(ok)
    hist.wamid = wamid
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
    lock = _lock_do_telefone(telefone)
    # TD-013: timeout de 90s evita starvation caso NIM trave indefinidamente.
    # Mensagem é descartada silenciosamente — Meta vai retransmitir se não receber ACK,
    # e o dedupe de 1h protege contra processamento duplicado nesse cenário.
    adquirido = lock.acquire(timeout=90)
    if not adquirido:
        log.warning("Lock timeout (90s) para %s — mensagem descartada para evitar starvation.", telefone)
        return
    try:
        _processar_mensagem(telefone, texto_cliente)
    except Exception as exc:
        # ADR-010: captura exceção raiz para garantir visibilidade de falhas silenciosas.
        # O lock é liberado no finally independentemente.
        ts = datetime.now(timezone.utc).isoformat()
        entrada = f"[{ts}] [BACKGROUND TASK] telefone={telefone} erro={exc}\n{traceback.format_exc()}\n"
        log.error("Exceção não tratada em tarefa_em_segundo_plano_ia para %s: %s", telefone, exc)
        try:
            caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "erro_ia_debug.txt")
            with open(caminho, "a", encoding="utf-8") as f:
                f.write(entrada)
        except Exception:
            pass
    finally:
        lock.release()

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

        # Seleção de item do menu interativo principal (list_reply: MENU_*).
        # Itens com sub-fluxo (Serviços, Equipe) ou resposta canônica direta são
        # tratados aqui sem chamar a IA. MENU_RECEPCAO já foi tratado em receive_message.
        if _despachar_menu_principal(db, user, texto_cliente):
            return

        # Seleção de botão de sub-fluxo (button_reply: SUB_*).
        # Categoria escolhida → lista determinística do DB; agendar → canônica;
        # voltar ao menu → reabre lista interativa.
        if _despachar_subfluxo(db, user, texto_cliente):
            return

        # Primeiro contato (histórico vazio) → SEMPRE entrega o menu interativo,
        # independentemente do que o cliente digitou. A IA só assume a partir da 2ª mensagem.
        if not historico:
            _enviar_menu_lista(db, user, texto_cliente, primeiro_contato=True)
            return

        # Cliente pedindo o menu/capacidades de novo → lista interativa.
        # Fallback automático para texto se a lista falhar.
        if _e_pedido_de_menu(texto_cliente):
            if user.reativado_por_timeout:
                whatsapp.enviar_mensagem_texto(telefone, FRASE_REATIVACAO_TIMEOUT)
                user.reativado_por_timeout = False
                db.commit()
            _enviar_menu_lista(db, user, texto_cliente, primeiro_contato=False)
            return

        # Saudação pura (oi, eai, bom dia…) sem pergunta acoplada → lista interativa
        # com primeiro nome do cliente. Evita que a IA gere variações casuais.
        if _e_saudacao_pura(texto_cliente):
            if user.reativado_por_timeout:
                whatsapp.enviar_mensagem_texto(telefone, FRASE_REATIVACAO_TIMEOUT)
                user.reativado_por_timeout = False
                db.commit()
            _enviar_menu_lista(db, user, texto_cliente, primeiro_contato=False)
            return

        # FAQ canônico: horário, endereço, agendamento, pagamento, estrutura.
        # Bypass de IA → custo zero, zero alucinação, formato sempre idêntico.
        resposta_canonica = detectar_resposta_canonica(texto_cliente)
        if resposta_canonica:
            if user.reativado_por_timeout:
                resposta_canonica = FRASE_REATIVACAO_TIMEOUT + "<br><br>" + resposta_canonica
                user.reativado_por_timeout = False
                db.commit()
            _enviar_e_registrar(db, user, texto_cliente, resposta_canonica, origem="bot")
            return

        # Processar IA Pesada
        resultado_ia = ai_service.processar_intencao(db, contexto_mensagens, texto_cliente, user.nome_cliente)
        intencao = resultado_ia.get("intencao")

        resposta_bruta = resultado_ia.get("resposta_sugerida", "Tivemos um problema processando sua solicitação.")

        # US-GAP-02: primeira resposta após reativação automática por timeout recebe
        # frase de contexto para o cliente saber que o bot voltou a responder.
        if user.reativado_por_timeout:
            resposta_bruta = FRASE_REATIVACAO_TIMEOUT + "<br><br>" + resposta_bruta
            user.reativado_por_timeout = False
            db.commit()

        # Modo híbrido: durante a chamada da IA (vários segundos) um atendente pode
        # ter assumido a conversa. Re-checa antes de gravar/enviar para não atropelar.
        if MODO_HIBRIDO:
            db.refresh(user)
            if user.atendente_id is not None or not user.bot_ativo:
                log.info("Atendente assumiu %s durante chamada IA; descartando resposta.", telefone)
                return

        # Poda automática: mantém últimos 50 registros por usuário (janela do contexto = 15).
        # TD-012: usa min_id em vez de NOT IN — evita lista de 50 IDs no DELETE.
        # Busca o id do 50º mais novo (offset=49); deleta tudo com id < esse valor.
        corte = (
            db.query(HistoricoConversa.id)
            .filter(HistoricoConversa.telefone_usuario == telefone)
            .order_by(HistoricoConversa.criado_em.desc())
            .offset(50)
            .limit(1)
            .scalar()
        )
        if corte is not None:
            db.query(HistoricoConversa).filter(
                HistoricoConversa.telefone_usuario == telefone,
                HistoricoConversa.id <= corte,
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
                        "Tive uma instabilidade ao processar sua mensagem.\n\n"
                        "Pode tentar reformular?\n\n"
                        "*Posso te ajudar com:*\n\n"
                        "✂️ Serviços e preços\n"
                        "👨‍🎨 Equipe\n"
                        "📅 Agendamento\n"
                        "📍 Localização e horários"
                    )
                else:
                    resposta_texto = (
                        "No momento o atendimento por aqui é feito apenas pelo assistente virtual.\n\n"
                        "Posso te ajudar com dúvidas sobre *serviços*, *equipe*, *horários* e *localização* — é só me perguntar.\n\n"
                        "Para agendar, acesse nosso app:\n"
                        "https://sites.appbarber.com.br/bolshoi"
                    )
                _enviar_e_registrar(db, user, texto_cliente, resposta_texto, origem="bot", intencao=intencao)
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
            _enviar_e_registrar(db, user, texto_cliente, resposta_bruta, origem="bot", intencao=intencao)
            return

        _enviar_e_registrar(db, user, texto_cliente, resposta_bruta, origem="bot", intencao=intencao)

    finally:
        db.close()



def _processar_status_updates(value: dict) -> None:
    """
    Processa status updates de entrega/leitura enviados pela Meta no mesmo endpoint do webhook.
    Atualiza `lida` em HistoricoConversa e publica SSE mensagem_lida para o dashboard.
    Cria sessão DB própria (background task não pode reusar a sessão da request).
    """
    statuses = value.get("statuses", [])
    if not statuses:
        return

    db = SessionLocal()
    try:
        for st in statuses:
            wamid = st.get("id")
            status = st.get("status")
            telefone = st.get("recipient_id")

            if status not in ("delivered", "read") or not wamid:
                continue

            hist = db.query(HistoricoConversa).filter(
                HistoricoConversa.wamid == wamid
            ).first()

            if not hist:
                continue

            if status == "delivered":
                hist.entregue = True
                hist.lida = False
            elif status == "read":
                hist.entregue = True
                hist.lida = True

            db.commit()

            if MODO_HIBRIDO:
                try:
                    from api.admin import notificador as admin_notificador
                    admin_notificador.publicar({
                        "tipo": "mensagem_lida",
                        "wamid": wamid,
                        "status": status,
                        "telefone": telefone,
                    })
                except Exception:
                    log.exception("Falha ao publicar SSE mensagem_lida para wamid=%s", wamid)
    except Exception:
        log.exception("Erro em _processar_status_updates")
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

    # Extrai o bloco value para processar status updates antes do early return de mensagens.
    try:
        _value = body.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {})
    except (IndexError, AttributeError):
        _value = {}

    if _value.get("statuses"):
        background_tasks.add_task(_processar_status_updates, _value)

    telefone, texto_cliente, nome_cliente, message_id = extrair_informacoes_mensagem(body)

    if not telefone or not texto_cliente:
        return {"status": "ok"}

    # Dedupe persistente: Meta retransmite quando não recebe ACK rápido. Sem isso, cliente
    # recebe resposta duplicada. Persistido em DB → sobrevive a restart.
    if message_id and _ja_processada(db, message_id):
        log.info("Dedupe: message_id %s já processado, ignorando retransmissão.", message_id)
        return {"status": "ok"}

    if str(texto_cliente).startswith("MÍDIA_"):
        mensagem_midia = (
            "Por aqui consigo ajudar apenas por *mensagens de texto* — não processo áudios, fotos ou documentos.\n\n"
            "Pode me descrever sua dúvida em palavras?\n\n"
            "Posso ajudar com:\n\n"
            "✂️ Serviços e preços\n"
            "👨‍🎨 Equipe\n"
            "📅 Agendamento\n"
            "📍 Localização e horários"
        )
        # BE-04: garante que message_id de mídia esteja em MensagemProcessada mesmo
        # se _ja_processada() acima falhou silenciosamente (ex.: exceção de DB fugaz).
        if message_id:
            try:
                if not db.query(MensagemProcessada).filter(MensagemProcessada.message_id == message_id).first():
                    db.add(MensagemProcessada(message_id=message_id))
                    db.commit()
            except Exception:
                db.rollback()
        background_tasks.add_task(
            whatsapp.enviar_mensagem_texto,
            telefone,
            mensagem_midia,
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

    # Reabertura automática: conversas marcadas como snoozed/resolved precisam
    # voltar para a fila do dashboard assim que o cliente mandar nova mensagem.
    # Sem isso, cliente VIP pode ficar invisível ao atendente por horas (PO).
    # Mudança silenciosa para o cliente — apenas estado interno + SSE para o painel.
    if user.status_conversa in ("snoozed", "resolved"):
        user.status_conversa = "open"
        user.snoozed_until = None
        db.commit()
        if MODO_HIBRIDO:
            try:
                notificador.publicar({
                    "tipo": "status_alterado",
                    "telefone": user.telefone,
                    "status": "open",
                    "snoozed_until": None,
                    "por_atendente_id": None,  # None = reabertura automática pelo sistema
                })
            except Exception:
                log.exception("Falha ao publicar status_alterado (reabertura automática) para %s", telefone)

    # Comandos de admin — processados ANTES de qualquer outra lógica de bot.
    # Apenas telefones listados em ADMIN_PHONES podem usar; tentativas de não-admin são silenciadas.
    _cmd = str(texto_cliente).strip().lower()

    if _cmd == "!reiniciar":
        if telefone not in ADMIN_PHONES:
            log.warning("Tentativa de !reiniciar por telefone não-admin: %s", telefone)
            return {"status": "ok"}
        # Reseta estado completo do usuário: bot ativo, sem handoff pendente, sem atendente.
        user.bot_ativo = True
        user.bot_desativado_em = None
        user.aguardando_humano = False
        user.atendente_id = None
        user.transbordo_em = None
        user.status_conversa = "open"
        user.snoozed_until = None
        user.reativado_por_timeout = False
        db.query(HistoricoConversa).filter(HistoricoConversa.telefone_usuario == telefone).delete()
        db.commit()
        log.info("!reiniciar executado por admin %s: estado e histórico limpos.", telefone)
        whatsapp.enviar_mensagem_texto(telefone, "Bot reiniciado por admin. Estado e memória limpos.")
        return {"status": "ok"}

    if _cmd == "!status":
        if telefone not in ADMIN_PHONES:
            log.warning("Tentativa de !status por telefone não-admin: %s", telefone)
            return {"status": "ok"}
        # Informa estado atual do usuário sem alterar nada — útil para diagnóstico.
        contagem = db.query(HistoricoConversa).filter(
            HistoricoConversa.telefone_usuario == telefone
        ).count()
        status_bot = "ATIVO" if user.bot_ativo else "INATIVO"
        aguardando = "sim" if user.aguardando_humano else "nao"
        atendente = f"#{user.atendente_id}" if user.atendente_id else "nenhum"
        modo = "hibrido" if MODO_HIBRIDO else "bot_only"
        msg = (
            f"Status do bot para {telefone}:\n"
            f"Bot: {status_bot}\n"
            f"Aguardando humano: {aguardando}\n"
            f"Atendente: {atendente}\n"
            f"Historico: {contagem} msgs\n"
            f"Modo: {modo}"
        )
        whatsapp.enviar_mensagem_texto(telefone, msg)
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

    # Solicitação de recepção/atendente: botões legados OU itens das listas/botões.
    # Tratado síncrono (antes de enfileirar IA) — handoff é sensível a tempo.
    # Aceita: botão legado, MENU_RECEPCAO (lista), SUB_FALAR_ATENDENTE (botão pós-categoria).
    _GATILHOS_HANDOFF = {
        "🙋 Falar c/ Recepção": "botao_recepcao_legado",
        "🙋 Falar c/ Atendente": "botao_atendente_legado",
        "MENU_RECEPCAO": "menu_recepcao",
        _SUB_ID_FALAR_ATENDENTE: "botao_falar_atendente",
    }
    if texto_cliente in _GATILHOS_HANDOFF:
        _executar_handoff_recepcao(db, user, _GATILHOS_HANDOFF[texto_cliente])
        return {"status": "ok"}

    log.info("Enfileirando IA: %s → %r", telefone, texto_cliente[:80])
    # Publica evento da mensagem do cliente IMEDIATAMENTE no dashboard (modo
    # híbrido). Sem isso, atendente só veria a mensagem do cliente depois da IA
    # terminar e responder — pode levar segundos. Com esse evento, msg do cliente
    # aparece em tempo real e o atendente pode decidir assumir antes da IA agir.
    _notificar_dashboard(telefone, user.nome_cliente, texto_cliente, "cliente")

    background_tasks.add_task(tarefa_em_segundo_plano_ia, telefone, texto_cliente)

    return {"status": "ok"}
