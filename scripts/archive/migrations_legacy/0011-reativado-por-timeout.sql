-- B4: US-GAP-02 — Adicionar campo reativado_por_timeout em usuarios
-- Flag setada quando o bot é reativado automaticamente por BOT_REATIVAR_APOS_HORAS.
-- Consumida na próxima resposta para prefixar frase de contexto; resetada após uso.
ALTER TABLE usuarios
    ADD COLUMN reativado_por_timeout BOOLEAN NOT NULL DEFAULT FALSE;
