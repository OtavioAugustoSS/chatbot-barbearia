// ============================================================
// Auth guard
// ============================================================
if (!localStorage.getItem('token')) {
  location.href = '/static/admin/login.html';
}

// ============================================================
// Estado global
// ============================================================
const state = {
  conversas: [],
  conversaAtual: null,     // telefone da conversa aberta
  usuarioAtual: null,      // objeto {telefone, nome, bot_ativo, aguardando_humano, atendente_id, tag, labels, status_conversa, snoozed_until}
  filtro: 'todas',
  statusFiltro: 'open',    // filtro de status: open (default), pending, resolved, snoozed, todas
  searchQuery: '',
  infoAberto: false,
  muted: localStorage.getItem('atendente_mute') === '1',
  allLabels: [],           // catálogo global de labels disponíveis (carregado no init)
  bulkSelecionadas: new Set(),  // telefones selecionados em modo bulk
  eu: {
    id: parseInt(localStorage.getItem('atendente_id') || '0'),
    nome: localStorage.getItem('atendente_nome') || ''
  }
};

// ============================================================
// Canned responses (carregadas da API; substitui hardcoded antigo)
// ============================================================
let CANNED_RESPONSES = [];  // [{id, atalho, texto, atendente_id}]

async function carregarCanned() {
  try {
    const lista = await api.getCanned();
    CANNED_RESPONSES = lista || [];
  } catch (e) {
    console.warn('carregarCanned (fallback):', e);
    CANNED_RESPONSES = [];
  }
}

// Helper: preview do texto com placeholders substituídos pelos dados do cliente atual
function previewCanned(texto) {
  if (!texto || !state.usuarioAtual) return texto;
  const u = state.usuarioAtual;
  const nomeCliente = (u.nome || '').trim();
  const primeiroNome = nomeCliente.split(' ')[0] || 'cliente';
  return (texto
    .replace(/\{nome_cliente\}/g, nomeCliente || 'cliente')
    .replace(/\{primeiro_nome\}/g, primeiroNome)
    .replace(/\{atendente\}/g, state.eu.nome || '')
    .replace(/\{barbearia\}/g, 'Barbearia Bolshoi'));
}

// ============================================================
// Utilitários de formatação
// ============================================================
function escapeHtml(s) {
  return (s || '').replace(/[&<>"']/g, c =>
    ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])
  );
}

const _CORES = ['#2481cc','#1a6eb0','#6c5ce7','#00b894','#e17055','#d63031','#636e72','#0984e3','#00838f','#8e44ad','#27ae60','#c0392b'];
function _hashStr(s) {
  let h = 0;
  for (const c of (s||'')) h = ((h*31) + c.charCodeAt(0)) >>> 0;
  return h;
}
function corDoCliente(s) { return _CORES[_hashStr(s||'') % _CORES.length]; }

function iniciais(nome, fallback) {
  const fonte = (nome||'').trim() || (fallback||'?');
  const p = fonte.trim().split(/\s+/);
  return ((p[0]||'?')[0] + ((p[1]||'')[0]||'')).toUpperCase();
}

function avatarHTML(nome, tel, cls = 'w-10 h-10 text-sm') {
  const cor = corDoCliente(nome || tel);
  const ini = iniciais(nome, tel);
  return `<div class="${cls} rounded-full flex items-center justify-center font-bold text-white flex-shrink-0 select-none" style="background:${cor}">${escapeHtml(ini)}</div>`;
}

function horarioRelativo(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 45)     return 'agora';
  if (diff < 90)     return '1min';
  if (diff < 3600)   return `${Math.floor(diff/60)}min`;
  if (diff < 7200)   return '1h';
  if (diff < 86400)  return `${Math.floor(diff/3600)}h`;
  if (diff < 172800) return 'ontem';
  if (diff < 604800) return `${Math.floor(diff/86400)}d`;
  return d.toLocaleDateString('pt-BR', {day:'2-digit',month:'2-digit'});
}

function dataLabel(iso) {
  if (!iso) return '';
  const d    = new Date(iso);
  const hoje = new Date().toLocaleDateString('pt-BR');
  const ont  = new Date(Date.now()-86400000).toLocaleDateString('pt-BR');
  const ds   = d.toLocaleDateString('pt-BR');
  if (ds === hoje) return 'Hoje';
  if (ds === ont)  return 'Ontem';
  return d.toLocaleDateString('pt-BR', {weekday:'long', day:'2-digit', month:'long'});
}

function horaCurta(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleTimeString('pt-BR', {hour:'2-digit', minute:'2-digit'});
}

function dataFormatoBR(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return `${String(d.getDate()).padStart(2,'0')}/${String(d.getMonth()+1).padStart(2,'0')}/${d.getFullYear()}`;
  } catch(_) { return '—'; }
}

// ============================================================
// Toast + som
// ============================================================
function showToast(texto, tipo = 'info') {
  const cores = {
    info: '#2481cc',
    success: '#10b981',
    error: '#ef4444',
    warning: '#f59e0b',
    transbordo: '#dc2626'
  };
  const cont = document.getElementById('toast-container');
  if (!cont) return;
  const el = document.createElement('div');
  el.className = 'slide-in text-white px-4 py-2.5 rounded-lg shadow-lg text-sm pointer-events-auto max-w-xs';
  el.style.background = cores[tipo] || cores.info;
  el.textContent = texto;
  cont.appendChild(el);
  setTimeout(() => {
    el.style.transition = 'opacity 0.4s, transform 0.4s';
    el.style.opacity = '0';
    el.style.transform = 'translateX(120%)';
    setTimeout(() => el.remove(), 400);
  }, 4500);
}

function tocarNotificacao() {
  if (state.muted) return;
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    [{f:880,d:0},{f:1175,d:0.09}].forEach(({f,d}) => {
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.type = 'sine'; o.frequency.value = f;
      o.connect(g); g.connect(ctx.destination);
      const t = ctx.currentTime + d;
      g.gain.setValueAtTime(0,t);
      g.gain.linearRampToValueAtTime(0.18, t+0.015);
      g.gain.exponentialRampToValueAtTime(0.001, t+0.30);
      o.start(t); o.stop(t+0.32);
    });
    setTimeout(() => ctx.close(), 800);
  } catch(_) {}
}

// ============================================================
// Tag helpers
// ============================================================
function tagBadgeHTML(tag) {
  if (tag === 'resolvido') return '<span class="text-xs font-bold px-2 py-0.5 rounded-full" style="background:#052e16;color:#10b981;">✓ Resolvido</span>';
  if (tag === 'follow_up') return '<span class="text-xs font-bold px-2 py-0.5 rounded-full" style="background:#451a03;color:#f59e0b;">↩ Follow-up</span>';
  return '';
}

// Renderiza array de labels como chips coloridos.
// labels: [{id, nome, cor}, ...]
function labelChipsHTML(labels) {
  if (!labels || !labels.length) return '';
  return labels.map(l => {
    const cor = l.cor || '#6366f1';
    const bg = cor + '20';  // alpha 12.5%
    return `<span class="text-xs font-medium px-2 py-0.5 rounded-full" style="background:${bg};color:${cor};">${escapeHtml(l.nome)}</span>`;
  }).join(' ');
}

// Chip removível (com X) para o info panel
function labelChipRemovableHTML(label) {
  const cor = label.cor || '#6366f1';
  const bg = cor + '20';
  return `<span class="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full" style="background:${bg};color:${cor};">
    ${escapeHtml(label.nome)}
    <button class="hover:opacity-70 ml-0.5" onclick="removerLabelConversa(${label.id})" title="Remover">×</button>
  </span>`;
}

// ============================================================
// Renderização: lista de conversas
// ============================================================
function renderConvList() {
  const cont = document.getElementById('conv-list');
  if (!cont) return;

  let lista = state.conversas;

  // Filtro por tab
  if (state.filtro === 'aguardando') {
    lista = lista.filter(c => c.aguardando_humano);
  } else if (state.filtro === 'meus') {
    lista = lista.filter(c => c.atendente_id === state.eu.id);
  } else if (state.filtro === 'bot') {
    lista = lista.filter(c => c.bot_ativo && !c.aguardando_humano && !c.atendente_id);
  }

  // Filtro por busca
  if (state.searchQuery) {
    const q = state.searchQuery.toLowerCase();
    lista = lista.filter(c =>
      (c.nome||'').toLowerCase().includes(q) || c.telefone.includes(q)
    );
  }

  if (lista.length === 0) {
    cont.innerHTML = '<div class="flex items-center justify-center h-24 text-sm" style="color:var(--text-muted);">Nenhuma conversa</div>';
    return;
  }

  cont.innerHTML = lista.map(c => {
    const isAtivo = c.telefone === state.conversaAtual;
    const ini = iniciais(c.nome, c.telefone);
    const cor = corDoCliente(c.nome || c.telefone);
    const nome = escapeHtml(c.nome || c.telefone);
    const preview = escapeHtml(c.preview || '');
    const tempo = horarioRelativo(c.ultima_mensagem_em);

    let dotColor = 'var(--text-muted)';
    let pulseClass = '';
    if (c.aguardando_humano) { dotColor = 'var(--danger)'; pulseClass = 'pulse-red'; }
    else if (c.atendente_id === state.eu.id) dotColor = 'var(--accent)';
    else if (c.bot_ativo && !c.atendente_id) dotColor = 'var(--success)';

    const isSelected = state.bulkSelecionadas.has(c.telefone);
    const bulkActive = state.bulkSelecionadas.size > 0;
    return `
      <div class="conv-card${isAtivo ? ' active' : ''}${isSelected ? ' bulk-selected' : ''}" data-tel="${escapeHtml(c.telefone)}">
        <input type="checkbox" class="bulk-check flex-shrink-0 mt-3 ${bulkActive ? '' : 'hidden'}" data-tel="${escapeHtml(c.telefone)}" ${isSelected ? 'checked' : ''} onclick="event.stopPropagation();" style="accent-color: var(--accent);">
        <div class="${pulseClass} w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold text-white flex-shrink-0 select-none" style="background:${cor}" onclick="event.stopPropagation(); toggleBulkSelecao('${escapeHtml(c.telefone)}')" title="Clique para selecionar">${escapeHtml(ini)}</div>
        <div class="flex-1 min-w-0" onclick="abrirConversa('${escapeHtml(c.telefone)}')">
          <div class="flex items-center justify-between gap-1 mb-0.5">
            <span class="font-medium text-sm truncate" style="color:var(--text-primary);">${nome}</span>
            <span class="text-xs flex-shrink-0" style="color:var(--text-muted);">${tempo}</span>
          </div>
          <div class="flex items-center justify-between gap-1">
            <span class="text-xs truncate" style="color:var(--text-secondary);">${preview}</span>
            <span class="w-2 h-2 rounded-full flex-shrink-0" style="background:${dotColor};"></span>
          </div>
          ${(c.labels && c.labels.length) ? `<div class="mt-1 flex flex-wrap gap-1">${labelChipsHTML(c.labels)}</div>` : (c.tag ? `<div class="mt-1">${tagBadgeHTML(c.tag)}</div>` : '')}
        </div>
      </div>
    `;
  }).join('');
}

function atualizarBadges(totais) {
  if (!totais) return;
  const total = (totais.aguardando||0) + (totais.meus||0) + (totais.bot||0) + (totais.outros||0);
  const badgeTotal = document.getElementById('badge-total');
  if (badgeTotal) badgeTotal.textContent = total;

  const badgeAg = document.getElementById('badge-aguardando');
  if (badgeAg) {
    badgeAg.textContent = totais.aguardando || '';
    badgeAg.classList.toggle('hidden', !totais.aguardando);
  }
  const badgeMeus = document.getElementById('badge-meus');
  if (badgeMeus) {
    badgeMeus.textContent = totais.meus || '';
    badgeMeus.classList.toggle('hidden', !totais.meus);
  }
}

// ============================================================
// Carregar conversas
// ============================================================
async function carregarConversas() {
  try {
    const data = await api.getConversasFiltradas(state.filtro, state.statusFiltro);
    if (!data) return;
    state.conversas = data.items || [];
    atualizarBadges(data.totais_por_estado);
    renderConvList();
  } catch(e) { console.error('carregarConversas:', e); }
}

// ============================================================
// Bolhas de mensagem
// ============================================================
function separadorData(label) {
  const el = document.createElement('div');
  el.className = 'flex items-center gap-3 my-4';
  el.innerHTML = `
    <div class="flex-1 h-px" style="background:var(--border);"></div>
    <span class="text-xs px-3 py-1 rounded-full flex-shrink-0" style="background:var(--bg-card);color:var(--text-secondary);">${escapeHtml(label)}</span>
    <div class="flex-1 h-px" style="background:var(--border);"></div>
  `;
  return el;
}

function separadorEvento(label) {
  const el = document.createElement('div');
  el.className = 'flex items-center gap-3 my-2';
  el.innerHTML = `
    <div class="flex-1 h-px" style="background:var(--border);"></div>
    <span class="text-xs italic" style="color:var(--text-muted);">${escapeHtml(label)}</span>
    <div class="flex-1 h-px" style="background:var(--border);"></div>
  `;
  return el;
}

function bolha(texto, origem, criado_em, opts = {}) {
  const row = document.createElement('div');
  const isCliente = origem === 'cliente';
  const isHumano  = origem === 'humano';

  row.className = `flex mb-1 ${isCliente ? 'justify-start' : 'justify-end'} fade-in`;

  let cls = isCliente ? 'bolha-incoming' : (isHumano ? 'bolha-outgoing-humano' : 'bolha-outgoing-bot');
  if (opts.falha) cls += ' bolha-falha';

  let labelTxt = '';
  if (isCliente) labelTxt = 'Cliente';
  else if (isHumano) labelTxt = opts.atendente_nome ? `Atendente · ${escapeHtml(opts.atendente_nome)}` : 'Atendente';
  else labelTxt = '<span class="px-1 rounded text-xs font-bold" style="background:#04473b;color:#86efac;">IA</span> Bot';

  const entregueIcon = opts.entregue === false ? ' ⚠' : (opts.entregue === true ? ' ✓' : '');
  const textoEscapado = escapeHtml(texto).replace(/\n/g, '<br>');

  row.innerHTML = `
    <div class="${cls}" ${opts.tempId ? `data-temp-id="${opts.tempId}"` : ''}>
      <span class="bolha-label">${labelTxt}</span>
      <p style="white-space:pre-wrap;word-break:break-word;">${textoEscapado}</p>
      <div class="flex items-center justify-end gap-1 mt-1">
        <span class="text-xs" style="color:var(--text-secondary);opacity:0.7;">${horaCurta(criado_em)}</span>
        ${!isCliente ? `<span class="entregue-status text-xs" style="color:var(--text-secondary);opacity:0.7;">${entregueIcon}</span>` : ''}
      </div>
    </div>
  `;
  return row;
}

// ============================================================
// Renderização: thread de mensagens
// ============================================================
function renderMensagens(mensagens) {
  const cont = document.getElementById('messages-area');
  if (!cont) return;
  cont.innerHTML = '';

  if (mensagens.length === 0) {
    const el = document.createElement('div');
    el.className = 'flex items-center justify-center h-full text-sm';
    el.style.color = 'var(--text-muted)';
    el.textContent = 'Nenhuma mensagem ainda';
    cont.appendChild(el);
    return;
  }

  let ultimoDia = null;
  let ultimaOrigem = null;

  for (const m of mensagens) {
    const labelDia = dataLabel(m.criado_em);
    if (labelDia && labelDia !== ultimoDia) {
      ultimoDia = labelDia;
      cont.appendChild(separadorData(labelDia));
    }

    if (m.cliente) {
      cont.appendChild(bolha(m.cliente, 'cliente', m.criado_em));
      ultimaOrigem = 'cliente';
    }

    if (m.resposta) {
      const origem = m.origem || 'bot';
      if (ultimaOrigem !== null) {
        if (origem === 'humano' && ultimaOrigem !== 'humano') {
          cont.appendChild(separadorEvento('Atendente assumiu'));
        } else if (origem !== 'humano' && ultimaOrigem === 'humano') {
          cont.appendChild(separadorEvento('Bot retomou'));
        }
      }
      const textoProcessado = (m.resposta || '').replace(/<\s*br\s*\/?>/gi, '\n');
      cont.appendChild(bolha(textoProcessado, origem, m.criado_em, { entregue: m.entregue }));
      ultimaOrigem = origem;
    }
  }

  scrollarFim();
}

function scrollarFim(force = true) {
  const cont = document.getElementById('messages-area');
  if (!cont) return;
  const noFundo = cont.scrollHeight - cont.scrollTop - cont.clientHeight < 80;
  if (force || noFundo) cont.scrollTop = cont.scrollHeight;
}

// ============================================================
// Append incremental (SSE)
// ============================================================
let _ultimaOrigemIncremental = null;

function appendMensagemIncremental(texto, origem, entregue, tempId = null) {
  const cont = document.getElementById('messages-area');
  if (!cont) return;

  const agora = new Date().toISOString();
  const labelDia = dataLabel(agora);

  // Verifica se precisa separador de data
  const ultimoSep = cont.querySelector('.separador-data:last-child');
  if (!ultimoSep || ultimoSep.getAttribute('data-label') !== labelDia) {
    const sep = separadorData(labelDia);
    sep.classList.add('separador-data');
    sep.setAttribute('data-label', labelDia);
    cont.appendChild(sep);
  }

  // Separador de evento se origem mudou
  if (_ultimaOrigemIncremental !== null) {
    if (origem === 'humano' && _ultimaOrigemIncremental !== 'humano') {
      cont.appendChild(separadorEvento('Atendente assumiu'));
    } else if (origem !== 'humano' && _ultimaOrigemIncremental === 'humano') {
      cont.appendChild(separadorEvento('Bot retomou'));
    }
  }
  _ultimaOrigemIncremental = origem;

  const textoProcessado = (texto || '').replace(/<\s*br\s*\/?>/gi, '\n');
  cont.appendChild(bolha(textoProcessado, origem, agora, { entregue, tempId }));
  scrollarFim();
}

function resolverBolhaPendente(tempId, ok) {
  const el = document.querySelector(`[data-temp-id="${tempId}"]`);
  if (!el) return;
  if (!ok) {
    el.classList.add('bolha-falha');
  }
  // Atualiza ícone de entrega
  const statusSpan = el.querySelector('.entregue-status');
  if (statusSpan) statusSpan.textContent = ok ? ' ✓' : ' ⚠';
}

// ============================================================
// Abrir conversa
// ============================================================
async function abrirConversa(telefone) {
  state.conversaAtual = telefone;
  _ultimaOrigemIncremental = null;

  // Remove active de todos os cards
  document.querySelectorAll('.conv-card').forEach(c => c.classList.remove('active'));
  const card = document.querySelector(`.conv-card[data-tel="${CSS.escape(telefone)}"]`);
  if (card) card.classList.add('active');

  // Fecha info panel ao trocar de conversa
  fecharInfoPanel();

  // Mostra skeleton loading
  document.getElementById('empty-state')?.classList.add('hidden');
  document.getElementById('thread-header')?.classList.remove('hidden');
  document.getElementById('messages-area')?.classList.remove('hidden');
  document.getElementById('composer')?.classList.remove('hidden');

  try {
    const data = await api.getConversa(telefone);
    if (!data) return;
    state.usuarioAtual = data.usuario;
    atualizarHeaderThread(data.usuario);
    renderMensagens(data.mensagens);
    syncComposerState(data.usuario);
  } catch(e) {
    console.error('abrirConversa:', e);
    showToast('Erro ao carregar conversa', 'error');
  }

  // Carrega info e notas em paralelo (não bloqueia)
  carregarInfoCliente(telefone);
  carregarNotas(telefone);
}

// ============================================================
// Header da thread
// ============================================================
function atualizarHeaderThread(u) {
  document.getElementById('thread-avatar').innerHTML = avatarHTML(u.nome, u.telefone, 'w-10 h-10 text-sm');
  document.getElementById('thread-nome').textContent = u.nome || u.telefone;
  document.getElementById('thread-telefone').textContent = u.telefone;
  const tagBadgeEl = document.getElementById('thread-tag-badge');
  if (tagBadgeEl) {
    if (u.tag) {
      tagBadgeEl.innerHTML = tagBadgeHTML(u.tag);
      tagBadgeEl.classList.remove('hidden');
    } else {
      tagBadgeEl.classList.add('hidden');
    }
  }
  atualizarStatusBadgeHeader();
}

// ============================================================
// syncComposerState — estado dos botões e composer
// ============================================================
function syncComposerState(u) {
  if (!u) u = state.usuarioAtual;
  if (!u) return;

  const btnAssumir    = document.getElementById('btn-assumir');
  const btnInterromper = document.getElementById('btn-interromper');
  const btnDevolver   = document.getElementById('btn-devolver');
  const btnTransferir = document.getElementById('btn-transferir');
  const threadStatus  = document.getElementById('thread-status');
  const banner        = document.getElementById('composer-banner');
  const msgInput      = document.getElementById('msg-input');
  const sendBtn       = document.getElementById('send-btn');

  // Reset
  [btnAssumir, btnInterromper, btnDevolver, btnTransferir].forEach(b => b?.classList.add('hidden'));
  if (banner) banner.classList.add('hidden');

  const meuAtendimento = u.atendente_id === state.eu.id;
  const outroAtendente = u.atendente_id && u.atendente_id !== state.eu.id;

  if (meuAtendimento) {
    // É minha conversa
    if (threadStatus) threadStatus.textContent = 'Você está atendendo';
    btnDevolver?.classList.remove('hidden');
    btnTransferir?.classList.remove('hidden');
    if (msgInput) { msgInput.disabled = false; msgInput.focus(); }
    if (sendBtn) sendBtn.disabled = false;
  } else if (outroAtendente) {
    // Outro atendente
    if (threadStatus) threadStatus.textContent = 'Outro atendente';
    if (banner) {
      banner.textContent = 'Esta conversa está sendo atendida por outro operador.';
      banner.classList.remove('hidden');
    }
    if (msgInput) msgInput.disabled = true;
    if (sendBtn) sendBtn.disabled = true;
  } else if (u.aguardando_humano) {
    // Aguardando humano
    if (threadStatus) threadStatus.textContent = 'Aguardando atendimento';
    btnAssumir?.classList.remove('hidden');
    if (banner) {
      banner.textContent = 'Cliente aguardando atendimento humano. Clique em "Assumir" para responder.';
      banner.classList.remove('hidden');
    }
    if (msgInput) msgInput.disabled = true;
    if (sendBtn) sendBtn.disabled = true;
  } else if (u.bot_ativo) {
    // Bot ativo
    if (threadStatus) threadStatus.textContent = 'Bot ativo';
    btnInterromper?.classList.remove('hidden');
    if (banner) {
      banner.textContent = 'O bot está respondendo. Clique em "Interromper bot" para assumir.';
      banner.classList.remove('hidden');
    }
    if (msgInput) msgInput.disabled = true;
    if (sendBtn) sendBtn.disabled = true;
  } else {
    // Bot inativo, sem atendente
    if (threadStatus) threadStatus.textContent = 'Bot inativo';
    btnAssumir?.classList.remove('hidden');
    if (msgInput) msgInput.disabled = true;
    if (sendBtn) sendBtn.disabled = true;
  }
}

// ============================================================
// Handoff actions
// ============================================================
async function assumirConversa(telefone) {
  try {
    await api.assumir(telefone);
    showToast('Você assumiu o atendimento', 'success');
    const data = await api.getConversa(telefone);
    if (data) {
      state.usuarioAtual = data.usuario;
      atualizarHeaderThread(data.usuario);
      syncComposerState(data.usuario);
    }
    carregarConversas();
  } catch(e) {
    const msg = e.message || String(e);
    showToast(msg.includes('409') ? 'Outro atendente assumiu primeiro' : 'Erro ao assumir', 'error');
  }
}

async function devolverAoBot(telefone) {
  if (!confirm('Devolver conversa ao bot?')) return;
  try {
    await api.devolver(telefone);
    showToast('Conversa devolvida ao bot', 'success');
    const data = await api.getConversa(telefone);
    if (data) {
      state.usuarioAtual = data.usuario;
      atualizarHeaderThread(data.usuario);
      syncComposerState(data.usuario);
    }
    carregarConversas();
  } catch(e) {
    showToast('Erro ao devolver ao bot', 'error');
  }
}

// ============================================================
// Enviar mensagem (optimistic UI)
// ============================================================
async function enviarMensagem() {
  const input = document.getElementById('msg-input');
  const texto = input?.value.trim();
  if (!texto || !state.conversaAtual) return;

  const tempId = `tmp-${Date.now()}`;
  input.value = '';
  input.style.height = 'auto';

  // Bolha pendente (sem entregue confirmado)
  appendMensagemIncremental(texto, 'humano', null, tempId);

  try {
    await api.enviar(state.conversaAtual, texto);
    resolverBolhaPendente(tempId, true);
    carregarConversas();
  } catch(e) {
    resolverBolhaPendente(tempId, false);
    showToast('Falha ao enviar mensagem', 'error');
  }
}

// ============================================================
// Info panel
// ============================================================
async function carregarInfoCliente(telefone) {
  try {
    const info = await api.getClienteInfo(telefone);
    if (!info) return;
    renderInfoPanel(info);
  } catch(e) { console.error('carregarInfoCliente:', e); }
}

function renderInfoPanel(info) {
  const ini = iniciais(info.nome_cliente, info.telefone);
  const cor = corDoCliente(info.nome_cliente || info.telefone);

  const avatarEl = document.getElementById('info-avatar');
  if (avatarEl) { avatarEl.textContent = ini; avatarEl.style.background = cor; }

  const nomeEl = document.getElementById('info-nome');
  if (nomeEl) nomeEl.textContent = info.nome_cliente || info.telefone;

  const telEl = document.getElementById('info-telefone');
  if (telEl) telEl.textContent = info.telefone;

  const criadoEl = document.getElementById('info-criado-em');
  if (criadoEl) criadoEl.textContent = dataFormatoBR(info.criado_em);

  const ultimaEl = document.getElementById('info-ultima');
  if (ultimaEl) ultimaEl.textContent = horarioRelativo(info.data_ultima_interacao) || '—';

  const msgsEl = document.getElementById('info-total-msgs');
  if (msgsEl) msgsEl.textContent = info.total_mensagens ?? '—';

  const humEl = document.getElementById('info-atend-humanos');
  if (humEl) humEl.textContent = info.total_atendimentos_humanos ?? '—';

  const statusEl = document.getElementById('info-status-badges');
  if (statusEl) {
    const badges = [];
    if (info.bot_ativo) badges.push('<span class="text-xs px-2 py-1 rounded-full font-medium" style="background:#052e16;color:#10b981;">Bot ativo</span>');
    else badges.push('<span class="text-xs px-2 py-1 rounded-full font-medium" style="background:#1a1a2e;color:#8b90a0;">Bot inativo</span>');
    if (info.aguardando_humano) badges.push('<span class="text-xs px-2 py-1 rounded-full font-medium" style="background:#450a0a;color:#ef4444;">Aguardando atendente</span>');
    statusEl.innerHTML = badges.join('');
  }

  renderInfoLabels();
}

// ============================================================
// Labels: gerenciamento na info panel
// ============================================================
async function carregarLabelsGlobais() {
  try {
    const labels = await api.getLabels();
    state.allLabels = labels || [];
  } catch (e) {
    console.error('carregarLabelsGlobais:', e);
  }
}

function renderInfoLabels() {
  const cont = document.getElementById('info-labels');
  if (!cont) return;
  const labels = (state.usuarioAtual && state.usuarioAtual.labels) || [];
  if (!labels.length) {
    cont.innerHTML = '<span class="text-xs italic" style="color: var(--text-muted);">Nenhuma etiqueta</span>';
    return;
  }
  cont.innerHTML = labels.map(l => labelChipRemovableHTML(l)).join(' ');
}

async function removerLabelConversa(labelId) {
  if (!state.conversaAtual || !state.usuarioAtual) return;
  try {
    await api.removerLabel(state.conversaAtual, labelId);
    state.usuarioAtual.labels = (state.usuarioAtual.labels || []).filter(l => l.id !== labelId);
    renderInfoLabels();
    // Atualiza conversa na lista também
    const conv = state.conversas.find(c => c.telefone === state.conversaAtual);
    if (conv) {
      conv.labels = (conv.labels || []).filter(l => l.id !== labelId);
      renderConvList();
    }
  } catch (e) {
    console.error('removerLabelConversa:', e);
    showToast('Erro ao remover etiqueta', 'error');
  }
}

function togglePickerLabels() {
  const picker = document.getElementById('label-picker');
  if (!picker) return;
  const isHidden = picker.classList.contains('hidden');
  if (isHidden) {
    picker.classList.remove('hidden');
    renderLabelPicker('');
    setTimeout(() => document.getElementById('label-search')?.focus(), 50);
  } else {
    picker.classList.add('hidden');
  }
}

function renderLabelPicker(query) {
  const lista = document.getElementById('label-picker-list');
  if (!lista) return;
  const q = (query || '').toLowerCase().trim();
  const assigned = new Set(((state.usuarioAtual && state.usuarioAtual.labels) || []).map(l => l.id));
  const disponiveis = state.allLabels.filter(l => !assigned.has(l.id));
  const filtradas = q
    ? disponiveis.filter(l => l.nome.toLowerCase().includes(q))
    : disponiveis;

  let html = '';
  if (filtradas.length) {
    html += filtradas.map(l => `
      <button class="w-full flex items-center gap-2 px-2 py-1.5 rounded text-xs hover:bg-opacity-50 transition-colors text-left"
              style="color: var(--text-primary);"
              onmouseover="this.style.background='var(--bg-base)'" onmouseout="this.style.background=''"
              onclick="aplicarLabel(${l.id})">
        <span class="w-3 h-3 rounded-full flex-shrink-0" style="background:${l.cor};"></span>
        <span class="flex-1">${escapeHtml(l.nome)}</span>
      </button>
    `).join('');
  }
  // Permite criar nova label se query não corresponde exatamente a nenhuma existente
  if (q && !state.allLabels.some(l => l.nome.toLowerCase() === q)) {
    if (/^[a-z0-9_\-]+$/.test(q)) {
      html += `
        <button class="w-full flex items-center gap-2 px-2 py-1.5 rounded text-xs mt-1 transition-colors text-left"
                style="color: var(--accent); background: rgba(99, 102, 241, 0.1);"
                onclick="criarEAplicarLabel('${escapeHtml(q)}')">
          + Criar etiqueta "${escapeHtml(q)}"
        </button>
      `;
    }
  }
  if (!html) {
    html = '<div class="text-xs italic px-2 py-2" style="color: var(--text-muted);">Sem etiquetas disponíveis</div>';
  }
  lista.innerHTML = html;
}

async function aplicarLabel(labelId) {
  if (!state.conversaAtual) return;
  try {
    const res = await api.atribuirLabel(state.conversaAtual, labelId);
    const label = state.allLabels.find(l => l.id === labelId);
    if (label) {
      const labelObj = { id: label.id, nome: label.nome, cor: label.cor };
      state.usuarioAtual.labels = state.usuarioAtual.labels || [];
      if (!state.usuarioAtual.labels.some(l => l.id === labelId)) {
        state.usuarioAtual.labels.push(labelObj);
      }
      const conv = state.conversas.find(c => c.telefone === state.conversaAtual);
      if (conv) {
        conv.labels = conv.labels || [];
        if (!conv.labels.some(l => l.id === labelId)) {
          conv.labels.push(labelObj);
        }
      }
      renderInfoLabels();
      renderConvList();
    }
    document.getElementById('label-picker')?.classList.add('hidden');
    document.getElementById('label-search').value = '';
  } catch (e) {
    console.error('aplicarLabel:', e);
    showToast('Erro ao adicionar etiqueta', 'error');
  }
}

async function criarEAplicarLabel(nome) {
  const cores = ['#6366f1','#10b981','#f59e0b','#ef4444','#a855f7','#3b82f6','#ec4899','#14b8a6'];
  const cor = cores[Math.floor(Math.random() * cores.length)];
  try {
    const nova = await api.criarLabel(nome, cor);
    if (nova && nova.id) {
      state.allLabels.push({ id: nova.id, nome: nova.nome, cor: nova.cor, descricao: nova.descricao, ativo: true });
      await aplicarLabel(nova.id);
    }
  } catch (e) {
    console.error('criarEAplicarLabel:', e);
    showToast('Erro ao criar etiqueta', 'error');
  }
}

// ============================================================
// Status de conversa
// ============================================================
function statusLabel(status) {
  return ({ open: 'Aberta', pending: 'Pendente', resolved: 'Resolvida', snoozed: 'Adiada' })[status] || status;
}
function statusColor(status) {
  return ({ open: 'var(--accent)', pending: 'var(--warning)', resolved: 'var(--success)', snoozed: 'var(--text-muted)' })[status] || 'var(--text-secondary)';
}

async function alterarStatus(novoStatus) {
  if (!state.conversaAtual) return;

  let snoozedUntil = null;
  if (novoStatus === 'snoozed') {
    // Prompt simples para datetime. Pode ser substituído por modal/datepicker depois.
    const horas = prompt('Adiar conversa por quantas horas?', '24');
    const h = parseInt(horas);
    if (isNaN(h) || h <= 0 || h > 720) {
      showToast('Horas inválidas (1-720)', 'error');
      return;
    }
    snoozedUntil = new Date(Date.now() + h * 3600 * 1000).toISOString();
  }
  if (novoStatus === 'resolved') {
    if (!confirm('Marcar conversa como resolvida? Ela sairá da lista padrão.')) return;
  }

  try {
    await api.setStatusConversa(state.conversaAtual, novoStatus, snoozedUntil);

    if (state.usuarioAtual) {
      state.usuarioAtual.status_conversa = novoStatus;
      state.usuarioAtual.snoozed_until = snoozedUntil;
      atualizarStatusBadgeHeader();
    }

    // Se status mudou para algo que não corresponde ao filtro atual, remove da lista
    if (state.statusFiltro !== 'todas' && state.statusFiltro !== novoStatus) {
      state.conversas = state.conversas.filter(c => c.telefone !== state.conversaAtual);
      renderConvList();
    } else {
      // Apenas atualiza o card
      const conv = state.conversas.find(c => c.telefone === state.conversaAtual);
      if (conv) {
        conv.status_conversa = novoStatus;
        conv.snoozed_until = snoozedUntil;
        renderConvList();
      }
    }

    showToast(`Status alterado para ${statusLabel(novoStatus)}`, 'success');
  } catch (e) {
    console.error('alterarStatus:', e);
    showToast('Erro ao alterar status', 'error');
  }
}

function atualizarStatusBadgeHeader() {
  const lbl = document.getElementById('btn-status-label');
  if (!lbl) return;
  const s = state.usuarioAtual?.status_conversa || 'open';
  lbl.textContent = statusLabel(s);
  const btn = document.getElementById('btn-status');
  if (btn) {
    btn.style.color = statusColor(s);
  }
}

// ============================================================
// Transferência entre atendentes
// ============================================================
state.allAtendentes = [];   // cache de atendentes ativos (carregado on-demand)

async function carregarAtendentesParaTransfer() {
  try {
    const lista = await api.getAtendentes();
    state.allAtendentes = (lista || []).filter(a => a.ativo);
  } catch (e) {
    console.error('carregarAtendentesParaTransfer:', e);
  }
}

async function abrirPopoverTransferir() {
  if (!state.allAtendentes.length) await carregarAtendentesParaTransfer();
  const pop = document.getElementById('transferir-popover');
  if (!pop) return;
  const disponiveis = state.allAtendentes.filter(a => a.id !== state.eu.id);
  if (!disponiveis.length) {
    pop.innerHTML = '<div class="px-4 py-2 text-xs italic" style="color: var(--text-muted);">Nenhum outro atendente ativo</div>';
  } else {
    pop.innerHTML = disponiveis.map(a => {
      const ini = (a.nome || '?')[0].toUpperCase();
      const presence = state.presence[String(a.id)];
      const presenceStatus = presence?.status || 'offline';
      const presenceDot = `<span class="w-2 h-2 rounded-full absolute bottom-0 right-0 border" style="background:${presenceCor(presenceStatus)}; border-color: var(--bg-card);"></span>`;
      return `
        <button class="transferir-opt w-full px-4 py-2 text-left text-sm hover:bg-white/5 transition-colors flex items-center gap-2" data-atendente-id="${a.id}" style="color:var(--text-primary);">
          <span class="relative w-6 h-6 flex-shrink-0">
            <span class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white" style="background:var(--accent);">${escapeHtml(ini)}</span>
            ${presenceDot}
          </span>
          <span class="flex-1">${escapeHtml(a.nome)}</span>
          <span class="text-xs" style="color: var(--text-muted);">${presenceStatus === 'online' ? 'Online' : presenceStatus === 'away' ? 'Ausente' : 'Offline'}</span>
        </button>
      `;
    }).join('');
    pop.querySelectorAll('.transferir-opt').forEach(b => {
      b.addEventListener('click', () => {
        const aid = parseInt(b.dataset.atendenteId);
        document.getElementById('transferir-popover')?.classList.add('hidden');
        transferirConversa(aid);
      });
    });
  }
  pop.classList.remove('hidden');
}

async function transferirConversa(atendenteId) {
  if (!state.conversaAtual) return;
  const dest = state.allAtendentes.find(a => a.id === atendenteId);
  if (!dest) return;
  if (!confirm(`Transferir conversa para ${dest.nome}?`)) return;
  try {
    await api.atribuirConversa(state.conversaAtual, atendenteId);
    showToast(`Conversa transferida para ${dest.nome}`, 'success');
    // A conversa some da minha lista — recarregar
    carregarConversas();
  } catch (e) {
    console.error('transferirConversa:', e);
    showToast('Erro ao transferir conversa', 'error');
  }
}

// ============================================================
// MENTIONS: inbox + autocomplete @ em notas
// ============================================================
state.mentions = { items: [], unread: 0 };

async function carregarMentions() {
  try {
    const items = await api.getMentionsInbox();
    state.mentions.items = items || [];
    state.mentions.unread = state.mentions.items.filter(m => !m.lida).length;
    atualizarBadgeMentions();
  } catch (e) {
    console.error('carregarMentions:', e);
  }
}

function atualizarBadgeMentions() {
  const badge = document.getElementById('mentions-badge');
  if (!badge) return;
  const n = state.mentions.unread;
  if (n > 0) {
    badge.textContent = n > 99 ? '99+' : String(n);
    badge.classList.remove('hidden');
  } else {
    badge.classList.add('hidden');
  }
}

function renderMentionsList() {
  const cont = document.getElementById('mentions-list');
  if (!cont) return;
  const items = state.mentions.items;
  if (!items.length) {
    cont.innerHTML = '<div class="px-3 py-6 text-xs italic text-center" style="color: var(--text-muted);">Nenhuma menção</div>';
    return;
  }
  cont.innerHTML = items.map(m => {
    const lidaStyle = m.lida ? 'opacity: 0.5;' : '';
    const dot = m.lida ? '' : `<span class="w-2 h-2 rounded-full flex-shrink-0 mt-1.5" style="background: var(--accent);"></span>`;
    return `
      <button class="mention-item w-full px-3 py-2 text-left transition-colors hover:bg-white/5 flex items-start gap-2 border-b" data-id="${m.id}" data-telefone="${escapeHtml(m.telefone)}" style="border-color: var(--border); ${lidaStyle}">
        ${dot || '<span class="w-2"></span>'}
        <div class="flex-1 min-w-0">
          <div class="flex items-center justify-between mb-0.5">
            <span class="text-xs font-medium" style="color: var(--text-primary);">${escapeHtml(m.mencionado_por_nome)} → ${escapeHtml(m.nome_cliente)}</span>
            <span class="text-xs flex-shrink-0" style="color: var(--text-muted);">${horarioRelativo(m.criado_em)}</span>
          </div>
          <p class="text-xs truncate" style="color: var(--text-secondary);">${escapeHtml(m.nota_texto)}</p>
        </div>
      </button>
    `;
  }).join('');

  cont.querySelectorAll('.mention-item').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = parseInt(btn.dataset.id);
      const tel = btn.dataset.telefone;
      // Marca como lida
      try {
        await api.marcarMentionLida(id);
        const item = state.mentions.items.find(m => m.id === id);
        if (item) {
          item.lida = true;
          state.mentions.unread = state.mentions.items.filter(m => !m.lida).length;
          atualizarBadgeMentions();
        }
      } catch(e) { console.error('marcar lida:', e); }
      // Fecha popover e abre conversa
      document.getElementById('mentions-popover')?.classList.add('hidden');
      abrirConversa(tel);
    });
  });
}

// ============================================================
// Autocomplete @ no textarea de notas
// ============================================================
function posicionarAutocomplete(textarea, popover) {
  const r = textarea.getBoundingClientRect();
  popover.style.top = (r.top - popover.offsetHeight - 4) + 'px';
  popover.style.left = r.left + 'px';
  popover.style.width = r.width + 'px';
}

// ============================================================
// BULK ACTIONS — seleção múltipla
// ============================================================
function toggleBulkSelecao(telefone) {
  if (state.bulkSelecionadas.has(telefone)) {
    state.bulkSelecionadas.delete(telefone);
  } else {
    state.bulkSelecionadas.add(telefone);
  }
  atualizarBulkBar();
  renderConvList();
}

function atualizarBulkBar() {
  const bar = document.getElementById('bulk-bar');
  const count = document.getElementById('bulk-count');
  if (!bar || !count) return;
  const n = state.bulkSelecionadas.size;
  if (n > 0) {
    bar.classList.remove('hidden');
    count.textContent = `${n} selecionada${n > 1 ? 's' : ''}`;
  } else {
    bar.classList.add('hidden');
  }
}

function limparBulkSelecao() {
  state.bulkSelecionadas.clear();
  atualizarBulkBar();
  renderConvList();
}

async function bulkResolver() {
  const telefones = Array.from(state.bulkSelecionadas);
  if (!telefones.length) return;
  if (!confirm(`Marcar ${telefones.length} conversa(s) como resolvidas?`)) return;
  try {
    const res = await api.bulkConversas(telefones, 'resolver');
    showToast(`${res.sucesso.length} conversa(s) resolvida(s)${res.falha.length ? ` (${res.falha.length} falharam)` : ''}`, 'success');
    limparBulkSelecao();
    carregarConversas();
  } catch (e) {
    console.error('bulkResolver:', e);
    showToast('Erro ao processar bulk', 'error');
  }
}

// ============================================================
// PRESENCE — online/away/offline
// ============================================================
state.presence = {};  // {atendente_id: {status, last_seen}}

function presenceCor(status) {
  return ({ online: '#10b981', away: '#f59e0b', offline: '#6b7280' })[status] || '#6b7280';
}

async function enviarPresence(status) {
  try { await api.setPresence(status); } catch (e) { console.warn('presence:', e); }
}

async function carregarPresence() {
  try {
    const data = await api.getPresence();
    state.presence = data || {};
  } catch (e) { console.warn('carregarPresence:', e); }
}

// ============================================================
// SAVED VIEWS
// ============================================================
state.views = [];

async function carregarViews() {
  try {
    const lista = await api.getViews();
    state.views = lista || [];
    renderViews();
  } catch (e) { console.error('carregarViews:', e); }
}

function renderViews() {
  const cont = document.getElementById('views-list');
  const row = document.getElementById('views-row');
  if (!cont || !row) return;
  if (!state.views.length) {
    row.style.display = 'none';
    return;
  }
  row.style.display = 'flex';
  cont.innerHTML = state.views.map(v => `
    <button class="view-chip flex-shrink-0 px-2 py-0.5 rounded transition-colors hover:bg-white/5 flex items-center gap-1" data-view-id="${v.id}" style="color: var(--text-secondary);">
      ${escapeHtml(v.nome)}
      <span class="text-xs opacity-50 hover:opacity-100 ml-1" onclick="event.stopPropagation(); deletarView(${v.id})" title="Excluir view">×</span>
    </button>
  `).join('');
  cont.querySelectorAll('.view-chip').forEach(b => {
    b.addEventListener('click', () => aplicarView(parseInt(b.dataset.viewId)));
  });
}

function aplicarView(viewId) {
  const v = state.views.find(x => x.id === viewId);
  if (!v) return;
  const c = v.criterios || {};
  if (c.filtro) state.filtro = c.filtro;
  if (c.statusFiltro) state.statusFiltro = c.statusFiltro;
  // Sync filter-tabs UI
  document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active-tab'));
  document.querySelector(`.filter-tab[data-filter="${state.filtro}"]`)?.classList.add('active-tab');
  document.querySelectorAll('.status-filter').forEach(b => {
    if (b.dataset.status === state.statusFiltro) {
      b.classList.add('active-status');
      b.style.color = 'var(--accent)';
      b.style.background = 'rgba(99, 102, 241, 0.15)';
    } else {
      b.classList.remove('active-status');
      b.style.color = 'var(--text-secondary)';
      b.style.background = '';
    }
  });
  carregarConversas();
  showToast(`View "${v.nome}" aplicada`, 'info');
}

async function salvarViewAtual() {
  const nome = prompt('Nome da view (ex.: "VIPs ativos"):');
  if (!nome || nome.trim().length < 1) return;
  try {
    const criterios = { filtro: state.filtro, statusFiltro: state.statusFiltro };
    const nova = await api.criarView(nome.trim(), criterios, state.views.length);
    state.views.push(nova);
    renderViews();
    showToast(`View "${nome}" salva`, 'success');
  } catch (e) {
    console.error('salvarViewAtual:', e);
    showToast(e.message?.includes('409') ? 'Nome já existe' : 'Erro ao salvar view', 'error');
  }
}

async function deletarView(viewId) {
  const v = state.views.find(x => x.id === viewId);
  if (!v) return;
  if (!confirm(`Excluir view "${v.nome}"?`)) return;
  try {
    await api.deletarView(viewId);
    state.views = state.views.filter(x => x.id !== viewId);
    renderViews();
    showToast('View excluída', 'success');
  } catch (e) {
    console.error('deletarView:', e);
    showToast('Erro ao excluir view', 'error');
  }
}

// ============================================================
// SEARCH GLOBAL — modo "Por mensagem"
// ============================================================
state.searchMode = 'contato';  // 'contato' | 'mensagem'
state.searchResults = [];

async function executarSearchMensagem(q) {
  if (!q || q.length < 2) {
    state.searchResults = [];
    renderConvList();
    return;
  }
  try {
    const res = await api.searchMensagens(q);
    state.searchResults = res || [];
    renderSearchResults();
  } catch (e) {
    console.error('searchMensagens:', e);
    showToast('Erro na busca', 'error');
  }
}

function renderSearchResults() {
  const cont = document.getElementById('conv-list');
  if (!cont) return;
  if (!state.searchResults.length) {
    cont.innerHTML = '<div class="px-4 py-8 text-xs italic text-center" style="color: var(--text-muted);">Nenhum resultado</div>';
    return;
  }
  cont.innerHTML = state.searchResults.map(r => {
    const ini = iniciais(r.nome, r.telefone);
    const cor = corDoCliente(r.nome || r.telefone);
    return `
      <div class="conv-card" onclick="abrirConversa('${escapeHtml(r.telefone)}')">
        <div class="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold text-white flex-shrink-0 select-none" style="background:${cor}">${escapeHtml(ini)}</div>
        <div class="flex-1 min-w-0">
          <div class="flex items-center justify-between gap-1 mb-0.5">
            <span class="font-medium text-sm truncate" style="color:var(--text-primary);">${escapeHtml(r.nome)}</span>
            <span class="text-xs flex-shrink-0" style="color:var(--text-muted);">${horarioRelativo(r.criado_em)}</span>
          </div>
          <div class="text-xs" style="color:var(--text-secondary);">${escapeHtml(r.snippet)}</div>
        </div>
      </div>
    `;
  }).join('');
}

function iniciarPresenceTracking() {
  // Heartbeat inicial
  enviarPresence('online');

  // Heartbeat a cada 30s
  setInterval(() => {
    enviarPresence(document.hidden ? 'away' : 'online');
  }, 30000);

  // Visibility change imediato
  document.addEventListener('visibilitychange', () => {
    enviarPresence(document.hidden ? 'away' : 'online');
  });

  // Beacon ao fechar a aba: sendBeacon não suporta headers, então passa token como query param.
  // Backend /admin/presence aceita ?token= como fallback (auth dupla).
  window.addEventListener('beforeunload', () => {
    try {
      const t = localStorage.getItem('token');
      if (!t) return;
      navigator.sendBeacon(
        '/admin/presence?token=' + encodeURIComponent(t),
        new Blob([JSON.stringify({ status: 'offline' })], { type: 'application/json' })
      );
    } catch (_) {}
  });
}

async function bulkSnooze() {
  const telefones = Array.from(state.bulkSelecionadas);
  if (!telefones.length) return;
  const horas = prompt(`Adiar ${telefones.length} conversa(s) por quantas horas?`, '24');
  const h = parseInt(horas);
  if (isNaN(h) || h <= 0 || h > 720) {
    showToast('Horas inválidas (1-720)', 'error');
    return;
  }
  const snoozedUntil = new Date(Date.now() + h * 3600 * 1000).toISOString();
  try {
    const res = await api.bulkConversas(telefones, 'snooze', { snoozed_until: snoozedUntil });
    showToast(`${res.sucesso.length} conversa(s) adiada(s) por ${h}h`, 'success');
    limparBulkSelecao();
    carregarConversas();
  } catch (e) {
    console.error('bulkSnooze:', e);
    showToast('Erro ao adiar', 'error');
  }
}

function renderMentionAutocomplete(query) {
  const pop = document.getElementById('mention-autocomplete');
  if (!pop) return;
  const q = (query || '').toLowerCase();
  const matches = state.allAtendentes.filter(a =>
    a.id !== state.eu.id && a.usuario_login.toLowerCase().includes(q)
  );
  if (!matches.length) {
    pop.classList.add('hidden');
    return;
  }
  pop.innerHTML = matches.map(a => `
    <button class="mention-opt w-full px-3 py-1.5 text-left text-xs transition-colors hover:bg-white/5 flex items-center gap-2" data-login="${escapeHtml(a.usuario_login)}" style="color:var(--text-primary);">
      <span class="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold text-white flex-shrink-0" style="background:var(--accent);">${(a.nome||'?')[0].toUpperCase()}</span>
      <span class="flex-1 truncate">${escapeHtml(a.nome)}</span>
      <code class="text-xs" style="color:var(--text-muted);">@${escapeHtml(a.usuario_login)}</code>
    </button>
  `).join('');
  pop.classList.remove('hidden');

  pop.querySelectorAll('.mention-opt').forEach(btn => {
    btn.addEventListener('click', () => {
      const login = btn.dataset.login;
      const ta = document.getElementById('note-input');
      if (ta) {
        const val = ta.value;
        const m = val.match(/(^|\s)(@[a-z0-9_]*)$/i);
        if (m) {
          ta.value = val.substring(0, m.index) + (m[1] || '') + '@' + login + ' ';
        } else {
          ta.value = val + '@' + login + ' ';
        }
        ta.focus();
      }
      pop.classList.add('hidden');
    });
  });
}

function abrirInfoPanel() {
  const panel = document.getElementById('info-panel');
  if (panel) { panel.classList.remove('hidden'); panel.style.display = 'flex'; }
  state.infoAberto = true;
}

function fecharInfoPanel() {
  const panel = document.getElementById('info-panel');
  if (panel) panel.classList.add('hidden');
  state.infoAberto = false;
}

// ============================================================
// Notas internas
// ============================================================
async function carregarNotas(telefone) {
  try {
    const data = await api.getNotas(telefone);
    if (!data) return;
    renderNotas(data.items || []);
  } catch(e) { console.error('carregarNotas:', e); }
}

function renderNotas(notas) {
  const cont = document.getElementById('notes-list');
  if (!cont) return;

  if (notas.length === 0) {
    cont.innerHTML = '<p class="text-xs" style="color:var(--text-muted);">Nenhuma nota ainda</p>';
    return;
  }

  cont.innerHTML = notas.map(n => `
    <div class="rounded-lg p-2 mb-1" style="background:var(--bg-card);border:1px solid var(--border);" data-nota-id="${n.id}">
      <p class="text-xs mb-1" style="color:var(--text-primary);white-space:pre-wrap;">${escapeHtml(n.texto)}</p>
      <div class="flex items-center justify-between">
        <span class="text-xs" style="color:var(--text-muted);">${horaCurta(n.criado_em)}${n.editado_em ? ' (editado)' : ''}</span>
        <div class="flex gap-2">
          <button class="nota-edit-btn text-xs" style="color:var(--accent);" data-nota-id="${n.id}" data-texto="${escapeHtml(n.texto)}">Editar</button>
          <button class="nota-del-btn text-xs" style="color:var(--danger);" data-nota-id="${n.id}">Excluir</button>
        </div>
      </div>
    </div>
  `).join('');

  // Eventos de editar/excluir
  cont.querySelectorAll('.nota-edit-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const notaId = btn.getAttribute('data-nota-id');
      const texto = btn.getAttribute('data-texto');
      const noteInput = document.getElementById('note-input');
      if (noteInput) { noteInput.value = texto; noteInput.focus(); noteInput.dataset.editingId = notaId; }
    });
  });
  cont.querySelectorAll('.nota-del-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (!confirm('Excluir nota?')) return;
      try {
        await api.deleteNota(btn.getAttribute('data-nota-id'));
        showToast('Nota excluída', 'success');
        carregarNotas(state.conversaAtual);
      } catch(e) { showToast('Erro ao excluir nota', 'error'); }
    });
  });
}

// ============================================================
// Tags
// ============================================================
async function setTag(tag) {
  if (!state.conversaAtual) return;
  try {
    await api.setTag(state.conversaAtual, tag || null);
    if (state.usuarioAtual) {
      state.usuarioAtual.tag = tag || null;
      atualizarHeaderThread(state.usuarioAtual);
    }
    carregarConversas();
    showToast(tag ? `Tag "${tag}" definida` : 'Tag removida', 'success');
  } catch(e) { showToast('Erro ao definir tag', 'error'); }
}

// ============================================================
// Canned responses popover
// ============================================================
function renderCannedPopover(filtro = '') {
  const pop = document.getElementById('canned-popover');
  if (!pop) return;
  const q = (filtro || '').toLowerCase().trim();
  const filtradas = q
    ? CANNED_RESPONSES.filter(c => c.atalho.toLowerCase().includes(q) || c.texto.toLowerCase().includes(q))
    : CANNED_RESPONSES;

  if (!filtradas.length) {
    pop.innerHTML = '<div class="px-3 py-2 text-xs italic" style="color: var(--text-muted);">Nenhuma resposta encontrada</div>';
    return;
  }

  pop.innerHTML = filtradas.map((r, i) => {
    const preview = previewCanned(r.texto);
    const escopoBadge = r.atendente_id
      ? '<span class="text-xs px-1 rounded" style="color: #60a5fa;">●</span>'
      : '<span class="text-xs px-1 rounded" style="color: #10b981;">●</span>';
    return `
      <button class="canned-item w-full px-3 py-2 text-left transition-colors hover:bg-white/5" style="color:var(--text-primary); border-bottom: 1px solid var(--border);" data-id="${r.id}">
        <div class="flex items-center gap-2 mb-0.5">
          ${escopoBadge}
          <code class="text-xs font-mono" style="color: var(--accent);">${escapeHtml(r.atalho)}</code>
        </div>
        <div class="text-xs truncate" style="color: var(--text-secondary);">${escapeHtml(preview)}</div>
      </button>
    `;
  }).join('');

  pop.querySelectorAll('.canned-item').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = parseInt(btn.dataset.id);
      const item = CANNED_RESPONSES.find(c => c.id === id);
      if (!item) return;
      const input = document.getElementById('msg-input');
      if (input) {
        // Se o texto atual começa com "/" (autocomplete), substitui; senão insere
        const atual = input.value;
        const matchAtalho = atual.match(/(^|\s)(\/[a-z0-9_\-]*)$/i);
        if (matchAtalho) {
          input.value = atual.substring(0, matchAtalho.index) +
                        (matchAtalho[1] || '') + previewCanned(item.texto);
        } else {
          input.value = previewCanned(item.texto);
        }
        input.focus();
        // trigger resize
        input.dispatchEvent(new Event('input'));
      }
      pop.classList.add('hidden');
    });
  });
}

// ============================================================
// SSE event handlers
// ============================================================
document.addEventListener('sse:nova_mensagem', (e) => {
  const ev = e.detail;
  if (ev.telefone === state.conversaAtual) {
    // Não duplica se é mensagem humana e tem bolha pendente
    const temPendente = !!document.querySelector('[data-temp-id]');
    if (!(ev.origem === 'humano' && temPendente)) {
      const textoProcessado = (ev.texto || '').replace(/<\s*br\s*\/?>/gi, '\n');
      appendMensagemIncremental(textoProcessado, ev.origem, ev.entregue);
    }
  } else if (ev.origem === 'cliente') {
    showToast(`Nova mensagem de ${ev.nome || ev.telefone}`, 'info');
    tocarNotificacao();
  }
  // Atualiza preview na lista
  const conv = state.conversas.find(c => c.telefone === ev.telefone);
  if (conv) {
    conv.preview = ev.texto || '';
    conv.ultima_mensagem_em = new Date().toISOString();
    renderConvList();
  } else {
    carregarConversas();
  }
});

document.addEventListener('sse:novo_transbordo', (e) => {
  const ev = e.detail;
  showToast(`${ev.nome || ev.telefone} aguardando atendimento humano`, 'transbordo');
  tocarNotificacao();
  carregarConversas();
});

document.addEventListener('sse:atendente_assumiu', (e) => {
  const ev = e.detail;
  carregarConversas();
  if (ev.telefone === state.conversaAtual) {
    api.getConversa(ev.telefone).then(data => {
      if (!data) return;
      state.usuarioAtual = data.usuario;
      atualizarHeaderThread(data.usuario);
      syncComposerState(data.usuario);
    });
  }
});

document.addEventListener('sse:presence_changed', (e) => {
  const ev = e.detail;
  state.presence[String(ev.atendente_id)] = { status: ev.status, last_seen: new Date().toISOString() };
  // Atualiza dropdown de transferir se aberto (apenas re-render se já carregado)
  const trPop = document.getElementById('transferir-popover');
  if (trPop && !trPop.classList.contains('hidden')) abrirPopoverTransferir();
});

document.addEventListener('sse:nova_mention', (e) => {
  const ev = e.detail;
  if (ev.atendente_id !== state.eu.id) return;
  showToast(`${ev.mencionado_por_nome || 'Alguém'} mencionou você`, 'transbordo');
  tocarNotificacao();
  carregarMentions();
});

document.addEventListener('sse:conversa_atribuida', (e) => {
  const ev = e.detail;
  // Se eu era o dono: conversa some da minha lista
  // Se eu sou o destino: aparece nas minhas
  carregarConversas();
  if (ev.telefone === state.conversaAtual) {
    // Recarrega a conversa atual para refletir o novo dono
    api.getConversa(ev.telefone).then(data => {
      if (!data) return;
      state.usuarioAtual = data.usuario;
      atualizarHeaderThread(data.usuario);
      syncComposerState(data.usuario);
    });
  }
  if (ev.para_atendente_id === state.eu.id) {
    showToast(`Conversa transferida para você`, 'info');
    tocarNotificacao();
  }
});

document.addEventListener('sse:status_alterado', (e) => {
  const ev = e.detail;
  const conv = state.conversas.find(c => c.telefone === ev.telefone);
  if (conv) {
    conv.status_conversa = ev.status;
    conv.snoozed_until = ev.snoozed_until;
  }
  if (state.conversaAtual === ev.telefone && state.usuarioAtual) {
    state.usuarioAtual.status_conversa = ev.status;
    state.usuarioAtual.snoozed_until = ev.snoozed_until;
    atualizarStatusBadgeHeader();
  }
  // Se status mudou e não corresponde ao filtro atual, recarrega
  if (state.statusFiltro !== 'todas' && state.statusFiltro !== ev.status) {
    carregarConversas();
  } else {
    renderConvList();
  }
});

document.addEventListener('sse:bot_devolveu', (e) => {
  const ev = e.detail;
  carregarConversas();
  if (ev.telefone === state.conversaAtual) {
    api.getConversa(ev.telefone).then(data => {
      if (!data) return;
      state.usuarioAtual = data.usuario;
      atualizarHeaderThread(data.usuario);
      syncComposerState(data.usuario);
    });
  }
});

// ============================================================
// Event listeners de DOM
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  // Avatar do atendente logado
  const avatarEl = document.getElementById('my-avatar');
  if (avatarEl) {
    avatarEl.textContent = iniciais(state.eu.nome, '?');
    avatarEl.setAttribute('title', state.eu.nome);
  }

  // Filter tabs
  document.getElementById('filter-tabs')?.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-filter]');
    if (!btn) return;
    state.filtro = btn.dataset.filter;
    document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active-tab'));
    btn.classList.add('active-tab');
    carregarConversas();
  });

  // Busca: prefixo "?" ativa modo "Por mensagem" (search global no servidor)
  let _searchTimer = null;
  document.getElementById('search-input')?.addEventListener('input', (e) => {
    const val = e.target.value;
    clearTimeout(_searchTimer);
    if (val.startsWith('?')) {
      const q = val.substring(1).trim();
      state.searchMode = 'mensagem';
      document.getElementById('btn-search-mode').textContent = '🔍 msg';
      _searchTimer = setTimeout(() => executarSearchMensagem(q), 300);
    } else {
      state.searchMode = 'contato';
      document.getElementById('btn-search-mode').textContent = '@';
      state.searchQuery = val.trim();
      state.searchResults = [];
      renderConvList();
    }
  });

  // Toggle de modo via clique no botão
  document.getElementById('btn-search-mode')?.addEventListener('click', () => {
    const inp = document.getElementById('search-input');
    if (!inp) return;
    if (state.searchMode === 'contato') {
      inp.value = '?' + inp.value;
    } else {
      inp.value = inp.value.replace(/^\?/, '');
    }
    inp.dispatchEvent(new Event('input'));
    inp.focus();
  });

  // Btn assumir
  document.getElementById('btn-assumir')?.addEventListener('click', () => {
    if (state.conversaAtual) assumirConversa(state.conversaAtual);
  });

  // Btn interromper bot (mesmo que assumir)
  document.getElementById('btn-interromper')?.addEventListener('click', () => {
    if (state.conversaAtual) assumirConversa(state.conversaAtual);
  });

  // Btn devolver
  document.getElementById('btn-devolver')?.addEventListener('click', () => {
    if (state.conversaAtual) devolverAoBot(state.conversaAtual);
  });

  // Btn info toggle
  document.getElementById('btn-info-toggle')?.addEventListener('click', () => {
    if (state.infoAberto) fecharInfoPanel();
    else abrirInfoPanel();
  });

  // Info close
  document.getElementById('info-close-btn')?.addEventListener('click', fecharInfoPanel);

  // Tag popover
  document.getElementById('btn-tag')?.addEventListener('click', (e) => {
    e.stopPropagation();
    document.getElementById('tag-popover')?.classList.toggle('hidden');
  });
  document.querySelectorAll('.tag-option').forEach(btn => {
    btn.addEventListener('click', () => {
      setTag(btn.dataset.tag);
      document.getElementById('tag-popover')?.classList.add('hidden');
    });
  });
  document.addEventListener('click', () => {
    document.getElementById('tag-popover')?.classList.add('hidden');
    document.getElementById('canned-popover')?.classList.add('hidden');
  });

  // Mute
  document.getElementById('mute-btn')?.addEventListener('click', () => {
    state.muted = !state.muted;
    localStorage.setItem('atendente_mute', state.muted ? '1' : '0');
    document.getElementById('mute-icon-on')?.classList.toggle('hidden', state.muted);
    document.getElementById('mute-icon-off')?.classList.toggle('hidden', !state.muted);
  });
  // Aplica estado inicial
  document.getElementById('mute-icon-on')?.classList.toggle('hidden', state.muted);
  document.getElementById('mute-icon-off')?.classList.toggle('hidden', !state.muted);

  // Canned popover
  renderCannedPopover();
  document.getElementById('canned-btn')?.addEventListener('click', (e) => {
    e.stopPropagation();
    document.getElementById('canned-popover')?.classList.toggle('hidden');
  });

  // Textarea auto-resize + slash autocomplete para canned responses
  const msgInput = document.getElementById('msg-input');
  if (msgInput) {
    msgInput.addEventListener('input', () => {
      msgInput.style.height = 'auto';
      msgInput.style.height = Math.min(msgInput.scrollHeight, 120) + 'px';

      // Detecta atalho "/xxx" no final do texto (ou no início)
      const val = msgInput.value;
      const match = val.match(/(^|\s)(\/[a-z0-9_\-]*)$/i);
      const pop = document.getElementById('canned-popover');
      if (match && pop) {
        renderCannedPopover(match[2]);
        pop.classList.remove('hidden');
      } else if (pop && !pop.classList.contains('hidden')) {
        // Fecha se não há atalho ativo
        pop.classList.add('hidden');
      }
    });
    msgInput.addEventListener('keydown', (e) => {
      const pop = document.getElementById('canned-popover');
      const popVisivel = pop && !pop.classList.contains('hidden');

      if (e.key === 'Escape' && popVisivel) {
        pop.classList.add('hidden');
        return;
      }
      // Tab/Enter dentro de canned: insere a primeira opção
      if ((e.key === 'Tab' || (e.key === 'Enter' && !e.shiftKey)) && popVisivel) {
        const first = pop.querySelector('.canned-item');
        if (first) {
          e.preventDefault();
          first.click();
          return;
        }
      }
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        enviarMensagem();
      }
    });
  }

  // Btn enviar
  document.getElementById('send-btn')?.addEventListener('click', enviarMensagem);

  // Nota: salvar / editar
  document.getElementById('note-save-btn')?.addEventListener('click', async () => {
    const input = document.getElementById('note-input');
    const texto = input?.value.trim();
    if (!texto || !state.conversaAtual) return;
    const editingId = input?.dataset.editingId;
    try {
      if (editingId) {
        await api.editNota(editingId, texto);
        showToast('Nota editada', 'success');
        delete input.dataset.editingId;
      } else {
        await api.addNota(state.conversaAtual, texto);
        showToast('Nota salva', 'success');
      }
      input.value = '';
      carregarNotas(state.conversaAtual);
    } catch(e) { showToast('Erro ao salvar nota', 'error'); }
  });

  // Inicializa
  // Status filter row
  document.getElementById('status-filter-row')?.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-status]');
    if (!btn) return;
    state.statusFiltro = btn.dataset.status;
    document.querySelectorAll('.status-filter').forEach(b => {
      if (b.dataset.status === state.statusFiltro) {
        b.classList.add('active-status');
        b.style.color = 'var(--accent)';
        b.style.background = 'rgba(99, 102, 241, 0.15)';
      } else {
        b.classList.remove('active-status');
        b.style.color = 'var(--text-secondary)';
        b.style.background = '';
      }
    });
    carregarConversas();
  });

  // Status dropdown trigger
  document.getElementById('btn-status')?.addEventListener('click', (e) => {
    e.stopPropagation();
    document.getElementById('status-popover')?.classList.toggle('hidden');
  });

  // Transferir dropdown trigger
  document.getElementById('btn-transferir')?.addEventListener('click', (e) => {
    e.stopPropagation();
    const pop = document.getElementById('transferir-popover');
    if (pop && !pop.classList.contains('hidden')) {
      pop.classList.add('hidden');
    } else {
      abrirPopoverTransferir();
    }
  });

  // Status options
  document.querySelectorAll('.status-option').forEach(opt => {
    opt.addEventListener('click', () => {
      const novo = opt.dataset.status;
      document.getElementById('status-popover')?.classList.add('hidden');
      alterarStatus(novo);
    });
  });

  // Botão adicionar label (info panel)
  document.getElementById('btn-add-label')?.addEventListener('click', (e) => {
    e.stopPropagation();
    togglePickerLabels();
  });

  // Search dentro do label picker
  document.getElementById('label-search')?.addEventListener('input', (e) => {
    renderLabelPicker(e.target.value);
  });
  document.getElementById('label-search')?.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.getElementById('label-picker')?.classList.add('hidden');
    }
  });

  // Click fora fecha label picker
  document.addEventListener('click', (e) => {
    const picker = document.getElementById('label-picker');
    const btn = document.getElementById('btn-add-label');
    if (picker && !picker.classList.contains('hidden') &&
        !picker.contains(e.target) && e.target !== btn) {
      picker.classList.add('hidden');
    }
    // Status popover
    const stPop = document.getElementById('status-popover');
    const stBtn = document.getElementById('btn-status');
    if (stPop && !stPop.classList.contains('hidden') &&
        !stPop.contains(e.target) && e.target !== stBtn && !stBtn?.contains(e.target)) {
      stPop.classList.add('hidden');
    }
    // Transferir popover
    const trPop = document.getElementById('transferir-popover');
    const trBtn = document.getElementById('btn-transferir');
    if (trPop && !trPop.classList.contains('hidden') &&
        !trPop.contains(e.target) && e.target !== trBtn && !trBtn?.contains(e.target)) {
      trPop.classList.add('hidden');
    }
  });

  // Save view + delete view
  document.getElementById('btn-save-view')?.addEventListener('click', salvarViewAtual);

  // Bulk actions: checkbox change
  document.getElementById('conv-list')?.addEventListener('change', (e) => {
    const cb = e.target.closest('.bulk-check');
    if (!cb) return;
    const tel = cb.dataset.tel;
    if (cb.checked) state.bulkSelecionadas.add(tel);
    else state.bulkSelecionadas.delete(tel);
    atualizarBulkBar();
    // Sem re-render: apenas marca/desmarca CSS visual
    cb.closest('.conv-card')?.classList.toggle('bulk-selected', cb.checked);
  });

  // Bulk actions: botões
  document.getElementById('bulk-resolver')?.addEventListener('click', bulkResolver);
  document.getElementById('bulk-snooze')?.addEventListener('click', bulkSnooze);
  document.getElementById('bulk-cancelar')?.addEventListener('click', limparBulkSelecao);

  // Botão mentions inbox
  document.getElementById('btn-mentions-inbox')?.addEventListener('click', (e) => {
    e.stopPropagation();
    const pop = document.getElementById('mentions-popover');
    if (!pop) return;
    if (pop.classList.contains('hidden')) {
      renderMentionsList();
      pop.classList.remove('hidden');
    } else {
      pop.classList.add('hidden');
    }
  });

  // Click fora fecha mentions popover
  document.addEventListener('click', (e) => {
    const pop = document.getElementById('mentions-popover');
    const btn = document.getElementById('btn-mentions-inbox');
    if (pop && !pop.classList.contains('hidden') &&
        !pop.contains(e.target) && !btn?.contains(e.target)) {
      pop.classList.add('hidden');
    }
    const macPop = document.getElementById('mention-autocomplete');
    const ta = document.getElementById('note-input');
    if (macPop && !macPop.classList.contains('hidden') &&
        !macPop.contains(e.target) && e.target !== ta) {
      macPop.classList.add('hidden');
    }
  });

  // Autocomplete @ no textarea de notas
  const noteInput = document.getElementById('note-input');
  if (noteInput) {
    noteInput.addEventListener('input', () => {
      const val = noteInput.value;
      const m = val.match(/(^|\s)(@[a-z0-9_]*)$/i);
      const pop = document.getElementById('mention-autocomplete');
      if (m && pop) {
        if (!state.allAtendentes.length) carregarAtendentesParaTransfer().then(() => {
          renderMentionAutocomplete(m[2].substring(1));
          if (!pop.classList.contains('hidden')) posicionarAutocomplete(noteInput, pop);
        });
        renderMentionAutocomplete(m[2].substring(1));
        posicionarAutocomplete(noteInput, pop);
      } else if (pop) {
        pop.classList.add('hidden');
      }
    });
    noteInput.addEventListener('keydown', (e) => {
      const pop = document.getElementById('mention-autocomplete');
      if (e.key === 'Escape' && pop) pop.classList.add('hidden');
    });
  }

  carregarLabelsGlobais();
  carregarCanned();
  carregarAtendentesParaTransfer();
  carregarMentions();
  carregarPresence();
  carregarViews();
  carregarConversas();
  sse.conectar();
  iniciarPresenceTracking();

  // Refresh mentions a cada 60s (backup do SSE)
  setInterval(carregarMentions, 60000);
  // Refresh presence a cada 60s (sync com servidor)
  setInterval(carregarPresence, 60000);

  // ============================================================
  // ATALHOS DE TECLADO
  // ============================================================
  document.addEventListener('keydown', (e) => {
    // Ignora se foco em input/textarea/contenteditable
    const tag = (e.target.tagName || '').toLowerCase();
    const dentroInput = tag === 'input' || tag === 'textarea' || e.target.isContentEditable;

    // Esc fecha modais/popovers (funciona mesmo dentro de inputs)
    if (e.key === 'Escape') {
      document.getElementById('modal-shortcuts')?.classList.add('hidden');
      document.getElementById('canned-popover')?.classList.add('hidden');
      document.getElementById('label-picker')?.classList.add('hidden');
      document.getElementById('status-popover')?.classList.add('hidden');
      document.getElementById('transferir-popover')?.classList.add('hidden');
      document.getElementById('mentions-popover')?.classList.add('hidden');
      document.getElementById('mention-autocomplete')?.classList.add('hidden');
      return;
    }
    if (dentroInput) return;

    switch (e.key) {
      case 'j': {
        e.preventDefault();
        // Próxima conversa
        const cards = Array.from(document.querySelectorAll('.conv-card'));
        if (!cards.length) return;
        const idx = cards.findIndex(c => c.dataset.tel === state.conversaAtual);
        const next = cards[Math.min(idx + 1, cards.length - 1)];
        if (next) abrirConversa(next.dataset.tel);
        break;
      }
      case 'k': {
        e.preventDefault();
        const cards = Array.from(document.querySelectorAll('.conv-card'));
        if (!cards.length) return;
        const idx = cards.findIndex(c => c.dataset.tel === state.conversaAtual);
        const prev = cards[Math.max(idx - 1, 0)];
        if (prev) abrirConversa(prev.dataset.tel);
        break;
      }
      case 'c': {
        e.preventDefault();
        document.getElementById('msg-input')?.focus();
        break;
      }
      case 'e': {
        if (!state.conversaAtual) return;
        e.preventDefault();
        alterarStatus('resolved');
        break;
      }
      case 's': {
        if (!state.conversaAtual) return;
        e.preventDefault();
        alterarStatus('snoozed');
        break;
      }
      case '/': {
        e.preventDefault();
        document.getElementById('search-input')?.focus();
        break;
      }
      case 'n': {
        if (!state.conversaAtual) return;
        e.preventDefault();
        if (!state.infoAberto) abrirInfoPanel();
        setTimeout(() => document.getElementById('note-input')?.focus(), 100);
        break;
      }
      case 'i': {
        e.preventDefault();
        if (state.infoAberto) fecharInfoPanel();
        else abrirInfoPanel();
        break;
      }
      case '?': {
        e.preventDefault();
        document.getElementById('modal-shortcuts')?.classList.remove('hidden');
        break;
      }
    }
  });

  // Fechar modal de atalhos
  document.getElementById('close-shortcuts')?.addEventListener('click', () => {
    document.getElementById('modal-shortcuts')?.classList.add('hidden');
  });
  document.getElementById('modal-shortcuts')?.addEventListener('click', (e) => {
    if (e.target === document.getElementById('modal-shortcuts')) {
      document.getElementById('modal-shortcuts').classList.add('hidden');
    }
  });

  // Refresh periódico da lista (60s)
  setInterval(carregarConversas, 60000);
});
