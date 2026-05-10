"""
Respostas canônicas determinísticas. Detecta intenções simples via regex
e devolve texto literal SEM acionar a IA. Reduz custo de tokens, elimina
variações estéticas e zera risco de alucinação para perguntas frequentes.

Quando NÃO casar nenhum padrão, devolve None e o fluxo segue para a IA.
"""

import re

# Link AppBarber e contato (fontes da verdade — qualquer mudança vem aqui)
LINK_APPBARBER = "https://sites.appbarber.com.br/bolshoi"
LINK_MAPA = "https://www.google.com/maps/search/?api=1&query=-16.36553001%2C-46.89651871"

RESPOSTA_HORARIO = (
    "Nosso horário de funcionamento:<br><br>"
    "Segunda: 14:00 às 21:00<br>"
    "Terça a Sexta: 09:00 às 21:00<br>"
    "Sábado: 09:00 às 18:00<br>"
    "Domingo: fechado<br><br>"
    "Posso ajudar em algo mais?"
)

RESPOSTA_ENDERECO = (
    "📍 Estamos em:<br><br>"
    "R. Zaida Torres Martins, 195<br>"
    "Bairro Cruzeiro - Unaí/MG<br>"
    "CEP 38616-016<br><br>"
    f"Mapa: {LINK_MAPA}"
)

RESPOSTA_AGENDAMENTO = (
    "Agendamentos são feitos exclusivamente pelo nosso aplicativo oficial:<br><br>"
    f"{LINK_APPBARBER}<br><br>"
    "Lá você escolhe serviço, barbeiro e horário."
)

RESPOSTA_PAGAMENTO = (
    "Aceitamos as seguintes formas de pagamento (no estabelecimento):<br><br>"
    "💵 Dinheiro<br>"
    "📱 Pix<br>"
    "💳 Cartão de Débito<br>"
    "💳 Cartão de Crédito"
)

RESPOSTA_FAQ_ESTRUTURA = (
    "🏢 Nossa estrutura oferece:<br><br>"
    "✅ Wi-Fi Ultra-Rápido<br>"
    "✅ Ambiente totalmente climatizado<br>"
    "✅ Pagamento: Pix, Dinheiro e Cartões<br>"
    "✅ Atendimento especializado Infantil<br>"
    "✅ Acessibilidade Completa (Cadeirantes)<br><br>"
    "Posso ajudar em algo mais?"
)

# Cada entrada: (regex_compilado, resposta_canonica)
# Padrões são case-insensitive e usam fronteiras de palavra para evitar falsos positivos.
_PADROES = [
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
            r"quero\s+(marcar|agendar|reservar)|"
            r"posso\s+(marcar|agendar|reservar)|"
            r"link\s+(do|de)\s+agendamento|"
            r"app(barber)?|"
            r"aplicativo"
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
            r"(qual|quais)\s+(o|os|as)\s+pagamentos?"
            r")\b",
            re.IGNORECASE,
        ),
        RESPOSTA_PAGAMENTO,
    ),
    (
        re.compile(
            r"\b("
            r"wi-?fi|"
            r"climatiza(do|cao|ção)|"
            r"ar(\s+condicionado)?|"
            r"acessibilidade|"
            r"cadeirante|"
            r"(atende(m)?|tem\s+atendimento)\s+(crian[çc]a|infantil)|"
            r"estrutura"
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


def detectar_resposta_canonica(texto_cliente: str) -> str | None:
    """
    Recebe a mensagem bruta do cliente. Devolve resposta canônica com tags <br>
    se algum padrão casar; caso contrário, devolve None (fluxo segue para IA).

    Exclusão: perguntas de disponibilidade (slot de agendamento) NÃO disparam
    canônico — mesmo que contenham "horário". Vão pra IA que tem contexto
    temporal e regra específica de disponibilidade.
    """
    if not texto_cliente or not isinstance(texto_cliente, str):
        return None
    if _PADRAO_DISPONIBILIDADE.search(texto_cliente):
        return None
    for regex, resposta in _PADROES:
        if regex.search(texto_cliente):
            return resposta
    return None
