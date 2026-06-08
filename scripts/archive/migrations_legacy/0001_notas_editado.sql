-- =============================================================
-- MIGRAÇÃO: Auditoria de edição em notas_internas
-- Adiciona suporte para rastreamento de edições de notas
-- Execute uma única vez em banco já populado.
-- =============================================================

ALTER TABLE notas_internas ADD COLUMN editado_em DATETIME NULL DEFAULT NULL;
ALTER TABLE notas_internas ADD COLUMN editado_por INT NULL DEFAULT NULL;
ALTER TABLE notas_internas
    ADD CONSTRAINT fk_notas_editado_por
    FOREIGN KEY (editado_por) REFERENCES atendentes(id) ON DELETE SET NULL;
