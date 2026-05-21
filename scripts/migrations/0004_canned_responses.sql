-- =============================================================
-- MIGRAÇÃO: Canned Responses (respostas rápidas dinâmicas)
-- Substitui CANNED_RESPONSES hardcoded no JS. Suporta:
--   - Globais (atendente_id IS NULL): visíveis a todos os atendentes
--   - Pessoais (atendente_id != NULL): apenas o dono vê e edita
--   - Placeholders no texto: {nome_cliente}, {primeiro_nome},
--     {atendente}, {barbearia} (substituídos no envio)
-- Atalhos digitados no composer (ex.: "/horario") buscam por prefix.
-- Execute uma única vez em banco já populado.
-- =============================================================

CREATE TABLE IF NOT EXISTS canned_responses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    atalho VARCHAR(30) NOT NULL,
    texto TEXT NOT NULL,
    atendente_id INT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NULL DEFAULT NULL,
    FOREIGN KEY (atendente_id) REFERENCES atendentes(id) ON DELETE CASCADE,
    UNIQUE KEY uk_atalho_atendente (atalho, atendente_id),
    INDEX idx_canned_atendente (atendente_id),
    INDEX idx_canned_atalho (atalho)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Seed com as 8 canned responses do JS atual como GLOBAIS (atendente_id IS NULL)
INSERT IGNORE INTO canned_responses (atalho, texto, atendente_id) VALUES
  ('/saudacao',        'Olá {primeiro_nome}! Sou {atendente}, do atendimento da {barbearia}. Como posso te ajudar?', NULL),
  ('/verificar',       'Vou verificar isso para você. Um momento, por favor.', NULL),
  ('/agendar',         'Para agendar, acesse nosso app: https://sites.appbarber.com.br/bolshoi', NULL),
  ('/horario',         'Nosso horário de funcionamento é de segunda a sábado, das 9h às 19h.', NULL),
  ('/encaminhar',      'Pode deixar! Vou encaminhar sua solicitação.', NULL),
  ('/maisajuda',       'Tem mais alguma dúvida que eu possa te ajudar?', NULL),
  ('/despedida',       'Obrigado pelo contato, {primeiro_nome}! Até logo.', NULL),
  ('/disponibilidade', 'Estou verificando a disponibilidade dos nossos profissionais.', NULL);
