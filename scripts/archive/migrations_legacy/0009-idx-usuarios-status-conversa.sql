-- TD-011: índice em status_conversa para _auto_unsnooze() eficiente
-- _auto_unsnooze() filtra usuarios.status_conversa = 'snoozed' em toda chamada a
-- GET /admin/conversas. Sem índice, MySQL faz full table scan a cada request do dashboard.
-- IF NOT EXISTS: idempotente para reexecução segura.
CREATE INDEX IF NOT EXISTS idx_usuarios_status ON usuarios(status_conversa);
