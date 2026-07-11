"""
Fixtures de teste para o chatbot-barbearia.

Estratégia:
- SQLite in-memory substituindo MySQL (tipos genéricos SQLAlchemy são compatíveis).
- Variáveis de ambiente críticas definidas antes de qualquer import dos módulos da aplicação.
- `db.database.engine` e `SessionLocal` são substituídos pelo engine SQLite ANTES de
  qualquer import de `main.py` — evita o `Base.metadata.create_all(bind=engine)` que
  tentaria conectar ao MySQL na linha 37 de main.py.
- get_db sobrescrito via FastAPI dependency_overrides para usar sessão SQLite.
- Mocks de rede (WhatsApp + NVIDIA NIM) garantem zero chamadas externas.
"""
import os

# --- Env de teste ANTES de qualquer import da aplicação ---
os.environ["MODO_OPERACAO"] = "hibrido"
os.environ["JWT_SECRET"] = "test-secret-do-not-use-in-prod-32chars!!"
os.environ["JWT_TTL_MIN"] = "60"
os.environ["META_APP_SECRET"] = ""
os.environ["ALLOW_UNSIGNED_WEBHOOK"] = "1"  # gate de boot requer este flag quando META_APP_SECRET vazio
os.environ["DB_USER"] = "test"
os.environ["DB_PASS"] = "test"
os.environ["DB_HOST"] = "localhost"
os.environ["DB_NAME"] = "test"
os.environ["WHATSAPP_TOKEN"] = "test-token"
os.environ["WHATSAPP_PHONE_ID"] = "000000000"
os.environ["NVIDIA_API_KEY"] = "test-key"
os.environ["BOT_REATIVAR_APOS_HORAS"] = "24"
os.environ["RATE_LIMIT_MSGS_POR_MINUTO"] = "10"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Cria engine SQLite ANTES de importar db.database (que cria o engine MySQL em nível de módulo).
SQLITE_URL = "sqlite://"
engine_teste = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SessionTeste = sessionmaker(autocommit=False, autoflush=False, bind=engine_teste)

# Substitui o engine e SessionLocal do módulo db.database antes de qualquer import subsequente.
# Isso garante que main.py:37 (`Base.metadata.create_all(bind=engine)`) use SQLite.
import db.database as _db_mod
_db_mod.engine = engine_teste
_db_mod.SessionLocal = SessionTeste

# Agora importa o resto
import pytest
from fastapi.testclient import TestClient
from db.database import Base, get_db
from db.models import Atendente, Usuario, MensagemProcessada, NotaInterna, Label
from api.auth import hash_senha, criar_token


@pytest.fixture(scope="session", autouse=True)
def criar_tabelas():
    """Cria todas as tabelas SQLite uma vez por sessão de teste."""
    Base.metadata.create_all(bind=engine_teste)
    yield
    Base.metadata.drop_all(bind=engine_teste)


@pytest.fixture()
def db():
    """
    Sessão SQLite por teste.
    Com StaticPool + in-memory SQLite, o rollback não desfaz commits já feitos.
    Estratégia: truncar todas as tabelas após cada teste (tabelas são pequenas em testes).
    """
    sessao = SessionTeste()
    yield sessao
    sessao.close()
    # Limpa todas as tabelas para isolar os testes
    with engine_teste.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()


def _override_get_db_factory(sessao):
    def _override():
        try:
            yield sessao
        finally:
            pass
    return _override


@pytest.fixture()
def app(db):
    """App FastAPI de teste com get_db sobrescrito para usar SQLite."""
    from main import app as _app
    _app.dependency_overrides[get_db] = _override_get_db_factory(db)
    yield _app
    _app.dependency_overrides.clear()


@pytest.fixture()
def client(app):
    """TestClient para a app de teste."""
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture()
def atendente_teste(db):
    """Cria um Atendente ADMIN no banco com senha conhecida.

    role='admin' para que os testes existentes de gestão de atendentes,
    horários e LGPD continuem passando após o RBAC (H2). Use `atendente_comum`
    para testar o 403 dos endpoints restritos.
    """
    atendente = Atendente(
        nome="Atendente Teste",
        usuario_login="teste",
        senha_hash=hash_senha("senha123"),
        role="admin",
        ativo=True,
    )
    db.add(atendente)
    db.commit()
    db.refresh(atendente)
    return atendente


@pytest.fixture()
def token(atendente_teste):
    """JWT válido para o atendente de teste."""
    return criar_token(atendente_teste)


@pytest.fixture()
def auth_headers(token):
    """Header Authorization pronto para uso nos requests."""
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def atendente_comum(db):
    """Atendente SEM perfil admin — para testar RBAC (403 nos endpoints restritos)."""
    atendente = Atendente(
        nome="Atendente Comum",
        usuario_login="comum",
        senha_hash=hash_senha("senha123"),
        role="atendente",
        ativo=True,
    )
    db.add(atendente)
    db.commit()
    db.refresh(atendente)
    return atendente


@pytest.fixture()
def auth_headers_comum(atendente_comum):
    """Header Authorization do atendente comum (não-admin)."""
    return {"Authorization": f"Bearer {criar_token(atendente_comum)}"}


@pytest.fixture()
def usuario_teste(db):
    """Cria um Usuario (cliente WhatsApp) no banco."""
    usuario = Usuario(
        telefone="5538999990001",
        nome_cliente="Cliente Teste",
        bot_ativo=True,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@pytest.fixture(autouse=True)
def mock_externos(monkeypatch):
    """Mock automático de todas as chamadas de rede externas."""
    import services.whatsapp as _wa_mod
    monkeypatch.setattr(
        _wa_mod.WhatsAppSender, "enviar_mensagem_texto",
        lambda self, numero, texto: (True, "wamid.test123"),
    )
    monkeypatch.setattr(
        _wa_mod.WhatsAppSender, "enviar_lista_interativa",
        lambda self, **kwargs: (True, "wamid.list123"),
    )
    monkeypatch.setattr(
        _wa_mod.WhatsAppSender, "enviar_botoes_resposta",
        lambda self, **kwargs: (True, "wamid.btn123"),
    )
    monkeypatch.setattr(
        _wa_mod.WhatsAppSender, "marcar_como_lida",
        lambda self, message_id, numero: True,
    )

    # Retry de status (race wamid) sem sleep nos testes.
    import api.webhook as _wh_mod
    monkeypatch.setattr(_wh_mod, "_STATUS_RETRY_DELAY_S", 0)

    import services.ai_service as _ai_mod

    class _FakeChoice:
        finish_reason = "stop"  # acessado como completion.choices[0].finish_reason

        class _FakeMsg:
            content = '{"intencao": "tirar_duvida", "resposta_sugerida": "Resposta de teste."}'
        message = _FakeMsg()

    class _FakeCompletion:
        choices = [_FakeChoice()]

    monkeypatch.setattr(
        _ai_mod.AIService, "_chamar_llm",
        lambda self, messages: _FakeCompletion(),
    )


def _montar_payload_webhook(telefone: str, texto: str, message_id: str = "msg001", nome: str = "Teste") -> dict:
    """Helper: monta payload Meta Cloud API para POST /webhook."""
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "entry1",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "55999990000", "phone_number_id": "000"},
                    "contacts": [{"profile": {"name": nome}, "wa_id": telefone}],
                    "messages": [{
                        "from": telefone,
                        "id": message_id,
                        "timestamp": "1700000000",
                        "type": "text",
                        "text": {"body": texto},
                    }],
                },
                "field": "messages",
            }],
        }],
    }
