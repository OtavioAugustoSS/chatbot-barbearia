"""
Configuração global do sistema.

MODO_OPERACAO controla se o bot opera sozinho ou com dashboard de atendente humano:
- "bot_only": IA responde tudo. Transbordo apenas desativa bot e reativa após N horas.
              Não há painel admin nem fila de espera.
- "hibrido":  IA + atendente humano via dashboard. Transbordo coloca cliente em fila,
              atendente assume via /admin/*, mensagens do cliente com bot inativo são
              persistidas (não dropadas) para o atendente responder.

Default: "bot_only" (preserva comportamento atual em caso de variável ausente).
"""
import os

MODO_OPERACAO = os.getenv("MODO_OPERACAO", "bot_only").strip().lower()

if MODO_OPERACAO not in ("bot_only", "hibrido"):
    raise ValueError(
        f"MODO_OPERACAO inválido: {MODO_OPERACAO!r}. Use 'bot_only' ou 'hibrido'."
    )

MODO_HIBRIDO = MODO_OPERACAO == "hibrido"
MODO_BOT_ONLY = MODO_OPERACAO == "bot_only"
