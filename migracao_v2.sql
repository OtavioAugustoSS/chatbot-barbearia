-- =============================================================
-- MIGRAÇÃO v2 — Barbearia Bolshoi
-- MySQL 8.4.7
-- ATENÇÃO: NÃO é idempotente. Rodar UMA VEZ apenas.
-- Se rodar duas vezes, dá erro 1060 / 1061 (objeto já existe) — esperado.
-- =============================================================

USE barbearia_bot_db;

-- 1. Coluna para reativação automática do bot após N horas
ALTER TABLE usuarios
    ADD COLUMN bot_desativado_em DATETIME NULL;

-- 2. Índice composto: acelera query principal do histórico
CREATE INDEX idx_historico_telefone_data
    ON historico_conversas (telefone_usuario, criado_em);

-- 3. Tabela de dedupe persistente (sobrevive a restart do servidor)
CREATE TABLE IF NOT EXISTS mensagens_processadas (
    message_id VARCHAR(100) PRIMARY KEY,
    processada_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_mensagens_processadas_data (processada_em)
);
