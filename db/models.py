from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, ForeignKey, Text, Table, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from db.database import Base

# Tabela associativa entre barbeiros e serviços (Muitos-para-Muitos)
barbeiros_servicos = Table(
    'barbeiros_servicos', Base.metadata,
    Column('barbeiro_id', Integer, ForeignKey('barbeiros.id', ondelete='CASCADE'), primary_key=True),
    Column('servico_id', Integer, ForeignKey('servicos.id', ondelete='CASCADE'), primary_key=True)
)

class Usuario(Base):
    __tablename__ = 'usuarios'

    telefone = Column(String(20), primary_key=True, index=True)
    nome_cliente = Column(String(100), nullable=True)
    bot_ativo = Column(Boolean, default=True)
    bot_desativado_em = Column(DateTime, nullable=True)
    # Modo híbrido: cliente pediu transbordo e ainda nenhum atendente assumiu.
    aguardando_humano = Column(Boolean, default=False)
    transbordo_em = Column(DateTime, nullable=True)
    # Atendente que assumiu a conversa. NULL = nenhum atendente ativo.
    atendente_id = Column(Integer, ForeignKey('atendentes.id', ondelete='SET NULL'), nullable=True)
    tag = Column(String(20), nullable=True, default=None)
    data_ultima_interacao = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    historico = relationship("HistoricoConversa", back_populates="usuario", cascade="all, delete-orphan")
    atendente = relationship("Atendente", foreign_keys=[atendente_id])


class HistoricoConversa(Base):
    __tablename__ = 'historico_conversas'

    id = Column(Integer, primary_key=True, index=True)
    telefone_usuario = Column(String(20), ForeignKey('usuarios.telefone', ondelete='CASCADE'))
    mensagem_cliente = Column(Text, nullable=True)
    resposta_bot = Column(Text, nullable=True)
    # Origem da resposta: "bot" (IA), "humano" (atendente via dashboard) ou "cliente"
    # (apenas mensagens do cliente registradas com bot inativo, sem resposta).
    origem = Column(String(10), default="bot")
    intencao = Column(String(30), nullable=True)
    atendente_id = Column(Integer, ForeignKey('atendentes.id', ondelete='SET NULL'), nullable=True)
    # Status de entrega ao WhatsApp via Meta Cloud API:
    # True = Meta aceitou (200 OK), False = falhou (4xx/5xx ou erro de rede),
    # None = não aplicável (linha só de mensagem do cliente, sem resposta saindo).
    entregue = Column(Boolean, nullable=True)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    usuario = relationship("Usuario", back_populates="historico")
    atendente = relationship("Atendente", foreign_keys=[atendente_id])

    # Índice composto: query padrão é WHERE telefone_usuario = X ORDER BY criado_em DESC.
    __table_args__ = (
        Index("idx_historico_telefone_data", "telefone_usuario", "criado_em"),
    )


class Atendente(Base):
    """Operador humano que assume conversas via dashboard (modo híbrido)."""
    __tablename__ = 'atendentes'

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    usuario_login = Column(String(50), unique=True, nullable=False, index=True)
    senha_hash = Column(String(255), nullable=False)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    ultimo_login = Column(DateTime, nullable=True)


class MensagemProcessada(Base):
    """Dedupe persistente de message.id da Meta. Sobrevive a restart do servidor."""
    __tablename__ = 'mensagens_processadas'

    message_id = Column(String(100), primary_key=True, index=True)
    processada_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class Servico(Base):
    __tablename__ = 'servicos'

    id = Column(Integer, primary_key=True, index=True)
    nome_servico = Column(String(100), nullable=False)
    descricao = Column(Text, nullable=True)
    preco = Column(Numeric(10, 2), nullable=False)
    tempo_estimado_minutos = Column(Integer, nullable=False)
    categoria = Column(String(20), nullable=False, default="barbearia")
    ativo = Column(Boolean, default=True, nullable=False)

    # Relacionamento MUITOS-PARA-MUITOS bidirecional
    barbeiros = relationship(
        "Barbeiro",
        secondary=barbeiros_servicos,
        back_populates="servicos"
    )


class Barbeiro(Base):
    __tablename__ = 'barbeiros'

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    dias_trabalho = Column(String(100), nullable=True)

    # Relacionamento MUITOS-PARA-MUITOS bidirecional
    servicos = relationship(
        "Servico",
        secondary=barbeiros_servicos,
        back_populates="barbeiros"
    )


class Horario(Base):
    """Horários de funcionamento por dia da semana (0=segunda ... 6=domingo)."""
    __tablename__ = "horarios"

    dia_semana = Column(Integer, primary_key=True)  # 0=Monday, 6=Sunday (Python weekday())
    abertura = Column(String(5), nullable=True)      # "HH:MM", NULL if fechado
    fechamento = Column(String(5), nullable=True)    # "HH:MM", NULL if fechado
    fechado = Column(Boolean, default=False, nullable=False)


class NotaInterna(Base):
    """Nota interna de atendente sobre um cliente (visível apenas no dashboard)."""
    __tablename__ = "notas_internas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telefone_usuario = Column(String(20), ForeignKey("usuarios.telefone", ondelete="CASCADE"), nullable=False)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    texto = Column(Text, nullable=False)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (Index("idx_notas_telefone", "telefone_usuario"),)
