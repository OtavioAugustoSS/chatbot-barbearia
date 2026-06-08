# Barbearia Bolshoi — bot WhatsApp + dashboard de atendentes (FastAPI)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# pymysql é puro Python — sem build-essential necessário.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Segredos vêm via `--env-file .env` em runtime. NUNCA copie o .env pra imagem
# (o .dockerignore já exclui, mas reforçando aqui).
EXPOSE 8000

# Health-check do container bate no /health (que testa o banco de verdade).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3).status==200 else 1)"

# IMPORTANTE: 1 worker apenas. Estado em memória (SSE/lock/rate-limit) NÃO suporta
# multi-worker hoje (ver P1-10 em docs/review/production-readiness-2026-06.md).
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
