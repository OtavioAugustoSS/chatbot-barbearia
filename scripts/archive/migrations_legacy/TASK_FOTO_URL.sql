-- TASK-CLIENT-INFO-PANEL: cache da URL de foto de perfil do WhatsApp.
--
-- A URL retornada pela Meta Cloud API (profile_picture_url) expira em ~1h.
-- Usamos esta coluna como cache curto (TTL recomendado: 30min) para evitar
-- chamar a Meta API a cada abertura de conversa pelo atendente.
--
-- Pode ser NULL em 3 cenários:
--   1) Cliente nunca teve a foto buscada
--   2) Cliente tem privacidade de foto fechada
--   3) Última busca falhou (timeout, 4xx etc) — frontend cai em iniciais
--
-- Idempotente: usa procedure para verificar se a coluna já existe antes do ALTER.

DELIMITER $$

DROP PROCEDURE IF EXISTS add_foto_url_if_missing$$

CREATE PROCEDURE add_foto_url_if_missing()
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'usuarios'
          AND COLUMN_NAME = 'foto_url'
    ) THEN
        ALTER TABLE usuarios
            ADD COLUMN foto_url VARCHAR(500) NULL DEFAULT NULL,
            ADD COLUMN foto_atualizada_em DATETIME NULL DEFAULT NULL;
    END IF;
END$$

DELIMITER ;

CALL add_foto_url_if_missing();
DROP PROCEDURE add_foto_url_if_missing;
