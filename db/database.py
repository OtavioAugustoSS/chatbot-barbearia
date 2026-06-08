import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "") 
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "barbearia_bot_db")

# URL de conexão para MySQL utilizando pymysql (driver recomendado).
# charset=utf8mb4 garante emoji/acentos em nome_cliente e mensagens (P1-2) — sem isso,
# servidor MySQL com default latin1 pode truncar ou dar "Incorrect string value".
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}?charset=utf8mb4"

# Engine com pool tuning:
# - pool_pre_ping: detecta conexões mortas antes de usar
# - pool_recycle: recicla conexões antes do MySQL fechar por idle (default 8h)
# - pool_size/max_overflow: dimensiona pool para ~30 mensagens simultâneas
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    connect_args={"connect_timeout": 10},
)

# Sessão do banco de dados
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para criar os modelos.
# ADR-014: naming_convention determinístico de constraints. Sem ele, o MySQL gera
# nomes implícitos que o autogenerate do Alembic não resolve, produzindo diffs falsos.
# Não afeta create_all (testes SQLite) — só nomeia constraints de forma estável.
_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
Base = declarative_base(metadata=MetaData(naming_convention=_NAMING_CONVENTION))

# Dependência que gera a sessão para as rotas do FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
