-- =============================================================
-- MIGRAÇÃO: Corrigir horário canned response '/horario'
-- A seed inicial da migration 0004 continha horário incorreto.
-- Atualiza para o horário real da Barbearia Bolshoi:
--   Segunda: 14h às 21h
--   Terça a Sexta: 09h às 21h
--   Sábado: 09h às 18h
--   Domingo: fechado
-- Idempotente — roda múltiplas vezes sem erro.
-- =============================================================

UPDATE canned_responses
SET texto = 'Nosso horário de funcionamento:\n\nSegunda: 14h às 21h\nTerça a Sexta: 09h às 21h\nSábado: 09h às 18h\nDomingo: fechado'
WHERE atalho = '/horario'
  AND atendente_id IS NULL;
