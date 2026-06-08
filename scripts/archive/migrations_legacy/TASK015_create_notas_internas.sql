CREATE TABLE IF NOT EXISTS notas_internas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    telefone_usuario VARCHAR(20) NOT NULL,
    atendente_id INT NULL,
    texto TEXT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT NOW(),
    INDEX idx_notas_telefone (telefone_usuario),
    FOREIGN KEY (telefone_usuario) REFERENCES usuarios(telefone) ON DELETE CASCADE,
    FOREIGN KEY (atendente_id) REFERENCES atendentes(id) ON DELETE SET NULL
);
