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
_CORPO_HORARIO = (
    "*Nosso horário de funcionamento:*<br><br>"
    "Segunda: 14:00 às 21:00<br>"
    "Terça a Sexta: 09:00 às 21:00<br>"
    "Sábado: 09:00 às 18:00<br>"
    "Domingo: fechado"
)

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

# Cada entrada: (regex_compilado, resposta_canonica)
# Padrões são case-insensitive e usam fronteiras de palavra para evitar falsos positivos.
# ORDEM IMPORTA: padrões mais específicos antes dos genéricos (ex.: cancelar antes de agendar).
_PADROES = [
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
            r"(qual|quais)\s+(o|os|as)\s+pagamentos?|"
            r"tem\s+(maquininha|m[aá]quina)\s+(de\s+)?(cart[aã]o|cr[eé]dito|d[eé]bito)|"
            r"posso\s+(passar|usar)\s+(o\s+)?cart[aã]o"
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
