-- =============================================================
-- MIGRAÇÃO: Status de Conversa (Chatwoot-style)
-- Adiciona máquina de estados clara: open, pending, resolved, snoozed.
-- Complementa flags existentes (bot_ativo, aguardando_humano, atendente_id)
-- — não substitui, coexistem ortogonalmente.
--   open:     conversa ativa, atendente pode responder
--   pending:  aguardando resposta do cliente (estado inicial após resolve parcial)
--   resolved: encerrada — sai dos filtros padrão
--   snoozed:  oculta até snoozed_until; check on-read volta para open
-- Execute uma única vez em banco já populado.
-- =============================================================

ALTER TABLE usuarios
    ADD COLUMN status_conversa ENUM('open','pending','resolved','snoozed') NOT NULL DEFAULT 'open',
    ADD COLUMN snoozed_until DATETIME NULL DEFAULT NULL,
    ADD COLUMN resolved_em DATETIME NULL DEFAULT NULL,
    ADD COLUMN resolved_por INT NULL DEFAULT NULL,
    ADD INDEX idx_status_conversa (status_conversa),
    ADD INDEX idx_snoozed_until (snoozed_until),
    ADD CONSTRAINT fk_resolved_por FOREIGN KEY (resolved_por) REFERENCES atendentes(id) ON DELETE SET NULL;
