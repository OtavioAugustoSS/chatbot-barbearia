-- =============================================================
-- MIGRAÇÃO: Backfill NULL → 'open' em status_conversa
-- A coluna status_conversa foi adicionada em 0003 com DEFAULT 'open'.
-- Registros pré-existentes (criados antes dessa migration) permaneceram NULL.
-- Filtros SQL com "WHERE status_conversa = 'open'" excluem NULLs (SQL standard),
-- causando que conversas legadas sumissem do dashboard.
-- Idempotente — roda múltiplas vezes sem erro.
-- =============================================================

UPDATE usuarios
SET status_conversa = 'open'
WHERE status_conversa IS NULL;
