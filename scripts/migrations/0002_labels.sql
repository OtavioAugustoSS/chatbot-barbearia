-- =============================================================
-- MIGRAÇÃO: Sistema de Labels Múltiplas Coloridas
-- Substitui o conceito de Usuario.tag (string única) por sistema
-- de múltiplas labels coloridas. Mantém coluna tag por compatibilidade
-- (será removida em migration posterior após validação).
-- Execute uma única vez em banco já populado.
-- =============================================================

CREATE TABLE IF NOT EXISTS labels (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(50) NOT NULL UNIQUE,
    cor VARCHAR(7) NOT NULL,
    descricao VARCHAR(200) NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_labels_ativo (ativo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS usuario_labels (
    telefone_usuario VARCHAR(20) NOT NULL,
    label_id INT NOT NULL,
    atribuido_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atribuido_por INT NULL,
    PRIMARY KEY (telefone_usuario, label_id),
    FOREIGN KEY (telefone_usuario) REFERENCES usuarios(telefone) ON DELETE CASCADE,
    FOREIGN KEY (label_id) REFERENCES labels(id) ON DELETE CASCADE,
    FOREIGN KEY (atribuido_por) REFERENCES atendentes(id) ON DELETE SET NULL,
    INDEX idx_ul_label (label_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Seed das labels que correspondem às tags legacy
INSERT INTO labels (nome, cor, descricao) VALUES
  ('resolvido',  '#10b981', 'Atendimento concluído com sucesso'),
  ('follow_up',  '#f59e0b', 'Requer acompanhamento posterior'),
  ('vip',        '#a855f7', 'Cliente VIP / prioritário'),
  ('reclamacao', '#ef4444', 'Reclamação ou problema reportado'),
  ('fidelidade', '#3b82f6', 'Cliente de programa de fidelidade')
ON DUPLICATE KEY UPDATE cor=VALUES(cor);

-- Migra Usuario.tag legacy para usuario_labels
INSERT IGNORE INTO usuario_labels (telefone_usuario, label_id)
SELECT u.telefone, l.id
FROM usuarios u
JOIN labels l ON l.nome = u.tag
WHERE u.tag IS NOT NULL;
