"""
Configuração global do sistema — fonte única de leitura de variáveis de ambiente.

MODO_OPERACAO controla se o bot opera sozinho ou com dashboard de atendente humano:
- "bot_only": IA responde tudo. Transbordo apenas desativa bot e reativa após N horas.
              Não há painel admin nem fila de espera.
- "hibrido":  IA + atendente humano via dashboard. Transbordo coloca cliente em fila,
              atendente assume via /admin/*, mensagens do cliente com bot inativo são
              persistidas (não dropadas) para o atendente responder.

MODO_DEV (derivado): ativo quando faltam credenciais reais e APP_ENV != "production".
Nele o sistema sobe com fallbacks seguros (SQLite local, IA demo, WhatsApp capturado
no simulador /dev/simulador, JWT efêmero) para permitir rodar e testar sem .env.
Com APP_ENV=production, qualquer credencial ausente aborta o boot com erro claro —
o modo dev nunca pode ser ativado silenciosamente em produção.
"""
import os
import secrets

from dotenv import load_dotenv

# Primeiro (e único necessário) load do .env — os load_dotenv() espalhados em outros
# módulos tornam-se inócuos, mas permanecem inofensivos.
load_dotenv()


def _env_int(nome: str, default: int) -> int:
    """Lê env var inteira com validação — valor não-numérico aborta com mensagem clara."""
    bruto = os.getenv(nome, "")
    if not bruto.strip():
        return default
    try:
        return int(bruto)
    except ValueError:
        raise RuntimeError(
            f"{nome}={bruto!r} inválido — use um número inteiro (ex.: {nome}={default})."
        )


APP_ENV = os.getenv("APP_ENV", "").strip().lower()  # "" = auto, "development", "production"

# ---------------------------------------------------------------------------
# Credenciais e parâmetros lidos centralmente
# ---------------------------------------------------------------------------
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "").strip()
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "").strip()
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "").strip()
META_APP_SECRET = os.getenv("META_APP_SECRET", "").strip()
WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "").strip()
ADMIN_PHONES = {p.strip() for p in os.getenv("ADMIN_PHONES", "").split(",") if p.strip()}
BOT_REATIVAR_APOS_HORAS = _env_int("BOT_REATIVAR_APOS_HORAS", 24)
JWT_TTL_MIN = _env_int("JWT_TTL_MIN", 15)
CB_FAILURE_THRESHOLD = _env_int("CB_FAILURE_THRESHOLD", 3)
CB_RESET_TIMEOUT = _env_int("CB_RESET_TIMEOUT", 30)

# ---------------------------------------------------------------------------
# Flags de subsistema fake (modo dev)
# ---------------------------------------------------------------------------
IA_FAKE = not NVIDIA_API_KEY
WHATSAPP_FAKE = not (WHATSAPP_TOKEN and WHATSAPP_PHONE_ID)

# DB: DB_URL explícita > DB_* (MySQL, comportamento atual) > SQLite dev.
# Detecção por PRESENÇA de config, nunca por tentativa de conexão — MySQL caído em
# produção jamais pode virar SQLite silencioso.
DB_URL_EXPLICITA = os.getenv("DB_URL", "").strip()
_TEM_DB_CONFIG = any(os.getenv(k) is not None for k in ("DB_USER", "DB_PASS", "DB_HOST", "DB_NAME"))
DB_SQLITE_DEV = not DB_URL_EXPLICITA and not _TEM_DB_CONFIG

# MODO_DEV agregado — nunca em production.
MODO_DEV = (APP_ENV == "development") or (
    APP_ENV != "production" and (DB_SQLITE_DEV or IA_FAKE or WHATSAPP_FAKE)
)

# Gate de produção: credencial faltando com APP_ENV=production é erro imediato,
# não fallback silencioso.
if APP_ENV == "production":
    _faltando = [
        nome
        for nome, valor in (
            ("NVIDIA_API_KEY", NVIDIA_API_KEY),
            ("WHATSAPP_TOKEN", WHATSAPP_TOKEN),
            ("WHATSAPP_PHONE_ID", WHATSAPP_PHONE_ID),
            ("META_APP_SECRET", META_APP_SECRET),
        )
        if not valor
    ]
    if DB_SQLITE_DEV:
        _faltando.append("DB_USER/DB_PASS/DB_HOST/DB_NAME (ou DB_URL)")
    if _faltando:
        raise RuntimeError(
            "APP_ENV=production mas faltam credenciais no .env: "
            + ", ".join(_faltando)
            + ". Preencha-as ou remova APP_ENV=production para rodar em modo dev."
        )

# Rate limit mais folgado em dev (simulador manda mensagens em rajada ao clicar menus).
RATE_LIMIT_MSGS_POR_MINUTO = _env_int("RATE_LIMIT_MSGS_POR_MINUTO", 60 if MODO_DEV else 10)

# ---------------------------------------------------------------------------
# MODO_OPERACAO — default "hibrido" em dev (dashboard demoável de cara),
# "bot_only" fora de dev (preserva comportamento atual).
# ---------------------------------------------------------------------------
_MODO_DEFAULT = "hibrido" if MODO_DEV else "bot_only"
MODO_OPERACAO = os.getenv("MODO_OPERACAO", _MODO_DEFAULT).strip().lower()

if MODO_OPERACAO not in ("bot_only", "hibrido"):
    raise ValueError(
        f"MODO_OPERACAO inválido: {MODO_OPERACAO!r}. Use 'bot_only' ou 'hibrido'."
    )

MODO_HIBRIDO = MODO_OPERACAO == "hibrido"
MODO_BOT_ONLY = MODO_OPERACAO == "bot_only"

# ---------------------------------------------------------------------------
# JWT: efêmero em dev (tokens invalidam a cada restart — aceitável para demo).
# ---------------------------------------------------------------------------
JWT_SECRET = os.getenv("JWT_SECRET", "").strip()
JWT_SECRET_EFEMERO = False
if not JWT_SECRET and MODO_DEV:
    JWT_SECRET = secrets.token_hex(32)
    JWT_SECRET_EFEMERO = True

# Webhook sem assinatura: em dev sem META_APP_SECRET aceita automaticamente;
# fora de dev continua exigindo opt-in explícito via ALLOW_UNSIGNED_WEBHOOK=1.
ALLOW_UNSIGNED_WEBHOOK = (
    os.getenv("ALLOW_UNSIGNED_WEBHOOK", "") == "1" or (MODO_DEV and not META_APP_SECRET)
)
