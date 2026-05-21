-- =============================================================
-- MIGRAÇÃO: Notificações de @mentions em notas internas
-- Permite colaboração entre atendentes: ao escrever uma nota com
-- "@usuario_login", o sistema gera notificação para o mencionado.
-- Execute uma única vez em banco já populado.
-- =============================================================

CREATE TABLE IF NOT EXISTS mention_notificacoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    atendente_id INT NOT NULL,           -- quem foi mencionado
    nota_id INT NOT NULL,
    telefone_usuario VARCHAR(20) NOT NULL,
    mencionado_por INT NULL,             -- quem criou a nota (autor da mention)
    lida BOOLEAN NOT NULL DEFAULT FALSE,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    lida_em DATETIME NULL DEFAULT NULL,
    FOREIGN KEY (atendente_id) REFERENCES atendentes(id) ON DELETE CASCADE,
    FOREIGN KEY (nota_id) REFERENCES notas_internas(id) ON DELETE CASCADE,
    FOREIGN KEY (mencionado_por) REFERENCES atendentes(id) ON DELETE SET NULL,
    FOREIGN KEY (telefone_usuario) REFERENCES usuarios(telefone) ON DELETE CASCADE,
    INDEX idx_mn_atendente_lida (atendente_id, lida),
    INDEX idx_mn_nota (nota_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
