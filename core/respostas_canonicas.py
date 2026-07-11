"""
Respostas canônicas determinísticas. Detecta intenções simples via regex
e devolve texto literal SEM acionar a IA. Reduz custo de tokens, elimina
variações estéticas e zera risco de alucinação para perguntas frequentes.

Quando NÃO casar nenhum padrão, devolve None e o fluxo segue para a IA.

Regras de redação dos textos canônicos:
- Português profissional (sem gírias, sem emojis decorativos no corpo).
- Emojis funcionais permitidos (📍 endereço, 💵 💳 📱 pagamento, ✅ FAQ).
- `<br>` é a quebra de linha oficial — o webhook converte para newline real.
- Toda canônica fecha com uma chamada-para-próxima-ação consistente.
- Nunca prometa marcar/agendar. Sempre redirecione para o AppBarber quando aplicável.
"""

import re

# Link AppBarber e contato (fontes da verdade — qualquer mudança vem aqui)
LINK_APPBARBER = "https://sites.appbarber.com.br/bolshoi"
LINK_MAPA = "https://www.google.com/maps/search/?api=1&query=-16.36553001%2C-46.89651871"

# Núcleo do conteúdo (sem fechamento). Reaproveitado pela versão completa
# E pela versão combinada (Horários + Endereço no mesmo item de menu).
# B9: gerado da fonte única services/horarios.py (HORARIOS_FALLBACK) — antes era
# um texto fixo que podia divergir do fallback da IA e do seed.
from services.horarios import corpo_horario_fallback as _corpo_horario_fallback

_CORPO_HORARIO = _corpo_horario_fallback()

_CORPO_ENDERECO = (
    "📍 *Estamos em:*<br><br>"
    "R. Zaida Torres Martins, 195<br>"
    "Bairro Cruzeiro - Unaí/MG<br>"
    "CEP 38616-016<br><br>"
    f"Mapa: {LINK_MAPA}"
)

# Fechamento padronizado das canônicas (uma só frase, reaproveitada).
_FECHAMENTO = "Posso ajudar em algo mais?"

RESPOSTA_HORARIO = f"{_CORPO_HORARIO}<br><br>{_FECHAMENTO}"

RESPOSTA_ENDERECO = f"{_CORPO_ENDERECO}<br><br>{_FECHAMENTO}"

# Versão combinada usada quando o cliente clica em "📍 Horários e Endereço"
# no menu interativo. Tem UM único fechamento ao final — evita duplicar
# "Posso ajudar em algo mais?" que aconteceria se concatenássemos as duas
# constantes completas.
RESPOSTA_HORARIO_ENDERECO = (
    f"{_CORPO_HORARIO}<br><br>"
    f"{_CORPO_ENDERECO}<br><br>"
    f"{_FECHAMENTO}"
)

RESPOSTA_AGENDAMENTO = (
    "*Agendamentos* são feitos exclusivamente pelo nosso aplicativo oficial:<br><br>"
    f"{LINK_APPBARBER}<br><br>"
    "Lá você escolhe o serviço, o profissional, a data e o horário disponível em tempo real.<br><br>"
    f"{_FECHAMENTO}"
)

# Variante para modo híbrido: mesma orientação canônica + nota suave de que existe
# atendente humano disponível caso o cliente tenha dúvidas operacionais com o app.
# IMPORTANTE: nunca usar em modo bot_only — prometeria atendente inexistente.
RESPOSTA_AGENDAMENTO_HIBRIDO = (
    "*Agendamentos* são feitos exclusivamente pelo nosso aplicativo oficial:<br><br>"
    f"{LINK_APPBARBER}<br><br>"
    "Lá você escolhe o serviço, o profissional, a data e o horário disponível em tempo real.<br><br>"
    "Se preferir, nossos atendentes também podem te ajudar com dúvidas sobre o app."
)

RESPOSTA_PAGAMENTO = (
    "*Formas de pagamento aceitas no estabelecimento:*<br><br>"
    "💵 Dinheiro<br>"
    "📱 Pix<br>"
    "💳 Cartão de Débito<br>"
    "💳 Cartão de Crédito<br><br>"
    f"{_FECHAMENTO}"
)

# Foco em estrutura FÍSICA do estabelecimento. Pagamento saiu daqui — tem canônica própria.
RESPOSTA_FAQ_ESTRUTURA = (
    "*Nossa estrutura oferece:*<br><br>"
    "✅ Wi-Fi liberado para clientes<br>"
    "✅ Ambiente totalmente climatizado<br>"
    "✅ Atendimento especializado infantil<br>"
    "✅ Acessibilidade completa para cadeirantes<br><br>"
    f"{_FECHAMENTO}"
)

# Cancelamento / remarcação: cliente já tem agendamento e quer alterar.
# Resposta sem promessa de execução — operação fica no app.
RESPOSTA_CANCELAR_REMARCAR = (
    "*Cancelamentos e remarcações* são feitos diretamente pelo nosso aplicativo:<br><br>"
    f"{LINK_APPBARBER}<br><br>"
    "Ao acessar, localize seu agendamento e escolha cancelar ou alterar a data/horário.<br><br>"
    f"{_FECHAMENTO}"
)

# Atendimento feminino: barbearia atende todos os públicos; estética é com Isabella.
RESPOSTA_ATENDIMENTO_FEMININO = (
    "Sim, atendemos todos os públicos.<br><br>"
    "💈 Na *barbearia*, nossa equipe atende clientes de todos os gêneros.<br>"
    "💆‍♀️ Na *estética*, contamos com a Isabella para procedimentos especializados.<br><br>"
    f"Para conferir serviços e agendar: {LINK_APPBARBER}"
)

# Disponibilidade/presença do Fred (proprietário) — NÃO confundir com pedido de contato.
# "o Fred tá lá?" / "Fred vai estar amanhã?" → orienta para AppBarber.
# Pedidos de contato/telefone do Fred NÃO estão aqui — vão para IA (BR-002: contato só se pedir explicitamente).
RESPOSTA_DISPONIBILIDADE_FRED = (
    "Não temos informação sobre a agenda em tempo real dos profissionais.<br><br>"
    "Para verificar a disponibilidade e agendar com o Fred, acesse:<br>"
    f"{LINK_APPBARBER}<br><br>"
    f"{_FECHAMENTO}"
)

# LGPD (Lei 13.709/2018): direito de acesso/exclusão de dados pessoais.
# Não expõe contato direto do Fred (BR-002) — usa o próprio canal de atendimento.
# PEDIDOS DE EXCLUSÃO são interceptados ANTES desta canônica pelo fluxo de
# confirmação em 2 passos do webhook (REGEX_LGPD_EXCLUSAO) — esta resposta
# cobre apenas consultas informativas ("política de privacidade", "que dados
# vocês têm"). A equipe também pode excluir via DELETE /admin/cliente/{telefone}.
RESPOSTA_APAGAR_DADOS = (
    "*Privacidade e seus dados (LGPD)*<br><br>"
    "Guardamos apenas o necessário para te atender: seu contato e o histórico desta conversa.<br><br>"
    "Se quiser removê-los, digite *apagar meus dados* e eu cuido do resto.<br><br>"
    f"{_FECHAMENTO}"
)

# Pedidos EXPLÍCITOS de exclusão de dados — dispara o fluxo de confirmação em
# 2 passos no webhook (que executa a exclusão de verdade). Mais restrito que o
# padrão canônico informativo acima: só verbos de remoção + objeto "dados/conta/…".
REGEX_LGPD_EXCLUSAO = re.compile(
    r"\b("
    r"(apagar|apague|deletar|delete|excluir|exclua|remover|remova)\s+"
    r"(os\s+|as\s+)?(meus?\s+|minhas?\s+)?(dados|informa[çc][oõ]es|hist[oó]rico|conta|cadastro)|"
    r"esquec(er|am)\s+(os\s+)?(meus?\s+)?dados|"
    r"direito\s+de\s+exclus[aã]o"
    r")\b",
    re.IGNORECASE,
)

# Cada entrada: (regex_compilado, resposta_canonica)
# Padrões são case-insensitive e usam fronteiras de palavra para evitar falsos positivos.
# ORDEM IMPORTA: padrões mais específicos antes dos genéricos (ex.: cancelar antes de agendar).
_PADROES = [
    # LGPD: direito de exclusão/acesso de dados pessoais — verificado cedo (termos específicos).
    (
        re.compile(
            r"\b("
            r"(apagar|deletar|excluir|remover)\s+(meus?\s+|minha\s+)?(dados|informa[çc][oõ]es|hist[oó]rico|conta|cadastro)|"
            r"esquec(er|am)\s+(meus?\s+)?dados|"
            r"(lgpd|prote[çc][aã]o\s+de\s+dados|direito\s+de\s+exclus[aã]o)|"
            r"pol[ií]tica\s+de\s+privacidade|"
            r"que\s+dados\s+(voc[eê]s\s+)?(t[eê]m|guardam|armazenam)"
            r")\b",
            re.IGNORECASE,
        ),
        RESPOSTA_APAGAR_DADOS,
    ),
    # Cancelamento / remarcação — ANTES de agendamento (palavras-chave podem coincidir).
    (
        re.compile(
            r"\b("
            r"cancel(ar|amento|o|a)|"
            r"desmarc(ar|o|a)|"
            r"remarc(ar|o|a|amento)|"
            r"transferir\s+(meu\s+)?(hor[aá]rio|agendamento)|"
            r"mudar\s+(o\s+)?(hor[aá]rio|dia|data)\s+(do|de)\s+(meu\s+)?agendamento|"
            r"alterar\s+(meu\s+)?(hor[aá]rio|agendamento)"
            r")\b",
            re.IGNORECASE,
        ),
        RESPOSTA_CANCELAR_REMARCAR,
    ),
    (
        re.compile(
            r"\b("
            r"hor[aá]rio(s)?|"
            r"que\s+horas?\s+(abre|fecha|funcion(a|am))|"
            r"funcionamento|"
            r"hor[aá]rio\s+de\s+atendimento|"
            r"abre[mn]?\s+que\s+horas?|"
            r"at[eé]\s+que\s+horas?"
            r")\b",
            re.IGNORECASE,
        ),
        RESPOSTA_HORARIO,
    ),
    (
        re.compile(
            r"\b("
            r"endere[çc]o|"
            r"localiza[çc][aã]o|"
            r"onde\s+(fica(m)?|[eé][^a-z]|s[aã]o|est[aã]o|voc[eê]s\s+(ficam|est[aã]o))|"
            r"como\s+chego|"
            r"qual\s+(o|a)\s+(endere[çc]o|localiza[çc][aã]o)|"
            r"fica\s+onde"
            r")\b",
            re.IGNORECASE,
        ),
        RESPOSTA_ENDERECO,
    ),
    (
        re.compile(
            r"\b("
            r"como\s+(eu\s+)?agend(o|ar|amento)|"
            r"como\s+marc(o|ar)|"
            r"como\s+(eu\s+)?fa[çc]o\s+para\s+(agendar|marcar)|"
            r"quero\s+(marcar|agendar|reservar)|"
            r"posso\s+(marcar|agendar|reservar)|"
            r"link\s+(do|de)\s+agendamento|"
            # B6: "app"/"aplicativo" SOZINHOS geravam falso positivo em qualquer frase
            # ("meu aplicativo de banco travou"). Agora: "appbarber" sempre casa;
            # "app/aplicativo" apenas com contexto de agendamento/barbearia.
            r"appbarber|"
            r"(baixar|baixo|usar|uso|pelo|link\s+do)\s+(o\s+)?(app|aplicativo)\b|"
            r"\b(app|aplicativo)\s+(de\s+agendamento|da\s+barbearia|de\s+voc[eê]s|para\s+(agendar|marcar))"
            r")\b",
            re.IGNORECASE,
        ),
        RESPOSTA_AGENDAMENTO,
    ),
    (
        re.compile(
            r"\b("
            r"formas?\s+de\s+pagamento|"
            r"como\s+(eu\s+)?pago|"
            r"aceitam?\s+(cart[aã]o|pix|dinheiro|d[eé]bito|cr[eé]dito)|"
            r"(pode\s+pagar|paga(m)?)\s+(com|no)\s+(cart[aã]o|pix|d[eé]bito|cr[eé]dito|dinheiro)|"
            r"(qual|quais)\s+(o|os|as)\s+pagamentos?|"
            r"tem\s+(maquininha|m[aá]quina)\s+(de\s+)?(cart[aã]o|cr[eé]dito|d[eé]bito)|"
            r"posso\s+(passar|usar)\s+(o\s+)?cart[aã]o|"
            # Marcas de banco/carteira digital — cliente pergunta sobre marca específica.
            # Resposta genérica cobre: Nubank é cartão débito/crédito; PicPay é cartão.
            r"aceitam?\s+(nubank|picpay|mercado\s+pago|inter|itau|bradesco|santander)|"
            r"(nubank|picpay|mercado\s+pago)\s+(funciona|aceita|vai|passa)"
            r")\b",
            re.IGNORECASE,
        ),
        RESPOSTA_PAGAMENTO,
    ),
    # Atendimento feminino: pergunta direta sobre público.
    (
        re.compile(
            r"\b("
            r"atende(m)?\s+(mulher(es)?|p[uú]blico\s+feminino|menina(s)?)|"
            r"corta(m)?\s+cabelo\s+(de\s+)?(mulher(es)?|feminino)|"
            r"cabelo\s+feminino|"
            r"mulher\s+pode\s+(ir|atender|cortar)|"
            r"atende(m)?\s+somente\s+homem"
            r")\b",
            re.IGNORECASE,
        ),
        RESPOSTA_ATENDIMENTO_FEMININO,
    ),
    (
        re.compile(
            r"\b("
            r"wi-?fi|"
            r"internet\s+(de\s+voc[eê]s|liberada|liberado|do\s+sal[aã]o|gr[aá]tis)|"
            r"climatiza(do|cao|ção)|"
            r"ar(\s+condicionado)?|"
            r"acessibilidade|"
            r"cadeirante|"
            r"(atende(m)?|tem\s+atendimento)\s+(crian[çc]a|infantil)|"
            r"estrutura|"
            # Acessibilidade para PCD: termos que o regex "cadeirante/acessibilidade" não cobre.
            r"deficiente(s)?|"
            r"pcd|"
            r"pessoa\s+(com\s+)?defici[eê]ncia|"
            r"mobilidade\s+reduzida|"
            r"cadeira\s+de\s+rodas"
            r")\b",
            re.IGNORECASE,
        ),
        RESPOSTA_FAQ_ESTRUTURA,
    ),
]


# Disponibilidade / slot de agendamento. Não confundir com horário de funcionamento.
# "tem horário amanhã?" = slot, NÃO operating hours. "qual o horário?" = operating hours.
_PADRAO_DISPONIBILIDADE = re.compile(
    r"\b("
    r"quem\s+tem\s+(hor[aá]rio|vaga|disponibilidade)|"
    r"tem\s+(hor[aá]rio|vaga|disponibilidade|como)\s+(pra|para|amanh[aã]|hoje|"
        r"depois\s+de\s+amanh[aã]|sexta|s[aá]bado|segunda|ter[çc]a|quarta|quinta|domingo|"
        r"de\s+manh[aã]|de\s+tarde|de\s+noite|\d{1,2}h)|"
    r"vaga\s+(pra|para)|"
    r"hor[aá]rio\s+(pra|para)\s+(amanh[aã]|hoje|sexta|s[aá]bado|segunda|ter[çc]a|quarta|quinta|domingo)"
    r")\b",
    re.IGNORECASE,
)


# Padrão de disponibilidade do Fred — verificado antes da exclusão geral de disponibilidade
# para que "fred tem horário amanhã?" retorne canônica em vez de ir para a IA.
_PADRAO_DISPONIBILIDADE_FRED = re.compile(
    r"\b("
    r"(o\s+)?fred\s+(t[aá]|est[aá]|vai\s+estar|vai\s+t[aá]|[eé]|trabalha|atende)\s+"
    r"(l[aá]|hoje|amanh[aã]|agora|disponivel|disponível)|"
    r"fred\s+tem\s+(hor[aá]rio|vaga)|"
    r"quando\s+(o\s+)?fred\s+(trabalha|atende)|"
    r"(o\s+)?fred\s+(trabalha|atende)\s+(hoje|amanh[aã]|s[aá]bado|segunda|ter[çc]a|quarta|quinta|sexta)"
    r")\b",
    re.IGNORECASE,
)


# Dias da semana em PT para montar o horário dinâmico (0=segunda ... 6=domingo).
_DIAS_SEMANA_PT = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


def _gerar_corpo_horario(db=None) -> str:
    """Monta o corpo do horário a partir da tabela `horarios` (fonte única, a mesma
    que a IA usa em ai_service). Fallback para o texto fixo `_CORPO_HORARIO` se o banco
    estiver vazio/indisponível — assim o comportamento sem-DB (testes) é idêntico ao
    antigo hardcode. Aceita uma sessão `db` (caller/testes) ou abre uma própria e fecha.
    """
    sessao_propria = False
    try:
        if db is None:
            from db.database import SessionLocal
            db = SessionLocal()
            sessao_propria = True
        from db.models import Horario
        registros = {r.dia_semana: r for r in db.query(Horario).all()}
        if not registros:
            return _CORPO_HORARIO
        partes = []
        for dia in range(7):
            reg = registros.get(dia)
            if reg is None or reg.fechado or not reg.abertura or not reg.fechamento:
                partes.append(f"{_DIAS_SEMANA_PT[dia]}: fechado")
            else:
                partes.append(f"{_DIAS_SEMANA_PT[dia]}: {reg.abertura} às {reg.fechamento}")
        return "*Nosso horário de funcionamento:*<br><br>" + "<br>".join(partes)
    except Exception:
        return _CORPO_HORARIO
    finally:
        if sessao_propria and db is not None:
            try:
                db.close()
            except Exception:
                pass


def detectar_resposta_canonica(texto_cliente: str, db=None) -> str | None:
    """
    Recebe a mensagem bruta do cliente. Devolve resposta canônica com tags <br>
    se algum padrão casar; caso contrário, devolve None (fluxo segue para IA).

    Exclusão: perguntas de disponibilidade (slot de agendamento) NÃO disparam
    canônico — mesmo que contenham "horário". Vão pra IA que tem contexto
    temporal e regra específica de disponibilidade.

    Exceção à exclusão: disponibilidade do Fred. "fred tem horário amanhã?" tem
    resposta canônica (orientar AppBarber) e não precisa de contexto temporal.
    """
    if not texto_cliente or not isinstance(texto_cliente, str):
        return None
    # Disponibilidade do Fred: verificada ANTES da exclusão geral de disponibilidade.
    if _PADRAO_DISPONIBILIDADE_FRED.search(texto_cliente):
        return RESPOSTA_DISPONIBILIDADE_FRED
    # Slot de agendamento genérico: envia para IA (tem contexto temporal e regra específica).
    if _PADRAO_DISPONIBILIDADE.search(texto_cliente):
        return None
    for regex, resposta in _PADROES:
        if regex.search(texto_cliente):
            # Horário: monta dinamicamente da tabela `horarios` (fonte única).
            # Fallback interno reproduz exatamente RESPOSTA_HORARIO se o banco estiver vazio.
            if resposta is RESPOSTA_HORARIO:
                return f"{_gerar_corpo_horario(db)}<br><br>{_FECHAMENTO}"
            return resposta
    return None
