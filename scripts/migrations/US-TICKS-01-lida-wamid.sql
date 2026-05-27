-- Migration: adicionar wamid e lida ao historico_conversas
ALTER TABLE historico_conversas
  ADD COLUMN wamid VARCHAR(255) DEFAULT NULL COMMENT 'WhatsApp message ID para rastrear status de entrega',
  ADD COLUMN lida BOOLEAN DEFAULT NULL COMMENT 'NULL=desconhecido, FALSE=entregue nao lida, TRUE=lida pelo cliente';

CREATE INDEX idx_historico_wamid ON historico_conversas (wamid);
