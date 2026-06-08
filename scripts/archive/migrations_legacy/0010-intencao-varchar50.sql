-- B3: TD-015 — Ampliar coluna intencao de VARCHAR(30) para VARCHAR(50)
-- Necessário para intencoes mais descritivas (ex: "transbordo_falha", futuras extensões)
ALTER TABLE historico_conversas
    MODIFY COLUMN intencao VARCHAR(50) NULL;
