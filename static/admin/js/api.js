// Helper interno (não exposto):
function _authHeaders() {
  return {
    'Authorization': `Bearer ${localStorage.getItem('token')}`,
    'Content-Type': 'application/json'
  };
}

function _logout() {
  localStorage.clear();
  location.href = '/static/admin/login.html';
}

async function _req(url, opts = {}) {
  const res = await fetch(url, {
    ...opts,
    headers: { ..._authHeaders(), ...(opts.headers || {}) }
  });
  if (res.status === 401) { _logout(); return null; }
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`${res.status}: ${txt}`);
  }
  if (res.status === 204) return null;
  const ct = res.headers.get('content-type') || '';
  if (!ct.includes('application/json')) return null;
  return res.json();
}

window.api = {
  login: (usuario_login, senha) =>
    fetch('/admin/login', { method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({usuario_login, senha}) }).then(r => {
        if (!r.ok) return r.json().then(e => Promise.reject(e));
        return r.json();
      }),

  getConversas: (estado, page = 1) => {
    const params = new URLSearchParams({ page });
    if (estado && estado !== 'todas') params.set('estado', estado);
    return _req(`/admin/conversas?${params}`);
  },

  getConversa: (telefone) => _req(`/admin/conversa/${encodeURIComponent(telefone)}`),

  getClienteInfo: (telefone) => _req(`/admin/cliente/${encodeURIComponent(telefone)}/info`),

  assumir: (telefone) => _req(`/admin/assumir/${encodeURIComponent(telefone)}`, { method:'POST' }),

  devolver: (telefone, silent = false) =>
    _req(`/admin/devolver/${encodeURIComponent(telefone)}?silent=${silent}`, { method:'POST' }),

  enviar: (telefone, texto) =>
    _req(`/admin/enviar/${encodeURIComponent(telefone)}`, {
      method: 'POST',
      body: JSON.stringify({ texto })
    }),

  setTag: (telefone, tag) =>
    _req(`/admin/conversa/${encodeURIComponent(telefone)}/tag`, {
      method: 'PATCH',
      body: JSON.stringify({ tag })
    }),

  getNotas: (telefone) => _req(`/admin/notas/${encodeURIComponent(telefone)}`),

  addNota: (telefone, texto) =>
    _req(`/admin/notas/${encodeURIComponent(telefone)}`, {
      method: 'POST',
      body: JSON.stringify({ texto })
    }),

  editNota: (notaId, texto) =>
    _req(`/admin/notas/${notaId}`, {
      method: 'PATCH',
      body: JSON.stringify({ texto })
    }),

  deleteNota: (notaId) =>
    _req(`/admin/notas/${notaId}`, { method: 'DELETE' }),

  getAtendentes: () => _req('/admin/atendentes'),

  criarAtendente: (nome, usuario_login, senha) =>
    _req('/admin/atendentes', {
      method: 'POST',
      body: JSON.stringify({ nome, usuario_login, senha })
    }),

  desativarAtendente: (id) =>
    _req(`/admin/atendentes/${id}/desativar`, { method: 'PATCH' }),

  ativarAtendente: (id) =>
    _req(`/admin/atendentes/${id}/ativar`, { method: 'PATCH' }),

  // ===== Labels =====
  getLabels: (incluirInativas = false) =>
    _req(`/admin/labels?incluir_inativas=${incluirInativas}`),

  criarLabel: (nome, cor, descricao) =>
    _req('/admin/labels', {
      method: 'POST',
      body: JSON.stringify({ nome, cor, descricao: descricao || null })
    }),

  editarLabel: (id, patch) =>
    _req(`/admin/labels/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(patch)
    }),

  deletarLabel: (id) =>
    _req(`/admin/labels/${id}`, { method: 'DELETE' }),

  atribuirLabel: (telefone, label_id) =>
    _req(`/admin/conversa/${encodeURIComponent(telefone)}/labels`, {
      method: 'POST',
      body: JSON.stringify({ label_id })
    }),

  removerLabel: (telefone, label_id) =>
    _req(`/admin/conversa/${encodeURIComponent(telefone)}/labels/${label_id}`, {
      method: 'DELETE'
    }),

  // ===== Status de conversa =====
  setStatusConversa: (telefone, status, snoozed_until = null) =>
    _req(`/admin/conversa/${encodeURIComponent(telefone)}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status, snoozed_until })
    }),

  // getConversas com status filter
  getConversasFiltradas: (estado, status, page = 1) => {
    const params = new URLSearchParams({ page });
    if (estado && estado !== 'todas') params.set('estado', estado);
    if (status) params.set('status', status);
    return _req(`/admin/conversas?${params}`);
  },

  // ===== Canned responses =====
  getCanned: () => _req('/admin/canned'),

  criarCanned: (atalho, texto, escopo = 'pessoal') =>
    _req('/admin/canned', {
      method: 'POST',
      body: JSON.stringify({ atalho, texto, escopo })
    }),

  editarCanned: (id, patch) =>
    _req(`/admin/canned/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(patch)
    }),

  deletarCanned: (id) =>
    _req(`/admin/canned/${id}`, { method: 'DELETE' }),

  // ===== Atribuição entre atendentes =====
  atribuirConversa: (telefone, atendente_id) =>
    _req(`/admin/conversa/${encodeURIComponent(telefone)}/atribuir`, {
      method: 'POST',
      body: JSON.stringify({ atendente_id })
    }),

  // ===== Mentions inbox =====
  getMentionsInbox: () => _req('/admin/mentions/inbox'),
  marcarMentionLida: (id) => _req(`/admin/mentions/${id}/marcar-lida`, { method: 'PATCH' }),

  // ===== Bulk =====
  bulkConversas: (telefones, acao, parametros = {}) =>
    _req('/admin/conversas/bulk', {
      method: 'POST',
      body: JSON.stringify({ telefones, acao, parametros })
    }),

  // ===== Presence =====
  setPresence: (status) =>
    _req('/admin/presence', {
      method: 'POST',
      body: JSON.stringify({ status })
    }),
  getPresence: () => _req('/admin/presence'),

  // ===== Saved Views =====
  getViews: () => _req('/admin/views'),
  criarView: (nome, criterios, ordem = 0) =>
    _req('/admin/views', { method: 'POST', body: JSON.stringify({ nome, criterios, ordem }) }),
  editarView: (id, patch) =>
    _req(`/admin/views/${id}`, { method: 'PATCH', body: JSON.stringify(patch) }),
  deletarView: (id) =>
    _req(`/admin/views/${id}`, { method: 'DELETE' }),

  // ===== Search =====
  searchMensagens: (q, limit = 50) =>
    _req(`/admin/search?q=${encodeURIComponent(q)}&limit=${limit}`),
};
