-- =============================================================
-- MIGRAÇÃO: Saved Views (filtros personalizados por atendente)
-- Permite cada atendente salvar combinações de filtros como atalhos
-- ("Aguardando hoje", "Resolvidos esta semana", etc.).
-- criterios é JSON com: { estado, status, label_ids, periodo, ... }
-- Execute uma única vez em banco já populado.
-- =============================================================

CREATE TABLE IF NOT EXISTS filtros_salvos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    atendente_id INT NOT NULL,
    nome VARCHAR(50) NOT NULL,
    criterios JSON NOT NULL,
    ordem INT NOT NULL DEFAULT 0,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (atendente_id) REFERENCES atendentes(id) ON DELETE CASCADE,
    UNIQUE KEY uk_atendente_nome (atendente_id, nome),
    INDEX idx_fs_atendente (atendente_id, ordem)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
