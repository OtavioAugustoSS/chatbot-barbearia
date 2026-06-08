-- ============================================================================
-- LEGADO — NÃO USAR. Schema inicial (~5 tabelas), desatualizado desde a Sprint 0.1.
-- Fonte de verdade atual do schema: db/models.py + alembic/versions/ (ADR-014).
-- Para provisionar um banco: ver docs/deploy/runbook.md (seção Migrations).
-- Mantido apenas como referência histórica.
-- ============================================================================

create database barbearia_bot_db;

use barbearia_bot_db;

create table usuarios (
	telefone varchar(20) primary key,
	nome_cliente varchar(100),
	bot_ativo boolean default true,
	data_ultima_interacao timestamp default current_timestamp on update current_timestamp
);

create table historico_conversas(
	ID int auto_increment primary key,
    telefone_usuario varchar(20),
    mensagem_cliente text,
    resposta_bot text,
    criado_em timestamp default current_timestamp,
    foreign key (telefone_usuario) references usuarios(telefone) on delete cascade
);

create table servicos(
	id int auto_increment primary key,
    nome_servico varchar(100) not null,
    descricao text,
    preco decimal(10,2) not null,
    tempo_estimado_minutos int,
    categoria varchar(20) not null default 'barbearia'
);

create table barbeiros(
	id int auto_increment primary key,
    nome varchar(100) not null,
    dias_trabalho varchar(100)
);

create table barbeiros_servicos(
	barbeiro_id int,
    servico_id int,
    primary key (barbeiro_id, servico_id),
    foreign key (barbeiro_id) references barbeiros(id) on delete cascade,
    foreign key (servico_id) references servicos(id) on delete cascade
);

insert into servicos (nome_servico, descricao, preco, tempo_estimado_minutos, categoria) values
-- id 1-2: barbearia
('Acabamento','Acabamento simples do corte no cabelo', 30.00, 30, 'barbearia'),
('Barba','Alinhamento e corte da barba com toalha quente.', 50.00, 30, 'barbearia'),
-- id 3: estetica
('Brow Lamination','Procedimento estético que alinha, levanta e molda os pelos naturais das sobrancelhas para cima, criando um efeito volumoso, preenchido.', 100.00, 90, 'estetica'),
-- id 4-8: barbearia
('Corte','Corte de cabelo no estilo que o cliente preferir', 50.00, 30, 'barbearia'),
('Corte com Desenho','Corte com desenho na escolha do cliente', 80.00, 60, 'barbearia'),
('Corte e Barba','Corte de cabelo no estilo que o cliente preferir e alinhamento e corte da barba com toalha quente.', 90.00, 60, 'barbearia'),
('Corte Infantil 0 a 3 anos','Temos atendimentos para crianças de 0 a 3 anos', 50.00, 30, 'barbearia'),
('Corte Infantil 4 a 7 anos','Temos atendimentos para crianças de 4 a 7 anos', 50.00, 30, 'barbearia'),
-- id 9-13: estetica
('Dermaplaning','Dermaplaning é um procedimento estético que envolve remover células mortas e pelos faciais (penugens) do rosto. Seu objetivo é deixar a pele mais lisa, macia e com aparência rejuvenescida.', 100.00, 60, 'estetica'),
('Design Sobrancelha','Técnica que busca alinhar os pelos da sobrancelha com harmonização de rosto da cliente, desenhando a curvatura mais adequada.', 45.00, 30, 'estetica'),
('Design Sobrancelha Henna','Técnica que busca alinhar os pelos da sobrancelha com harmonização de rosto da cliente, desenhando a curvatura mais adequada.', 60.00, 60, 'estetica'),
('Design Sobrancelha Tintura','Técnica que busca alinhar os pelos da sobrancelha com harmonização de rosto da cliente, desenhando a curvatura mais adequada.', 80.00, 60, 'estetica'),
('Extensão de Cílios','Extensão de cílios no estilo que a cliente desejar', 120.00, 120, 'estetica'),
-- id 14: barbearia
('Hidratação Masculina','Utilizada para repor a umidade natural, nutrientes e queratina perdida. A hidratação constante é uma grande aliada para manter os cabelos saudáveis, com brilho, sedoso e macios.', 40.00, 30, 'barbearia'),
-- id 15-18: estetica
('Lash Lifting - Cílios','Essa técnica pode ser considerada a evolução do antigo permanente de cílios. além de curvar os cílios natural, e entregar uma cor mais viva aos fios, o lash lift possui uma formulação que trata os fios, auxiliam a ficarem mais saudáveis.', 150.00, 120, 'estetica'),
('Limpeza de Pele','Higieniza, esfolia e remove células mortas. Os poros purificados previnem a acne e a oleosidade.', 80.00, 30, 'estetica'),
('Limpeza de Pele Profunda','Procedimento envolve higienização, esfoliação, extração de cravos manualmente e máscara hidratante.', 100.00, 90, 'estetica'),
('Nanoblading','Nanoblading é uma técnica avançada de micro pigmentação de sobrancelhas que visa criar um visual natural e preenchido, utilizando lâminas ultrafinas para desenhar fios individuais que imitam o crescimento natural dos pelos. É uma evolução do microblading, oferecendo resultados ainda mais precisos e delicados.', 650.00, 120, 'estetica'),
-- id 19-22: barbearia
('Pigmentação Barba','Procedimento estético que aplica pigmentos nos fios para simular densidade, cobrir falhas e cicatrizes, ou realçar cortes.', 50.00, 30, 'barbearia'),
('Pigmentação Cabelo','Procedimento estético que aplica pigmentos nos fios para simular densidade, cobrir falhas e cicatrizes, ou realçar cortes.', 50.00, 30, 'barbearia'),
('Pigmentação Cabelo e Barba','Procedimento estético que aplica pigmentos nos fios para simular densidade, cobrir falhas e cicatrizes, ou realçar cortes.', 90.00, 30, 'barbearia'),
('Selagem','Tratamento focado em selar as cutículas dos fios, criando uma camada protetora que reduz a porosidade, o frizz e o volume, além de aumentar o brilho.', 85.00, 60, 'barbearia'),
-- id 23: estetica
('Sobrancelha na Cera','Sobrancelha feita na cera.', 45.00, 30, 'estetica'),
-- id 24: barbearia
('Sobrancelha na Navalha','Sobrancelha feita na navalha.', 40.00, 30, 'barbearia');

insert into barbeiros (nome, dias_trabalho) values
('Fred', 'Segunda à sábado'),
('Isabella', 'Segunda à sábado'),
('Fernando', 'Segunda à sábado'),
('Eduardo', 'Segunda à sábado'),
('João', 'Segunda à sábado'),
('Rhuan', 'Segunda à sábado'),
('Victor', 'Segunda à sábado');

insert into barbeiros_servicos (barbeiro_id, servico_id) values
-- Serviços Fred
(1, 1),(1, 2), (1, 4), (1, 5), (1, 6), (1, 8),
-- Serviços Isabella
(2, 3), (2, 9), (2, 10), (2, 11), (2, 12), (2, 13), (2, 15), (2, 17), (2, 18), (2, 23),
-- Serviços Fernando
(3, 1),(3, 2), (3, 4), (3, 5), (3, 6), (3, 19), (3, 24),
-- Serviços Eduardo
(4, 1),(4, 2), (4, 4), (4, 5), (4, 6), (4, 7), (4, 8), (4, 14), (4,19), (4, 20), (4, 21), (4, 22), (4, 24),
-- Serviços João
(5, 1),(5, 2), (5, 4), (5, 5), (5, 6), (5, 7), (5, 8), (5, 14), (5, 19), (5, 20), (5, 21),(5, 22), (5, 24),
-- Serviços Rhuan
(6, 1),(6, 2), (6, 4), (6, 6), (6, 7), (6, 8), (6, 16), (6,19), (6, 20), (6, 21),(6, 22), (6, 24),
-- Serviços Victor
(7, 1),(7, 2), (7, 4), (7, 6), (7,19), (7, 24);

-- =============================================================
-- MIGRAÇÃO: execute no banco já populado (não rodar no banco novo)
-- =============================================================
ALTER TABLE servicos ADD COLUMN IF NOT EXISTS categoria varchar(20) not null default 'barbearia';

UPDATE servicos SET categoria = 'estetica' WHERE nome_servico IN (
    'Brow Lamination',
    'Dermaplaning',
    'Design Sobrancelha',
    'Design Sobrancelha Henna',
    'Design Sobrancelha Tintura',
    'Extensão de Cílios',
    'Lash Lifting - Cílios',
    'Limpeza de Pele',
    'Limpeza de Pele Profunda',
    'Nanoblading',
    'Sobrancelha na Cera'
);

-- =============================================================
-- MIGRAÇÃO v2 (anti-alucinação + dedupe persistente + reativação automática)
-- Execute uma única vez em banco já populado.
-- MySQL não suporta IF NOT EXISTS em ALTER ADD COLUMN nem em CREATE INDEX.
-- Se rodar 2x → erro 1060 (Duplicate column) / 1061 (Duplicate key) — esperado.
-- =============================================================
ALTER TABLE usuarios ADD COLUMN bot_desativado_em DATETIME NULL;

CREATE INDEX idx_historico_telefone_data
    ON historico_conversas (telefone_usuario, criado_em);

CREATE TABLE IF NOT EXISTS mensagens_processadas (
    message_id VARCHAR(100) PRIMARY KEY,
    processada_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_mensagens_processadas_data (processada_em)
);

-- =============================================================
-- MIGRAÇÃO v3 (modo híbrido bot + atendente humano com dashboard)
-- Execute uma única vez em banco já populado.
-- Se rodar 2x → erro 1060 (Duplicate column) / 1050 (Table exists) — esperado.
-- =============================================================

-- Tabela de atendentes humanos (login no dashboard).
CREATE TABLE IF NOT EXISTS atendentes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    usuario_login VARCHAR(50) NOT NULL UNIQUE,
    senha_hash VARCHAR(255) NOT NULL,
    ativo BOOLEAN DEFAULT TRUE,
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_atendentes_login (usuario_login)
);

-- Colunas novas em usuarios para fluxo de transbordo humano.
ALTER TABLE usuarios ADD COLUMN aguardando_humano BOOLEAN DEFAULT FALSE;
ALTER TABLE usuarios ADD COLUMN transbordo_em DATETIME NULL;
ALTER TABLE usuarios ADD COLUMN atendente_id INT NULL;
ALTER TABLE usuarios
    ADD CONSTRAINT fk_usuarios_atendente
    FOREIGN KEY (atendente_id) REFERENCES atendentes(id) ON DELETE SET NULL;

-- Colunas novas em historico_conversas para diferenciar autoria da resposta.
-- origem: 'bot' (IA), 'humano' (atendente), 'cliente' (mensagem registrada sem resposta).
ALTER TABLE historico_conversas ADD COLUMN origem VARCHAR(10) DEFAULT 'bot';
ALTER TABLE historico_conversas ADD COLUMN atendente_id INT NULL;
ALTER TABLE historico_conversas
    ADD CONSTRAINT fk_historico_atendente
    FOREIGN KEY (atendente_id) REFERENCES atendentes(id) ON DELETE SET NULL;

-- =============================================================
-- MIGRAÇÃO v4 (indicador de entrega Meta API)
-- =============================================================
-- Status de entrega ao WhatsApp:
--   TRUE  = Meta aceitou (200 OK)
--   FALSE = Meta rejeitou (4xx/5xx, token expirado, número inválido, etc)
--   NULL  = não aplicável (linha sem resposta) ou linha antiga pré-migração.
ALTER TABLE historico_conversas ADD COLUMN entregue BOOLEAN NULL;
