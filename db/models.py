from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, Table
from sqlalchemy.orm import relationship
from datetime import datetime
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
    estado_atual = Column(String(50), default="BOAS_VINDAS")
    bot_ativo = Column(Boolean, default=True)
    data_ultima_interacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamento UM-PARA-MUITOS (Usuário tem vários Históricos)
    historico = relationship("HistoricoConversa", back_populates="usuario", cascade="all, delete-orphan")


class HistoricoConversa(Base):
    __tablename__ = 'historico_conversas'

    id = Column(Integer, primary_key=True, index=True)
    telefone_usuario = Column(String(20), ForeignKey('usuarios.telefone', ondelete='CASCADE'))
    mensagem_cliente = Column(Text, nullable=True)
    resposta_bot = Column(Text, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    # Relacionamento Múltiplos-para-Um (Vários históricos pertencem a um Usuário)
    usuario = relationship("Usuario", back_populates="historico")


class Servico(Base):
    __tablename__ = 'servicos'

    id = Column(Integer, primary_key=True, index=True)
    nome_servico = Column(String(100), nullable=False)
    descricao = Column(Text, nullable=True)
    preco = Column(Float, nullable=False)
    tempo_estimado_minutos = Column(Integer, nullable=False)

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
