// Painel atendente — Barbearia Bolshoi
// Vanilla JS + fetch + fetch-streaming SSE. Sem build, sem framework.

// TASK-013: canned responses
const RESPOSTAS_RAPIDAS = [
  "Olá! Em que posso ajudá-lo(a)?",
  "Obrigado por entrar em contato com a Barbearia Bolshoi!",
  "Para agendar, utilize o aplicativo AppBarber.",
  "Nosso endereço é [endereço da barbearia]. Estamos abertos de segunda a sábado.",
  "Aguarde um momento, estou verificando as informações.",
  "Posso ajudar com mais alguma coisa?",
  "Encerrando o atendimento. Obrigado pela preferência!",
  "Em caso de dúvidas, entre em contato pelo WhatsApp novamente.",
];

const TOKEN = localStorage.getItem('token');
const ATENDENTE_ID = parseInt(localStorage.getItem('atendente_id') || '0');
const ATENDENTE_NOME = localStorage.getItem('atendente_nome') || '';
const MUTE_KEY = 'atendente_mute';

if (!TOKEN) {
  window.location.href = '/static/admin/login.html';
}

document.getElementById('nome-atendente').textContent = ATENDENTE_NOME;

// TASK-019: exibir último acesso na sidebar
(function exibirUltimoAcesso() {
  const iso = localStorage.getItem('ultimo_login');
  const el = document.getElementById('ultimo-acesso');
  if (!el) return;
  if (!iso) { el.classList.add('hidden'); return; }
  try {
    const d = new Date(iso);
    const dd = String(d.getDate()).padStart(2, '0');
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const aaaa = d.getFullYear();
    const hh = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    el.textContent = `Último acesso: ${dd}/${mm}/${aaaa} às ${hh}:${min}`;
    el.classList.remove('hidden');
  } catch (_) {
    el.classList.add('hidden');
  }
})();

let conversaAtual = null;
let conversas = [];
let muted = localStorage.getItem(MUTE_KEY) === '1';

// ============================================================
// HTTP helpers
// ============================================================

const headersAuth = () => ({
  'Authorization': `Bearer ${TOKEN}`,
  'Content-Type': 'application/json',
});

async function api(url, opts = {}) {
  const res = await fetch(url, {
    ...opts,
    headers: { ...headersAuth(), ...(opts.headers || {}) },
  });
  if (res.status === 401) {
    localStorage.clear();
    window.location.href = '/static/admin/login.html';
    return;
  }
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`${res.status}: ${txt}`);
  }
  return res.json();
}

// ============================================================
// UI helpers
// ============================================================

function escapeHtml(s) {
  return (s || '').replace(/[&<>"']/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
}

const _CORES_AVATAR = [
  'bg-blue-500', 'bg-purple-500', 'bg-pink-500', 'bg-emerald-500',
  'bg-amber-500', 'bg-rose-500', 'bg-indigo-500', 'bg-teal-500',
  'bg-cyan-500', 'bg-fuchsia-500', 'bg-lime-600', 'bg-orange-500',
];

function corDoTelefone(tel) {
  let h = 0;
  for (const c of (tel || '')) h = ((h * 31) + c.charCodeAt(0)) >>> 0;
  return _CORES_AVATAR[h % _CORES_AVATAR.length];
}

function iniciais(nome, fallback) {
  const fonte = (nome || '').trim() || (fallback || '?');
  const partes = fonte.trim().split(/\s+/);
  const a = (partes[0] || '?')[0] || '?';
  const b = (partes[1] || '')[0] || '';
  return (a + b).toUpperCase();
}

function avatarHTML(nome, tel, size = 'w-10 h-10 text-sm') {
  const cor = corDoTelefone(tel);
  return `<div class="${cor} ${size} rounded-full flex items-center justify-center text-white font-bold flex-shrink-0 select-none">${escapeHtml(iniciais(nome, tel))}</div>`;
}

function horarioRelativo(iso) {
  if (!iso) return '';
  const data = new Date(iso);
  const diff = (Date.now() - data.getTime()) / 1000;
  if (diff < 45) return 'agora';
  if (diff < 90) return '1min';
  if (diff < 3600) return `${Math.floor(diff / 60)}min`;
  if (diff < 7200) return '1h';
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
  if (diff < 172800) return 'ontem';
  if (diff < 604800) return `${Math.floor(diff / 86400)}d`;
  return data.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
}

function dataLabel(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const hojeStr = new Date().toLocaleDateString('pt-BR');
  const ontemStr = new Date(Date.now() - 86400000).toLocaleDateString('pt-BR');
  const dStr = d.toLocaleDateString('pt-BR');
  if (dStr === hojeStr) return 'Hoje';
  if (dStr === ontemStr) return 'Ontem';
  return d.toLocaleDateString('pt-BR', { weekday: 'long', day: '2-digit', month: 'long' });
}

function horaCurta(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

// ============================================================
// Toast + som notificação
// ============================================================

function toast(texto, tipo = 'info') {
  const cores = {
    info: 'bg-amber-600',
    transbordo: 'bg-red-600',
    ok: 'bg-emerald-600',
  };
  const el = document.createElement('div');
  el.className = `${cores[tipo] || cores.info} slide-in text-white px-4 py-2.5 rounded-lg shadow-lg text-sm pointer-events-auto max-w-xs`;
  el.textContent = texto;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => {
    el.style.transition = 'opacity 0.4s, transform 0.4s';
    el.style.opacity = '0';
    el.style.transform = 'translateX(120%)';
    setTimeout(() => el.remove(), 400);
  }, 4500);
}

function tocarNotificacao() {
  if (muted) return;
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    // Dois tons agradáveis estilo Slack/Discord.
    const tons = [{ f: 880, d: 0 }, { f: 1175, d: 0.09 }];
    tons.forEach(({ f, d }) => {
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.type = 'sine';
      o.frequency.value = f;
      o.connect(g);
      g.connect(ctx.destination);
      const t = ctx.currentTime + d;
      g.gain.setValueAtTime(0, t);
      g.gain.linearRampToValueAtTime(0.18, t + 0.015);
      g.gain.exponentialRampToValueAtTime(0.001, t + 0.30);
      o.start(t);
      o.stop(t + 0.32);
    });
    setTimeout(() => ctx.close(), 800);
  } catch (e) { /* silencioso */ }
}

// ============================================================
// Tag helpers
// ============================================================

function tagBadgeHTML(tag) {
  if (tag === 'resolvido') {
    return '<span class="text-[9px] uppercase font-bold text-green-700 bg-green-100 px-1.5 py-0.5 rounded">&#10003; Resolvido</span>';
  }
  if (tag === 'follow_up') {
    return '<span class="text-[9px] uppercase font-bold text-yellow-700 bg-yellow-100 px-1.5 py-0.5 rounded">&#8617; Follow-up</span>';
  }
  return '';
}

async function definirTag(telefone, tag) {
  // tag pode ser "resolvido", "follow_up" ou null (remover)
  await api(`/admin/conversa/${encodeURIComponent(telefone)}/tag`, {
    method: 'PATCH',
    body: JSON.stringify({ tag }),
  });
  // Atualiza o objeto local em memória
  const conv = conversas.find(c => c.telefone === telefone);
  if (conv) conv.tag = tag;
  // Atualiza badge na sidebar sem re-fetch completo
  const li = document.querySelector(`#lista-conversas li[data-telefone="${CSS.escape(telefone)}"]`);
  if (li) {
    const badgeEl = li.querySelector('[data-tag-badge]');
    if (badgeEl) badgeEl.innerHTML = tagBadgeHTML(tag);
  }
  // Atualiza seletor no header
  renderTagHeader(tag);
  const labels = { resolvido: 'Resolvido', follow_up: 'Follow-up', null: 'removida' };
  toast(`Tag ${labels[tag] || 'removida'}.`, 'ok');
}

function renderTagHeader(tag) {
  const el = document.getElementById('tag-selector');
  if (!el) return;
  document.querySelectorAll('#tag-selector button[data-tag]').forEach(btn => {
    const isAtivo = btn.dataset.tag === (tag || '');
    btn.classList.toggle('ring-2', isAtivo);
    btn.classList.toggle('ring-offset-1', isAtivo);
  });
}

// ============================================================
// Render — sidebar
// ============================================================

function renderListaConversas() {
  const filtro = document.getElementById('filtro').value.toLowerCase().trim();
  const ul = document.getElementById('lista-conversas');
  ul.innerHTML = '';

  const visiveis = conversas.filter(c => {
    if (!filtro) return true;
    return (c.nome || '').toLowerCase().includes(filtro) || c.telefone.includes(filtro);
  });

  if (visiveis.length === 0) {
    const li = document.createElement('li');
    li.className = 'px-4 py-8 text-center text-xs text-gray-400';
    li.textContent = filtro ? 'Nenhuma conversa encontrada' : 'Sem conversas ainda';
    ul.appendChild(li);
    return;
  }

  for (const c of visiveis) {
    const li = document.createElement('li');
    const ativo = conversaAtual === c.telefone;

    let etiqueta = '';
    let extraClasses = '';
    if (c.aguardando_humano) {
      etiqueta = '<span class="text-[9px] uppercase font-bold text-red-700 bg-red-100 px-1.5 py-0.5 rounded">Aguardando</span>';
      extraClasses = 'pulse-red';
    } else if (c.assumida_por_mim) {
      etiqueta = '<span class="text-[9px] uppercase font-bold text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded">Eu</span>';
    } else if (c.atendente_id) {
      etiqueta = '<span class="text-[9px] uppercase font-bold text-gray-600 bg-gray-100 px-1.5 py-0.5 rounded">Outro</span>';
    } else {
      etiqueta = '<span class="text-[9px] uppercase font-bold text-blue-700 bg-blue-100 px-1.5 py-0.5 rounded">Bot</span>';
    }

    const tagBadge = tagBadgeHTML(c.tag);

    li.className = `px-3 py-2.5 border-b border-gray-100 cursor-pointer transition relative ${ativo ? 'bg-amber-50' : 'hover:bg-gray-50'}`;
    li.dataset.telefone = c.telefone;
    li.innerHTML = `
      <div class="flex items-start gap-2.5">
        <div class="${extraClasses} rounded-full">
          ${avatarHTML(c.nome, c.telefone, 'w-10 h-10 text-sm')}
        </div>
        <div class="flex-1 min-w-0">
          <div class="flex items-baseline justify-between gap-2">
            <span class="font-semibold text-sm text-gray-900 truncate">${escapeHtml(c.nome || c.telefone)}</span>
            <span class="text-[10px] text-gray-400 flex-shrink-0">${horarioRelativo(c.ultima_mensagem_em)}</span>
          </div>
          <div class="flex items-center justify-between gap-2 mt-0.5">
            <span class="text-xs text-gray-500 truncate">${escapeHtml(c.preview || c.telefone)}</span>
            <div class="flex items-center gap-1 flex-shrink-0"><span data-tag-badge>${tagBadge}</span>${etiqueta}</div>
          </div>
        </div>
      </div>
    `;
    li.addEventListener('click', () => abrirConversa(c.telefone));
    ul.appendChild(li);
  }
}

// TASK-012: compute and render queue metrics
function atualizarMetricas() {
  const aguardando = conversas.filter(c => c.aguardando_humano === true).length;
  const atendimento = conversas.filter(c => c.atendente_id !== null && c.atendente_id !== undefined).length;
  const comBot = conversas.filter(c => c.bot_ativo === true && !c.aguardando_humano).length;
  document.getElementById('metric-aguardando').textContent = aguardando;
  document.getElementById('metric-atendimento').textContent = atendimento;
  document.getElementById('metric-bot').textContent = comBot;
}

async function carregarConversas() {
  try {
    conversas = await api('/admin/conversas');
    renderListaConversas();
    atualizarMetricas();
  } catch (e) { console.error(e); }
}

// ============================================================
// Render — thread
// ============================================================

async function abrirConversa(telefone) {
  conversaAtual = telefone;
  renderListaConversas();
  // TASK-018: auto-close sidebar drawer on mobile when conversation is selected
  if (window.innerWidth < 640) fecharSidebar();
  try {
    const data = await api(`/admin/conversa/${encodeURIComponent(telefone)}`);
    renderThread(data);
  } catch (e) { console.error(e); }
  // TASK-015: mostrar painel e carregar notas ao abrir conversa
  document.getElementById('painel-notas').classList.remove('hidden');
  carregarNotas(telefone);
}

function atualizarHeaderThread(u) {
  document.getElementById('thread-header').classList.remove('hidden');
  document.getElementById('thread-avatar').innerHTML = avatarHTML(u.nome, u.telefone, 'w-10 h-10 text-sm');
  document.getElementById('thread-nome').textContent = u.nome || u.telefone;
  document.getElementById('thread-telefone').textContent = u.telefone;

  // Render tag selector
  renderTagHeader(u.tag);

  const status = document.getElementById('thread-status');
  const btnAssumir = document.getElementById('btn-assumir');
  const btnDevolver = document.getElementById('btn-devolver');
  const footer = document.getElementById('thread-footer');

  btnAssumir.classList.add('hidden');
  btnDevolver.classList.add('hidden');
  footer.classList.add('hidden');

  if (u.atendente_id === ATENDENTE_ID) {
    status.textContent = '🟢 Você está atendendo essa conversa.';
    status.className = 'text-xs mt-1.5 text-emerald-700 font-medium';
    btnDevolver.classList.remove('hidden');
    footer.classList.remove('hidden');
    setTimeout(() => document.getElementById('texto-msg').focus(), 50);
  } else if (u.atendente_id) {
    status.textContent = `Conversa atendida por outro atendente (id ${u.atendente_id}).`;
    status.className = 'text-xs mt-1.5 text-gray-500';
  } else if (u.aguardando_humano) {
    status.textContent = '🔴 Cliente aguardando atendente humano.';
    status.className = 'text-xs mt-1.5 text-red-600 font-semibold';
    btnAssumir.classList.remove('hidden');
  } else if (u.bot_ativo) {
    status.textContent = '🤖 Bot ativo. Você pode assumir a conversa se quiser.';
    status.className = 'text-xs mt-1.5 text-blue-600';
    btnAssumir.classList.remove('hidden');
  } else {
    status.textContent = 'Bot inativo, sem atendente designado.';
    status.className = 'text-xs mt-1.5 text-gray-500';
    btnAssumir.classList.remove('hidden');
  }
}

function renderThread(data) {
  atualizarHeaderThread(data.usuario);

  const cont = document.getElementById('thread-mensagens');
  cont.innerHTML = '';

  if (data.mensagens.length === 0) {
    const div = document.createElement('div');
    div.className = 'flex items-center justify-center h-full text-sm text-gray-400';
    div.textContent = 'Nenhuma mensagem ainda';
    cont.appendChild(div);
    return;
  }

  let ultimoDiaLabel = null;
  for (const m of data.mensagens) {
    const labelDia = dataLabel(m.criado_em);
    if (labelDia && labelDia !== ultimoDiaLabel) {
      ultimoDiaLabel = labelDia;
      cont.appendChild(separadorData(labelDia));
    }
    if (m.cliente) {
      cont.appendChild(bolha(m.cliente, 'cliente', m.criado_em));
    }
    if (m.resposta) {
      cont.appendChild(bolha(
        m.resposta.replace(/<\s*br\s*\/?>/gi, '\n'),
        m.origem || 'bot',
        m.criado_em,
        { entregue: m.entregue }
      ));
    }
  }
  scrollarFim();
}

function separadorData(label) {
  const div = document.createElement('div');
  div.className = 'flex items-center justify-center my-3 fade-in';
  div.innerHTML = `<span class="text-[11px] font-medium text-gray-500 bg-white border border-gray-200 px-3 py-0.5 rounded-full">${escapeHtml(label)}</span>`;
  return div;
}

function indicadorEntrega(entregue, pending) {
  // Ícones de entrega WhatsApp: ✓ entregue / ⚠ falhou / "..." pendente / nada para cliente.
  if (pending) return '<span data-status class="ml-1.5 italic">enviando…</span>';
  if (entregue === true) {
    return '<span title="Entregue ao WhatsApp" class="ml-1.5 text-emerald-600 font-bold">✓</span>';
  }
  if (entregue === false) {
    return '<span title="FALHOU - Meta API rejeitou. Token expirado, número inválido ou janela 24h fechada." class="ml-1.5 text-red-600 font-bold cursor-help">⚠ não entregue</span>';
  }
  return '';
}

// TASK-014: resolve MÍDIA_ prefix to chip HTML
function resolverConteudoMensagem(texto) {
  if (texto && texto.startsWith('MÍDIA_')) {
    const tipo = texto.replace('MÍDIA_', '').toLowerCase();
    const chips = {
      audio: '🎵 Áudio',
      image: '🖼️ Imagem',
      document: '📎 Documento',
    };
    const label = chips[tipo] || '📁 Mídia';
    return { html: `<span class="inline-block bg-gray-100 text-gray-600 text-xs px-2 py-1 rounded-full">${label}</span>`, isMedia: true };
  }
  return { html: null, isMedia: false };
}

function bolha(texto, origem, criado_em, opts = {}) {
  const wrapper = document.createElement('div');
  const isOutgoing = origem === 'humano' || origem === 'bot';

  let cls = '';
  let label = '';
  if (origem === 'cliente') {
    cls = 'bg-white border border-gray-200';
    label = 'Cliente';
  } else if (origem === 'humano') {
    cls = 'bg-emerald-100 border border-emerald-200';
    label = 'Atendente';
  } else {
    cls = 'bg-amber-50 border border-amber-200';
    label = 'Bot';
  }

  // Bolhas saindo (bot/humano) que falharam ganham borda vermelha de aviso.
  if (isOutgoing && opts.entregue === false) {
    cls = 'bg-red-50 border-2 border-red-300';
  }

  wrapper.className = `flex fade-in ${isOutgoing ? 'justify-end' : 'justify-start'}`;
  if (opts.tempId) wrapper.dataset.tempId = opts.tempId;
  if (opts.pending) wrapper.classList.add('opacity-60');

  const hora = horaCurta(criado_em);
  // Só mostra indicador em mensagens saindo (cliente não tem status de entrega).
  const status = isOutgoing ? indicadorEntrega(opts.entregue, opts.pending) : '';

  // TASK-014: check for MÍDIA_ prefix
  const { html: mediaHtml, isMedia } = resolverConteudoMensagem(texto);
  const conteudoHtml = isMedia
    ? mediaHtml
    : `<span class="block text-sm whitespace-pre-wrap text-gray-800 leading-relaxed">${escapeHtml(texto)}</span>`;

  wrapper.innerHTML = `
    <div class="max-w-md px-3 py-2 rounded-2xl shadow-sm ${cls} ${isOutgoing ? 'rounded-tr-sm' : 'rounded-tl-sm'}">
      <span class="block text-[10px] uppercase font-bold text-gray-500 mb-1 tracking-wide">${label}</span>
      ${conteudoHtml}
      <span class="block text-[10px] text-gray-400 mt-1 text-right">${hora}${status}</span>
    </div>
  `;
  return wrapper;
}

function scrollarFim() {
  const cont = document.getElementById('thread-mensagens');
  // requestAnimationFrame garante que o layout terminou antes de medir scrollHeight.
  // Sem isso, scroll pode parar antes do fim em DOMs grandes (atualização síncrona
  // do Tailwind via CDN tem latência mínima).
  requestAnimationFrame(() => {
    cont.scrollTop = cont.scrollHeight;
    // Segurança extra: tenta de novo no próximo frame, caso imagens/fonts ainda
    // estejam alterando o tamanho.
    requestAnimationFrame(() => {
      cont.scrollTop = cont.scrollHeight;
    });
  });
}

function estaNoFim() {
  const cont = document.getElementById('thread-mensagens');
  return (cont.scrollHeight - cont.scrollTop - cont.clientHeight) < 100;
}

// ============================================================
// Listeners — UI
// ============================================================

document.getElementById('filtro').addEventListener('input', renderListaConversas);

document.getElementById('btn-sair').addEventListener('click', () => {
  if (!confirm('Sair do painel?')) return;
  localStorage.clear();
  window.location.href = '/static/admin/login.html';
});

document.getElementById('btn-mute').addEventListener('click', () => {
  muted = !muted;
  localStorage.setItem(MUTE_KEY, muted ? '1' : '0');
  atualizarIconeMute();
});

function atualizarIconeMute() {
  const icone = document.getElementById('icone-som');
  const btn = document.getElementById('btn-mute');
  if (muted) {
    icone.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" d="M9.75 9.75v4.5L12 16.5h.75v-9H12L9.75 9.75zM6 9.75h3.75M3 3l18 18"/>';
    btn.title = 'Notificações silenciadas — clique para reativar';
    btn.classList.add('text-red-500');
  } else {
    icone.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" d="M15 8.25v7.5L12 18 9 15.75H6V8.25h3L12 6l3 2.25zM18 9.75a3.75 3.75 0 010 4.5M20.25 7.5a6.75 6.75 0 010 9"/>';
    btn.title = 'Silenciar notificações';
    btn.classList.remove('text-red-500');
  }
}
atualizarIconeMute();

// ============================================================
// TASK-013: canned responses panel
// ============================================================

(function iniciarRespostasRapidas() {
  const listaDom = document.getElementById('lista-rapidas');
  RESPOSTAS_RAPIDAS.forEach(texto => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'w-full text-left text-sm px-3 py-2 hover:bg-amber-50 hover:text-amber-700 transition text-gray-700 border-b border-gray-100 last:border-0';
    btn.textContent = texto;
    btn.addEventListener('click', () => {
      const ta = document.getElementById('texto-msg');
      ta.value = texto;
      autoResize();
      ta.focus();
      fecharPopoverRapidas();
    });
    listaDom.appendChild(btn);
  });
})();

function fecharPopoverRapidas() {
  document.getElementById('popover-rapidas').classList.add('hidden');
}

document.getElementById('btn-rapidas').addEventListener('click', (e) => {
  e.stopPropagation();
  document.getElementById('popover-rapidas').classList.toggle('hidden');
});

document.addEventListener('click', (e) => {
  const popover = document.getElementById('popover-rapidas');
  if (popover && !popover.classList.contains('hidden') &&
      !popover.contains(e.target) && e.target !== document.getElementById('btn-rapidas')) {
    fecharPopoverRapidas();
  }
});

// ============================================================
// TASK-018: responsive sidebar toggle (mobile)
// ============================================================

function abrirSidebar() {
  document.getElementById('sidebar').classList.remove('-translate-x-full');
  document.getElementById('sidebar-backdrop').classList.remove('hidden');
}

function fecharSidebar() {
  document.getElementById('sidebar').classList.add('-translate-x-full');
  document.getElementById('sidebar-backdrop').classList.add('hidden');
}

document.getElementById('btn-hamburger').addEventListener('click', abrirSidebar);
document.getElementById('sidebar-backdrop').addEventListener('click', fecharSidebar);

document.getElementById('btn-assumir').addEventListener('click', async (e) => {
  if (!conversaAtual) return;
  e.target.disabled = true;
  try {
    await api(`/admin/assumir/${encodeURIComponent(conversaAtual)}`, { method: 'POST' });
    await carregarConversas();
    await abrirConversa(conversaAtual);
    toast('Conversa assumida com sucesso.', 'ok');
  } catch (err) {
    toast('Erro ao assumir: ' + err.message, 'transbordo');
  } finally {
    e.target.disabled = false;
  }
});

document.getElementById('btn-devolver').addEventListener('click', async (e) => {
  if (!conversaAtual) return;
  if (!confirm('Devolver essa conversa para a IA? O cliente será avisado.')) return;
  e.target.disabled = true;
  try {
    await api(`/admin/devolver/${encodeURIComponent(conversaAtual)}`, { method: 'POST' });
    await carregarConversas();
    await abrirConversa(conversaAtual);
    toast('Bot voltou ao atendimento.', 'ok');
  } catch (err) {
    toast('Erro ao devolver: ' + err.message, 'transbordo');
  } finally {
    e.target.disabled = false;
  }
});

// ============================================================
// Textarea autoresize + Enter envia
// ============================================================

const textarea = document.getElementById('texto-msg');
function autoResize() {
  textarea.style.height = 'auto';
  textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}
textarea.addEventListener('input', autoResize);
textarea.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    document.getElementById('form-enviar').requestSubmit();
  }
});

// ============================================================
// Envio com optimistic UI
// ============================================================

document.getElementById('form-enviar').addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!conversaAtual) return;
  const texto = textarea.value.trim();
  if (!texto) return;

  const btn = document.getElementById('btn-enviar');
  const cont = document.getElementById('thread-mensagens');
  const tempId = 'temp-' + Date.now() + '-' + Math.random().toString(36).slice(2, 7);

  // Optimistic: bolha aparece imediatamente
  const tempBolha = bolha(texto, 'humano', new Date().toISOString(), { tempId, pending: true });
  cont.appendChild(tempBolha);
  scrollarFim();

  textarea.value = '';
  autoResize();
  btn.disabled = true;
  btn.textContent = 'Enviando…';

  try {
    const resp = await api(`/admin/enviar/${encodeURIComponent(conversaAtual)}`, {
      method: 'POST',
      body: JSON.stringify({ texto }),
    });
    // Sucesso — atualiza visual com status entregue real reportado pelo server.
    tempBolha.classList.remove('opacity-60');
    const status = tempBolha.querySelector('[data-status]');
    if (status) {
      // Substitui "enviando..." pelo indicador real ✓ ou ⚠
      const novoSpan = document.createElement('span');
      novoSpan.innerHTML = indicadorEntrega(resp.entregue, false);
      status.replaceWith(novoSpan.firstChild || novoSpan);
    }
    // Se Meta rejeitou, marca bolha vermelha.
    if (resp.entregue === false) {
      const inner = tempBolha.querySelector('div');
      if (inner) {
        inner.classList.remove('bg-emerald-100', 'border-emerald-200');
        inner.classList.add('bg-red-50', 'border-2', 'border-red-300');
      }
      toast('⚠ Meta API rejeitou — mensagem não chegou ao cliente.', 'transbordo');
    }
    carregarConversas();
  } catch (err) {
    // Falha — marca vermelho com botão retry
    const inner = tempBolha.querySelector('div');
    if (inner) {
      inner.classList.remove('bg-emerald-100', 'border-emerald-200');
      inner.classList.add('bg-red-100', 'border-red-300');
    }
    const status = tempBolha.querySelector('[data-status]');
    if (status) {
      status.textContent = '⚠ falha ao enviar — clique para tentar de novo';
      status.classList.add('cursor-pointer', 'underline');
      status.addEventListener('click', () => {
        tempBolha.remove();
        textarea.value = texto;
        autoResize();
        textarea.focus();
      });
    }
    toast('Falha ao enviar mensagem.', 'transbordo');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Enviar';
    textarea.focus();
  }
});

// ============================================================
// SSE — eventos em tempo real
// ============================================================

async function conectarSSE() {
  setStatusConexao(false);
  try {
    const res = await fetch('/admin/eventos/stream', { headers: headersAuth() });
    if (!res.ok || !res.body) {
      setTimeout(conectarSSE, 3000);
      return;
    }
    setStatusConexao(true);
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocos = buffer.split('\n\n');
      buffer = blocos.pop() || '';
      for (const bloco of blocos) {
        const linha = bloco.split('\n').find(l => l.startsWith('data: '));
        if (!linha) continue;
        try {
          tratarEvento(JSON.parse(linha.slice(6)));
        } catch {}
      }
    }
  } catch (e) {
    console.warn('SSE caiu, reconectando em 3s', e);
  }
  setStatusConexao(false);
  setTimeout(conectarSSE, 3000);
}

function setStatusConexao(ok) {
  const el = document.getElementById('status-conexao');
  if (ok) {
    el.innerHTML = '<span class="w-2 h-2 rounded-full bg-green-500"></span> conectado';
  } else {
    el.innerHTML = '<span class="w-2 h-2 rounded-full bg-gray-400 animate-pulse"></span> reconectando…';
  }
}

function tratarEvento(ev) {
  if (ev.tipo === 'novo_transbordo') {
    toast(`🔔 ${ev.nome || ev.telefone} aguardando atendimento`, 'transbordo');
    tocarNotificacao();
    carregarConversas();
  } else if (ev.tipo === 'nova_mensagem') {
    if (conversaAtual === ev.telefone) {
      // Append incremental — bem mais rápido que re-fetch da conversa toda.
      // Se atendente subiu pra ler msgs antigas, mantém posição.
      // O envio próprio do atendente já criou a bolha optimistic — não duplica.
      if (ev.origem !== 'humano' || !temBolhaPendente()) {
        appendMensagemIncremental(ev.texto, ev.origem, ev.entregue);
      }
    } else if (ev.origem === 'cliente') {
      toast(`💬 Nova mensagem de ${ev.nome || ev.telefone}`, 'info');
      tocarNotificacao();
    }
    carregarConversas();
  } else if (ev.tipo === 'atendente_assumiu' || ev.tipo === 'bot_devolveu') {
    carregarConversas();
    if (conversaAtual === ev.telefone) abrirConversa(conversaAtual);
  }
}

function temBolhaPendente() {
  return !!document.querySelector('#thread-mensagens [data-temp-id]');
}

function appendMensagemIncremental(texto, origem, entregue) {
  const cont = document.getElementById('thread-mensagens');
  if (!cont) return;
  // Esconde empty state se ainda visível.
  const empty = document.getElementById('empty-state');
  if (empty) empty.classList.add('hidden');
  const queroScroll = estaNoFim();
  // Inserir separador de data se virou outro dia desde a última msg renderizada.
  const agoraISO = new Date().toISOString();
  const ultLabel = ultimoSeparadorLabel();
  const novoLabel = dataLabel(agoraISO);
  if (ultLabel !== novoLabel) {
    cont.appendChild(separadorData(novoLabel));
  }
  const textoLimpo = (texto || '').replace(/<\s*br\s*\/?>/gi, '\n');
  cont.appendChild(bolha(textoLimpo, origem || 'bot', agoraISO, { entregue }));
  if (queroScroll) scrollarFim();
}

function ultimoSeparadorLabel() {
  const sep = document.querySelectorAll('#thread-mensagens > .flex.items-center.justify-center > span');
  return sep.length ? sep[sep.length - 1].textContent : null;
}

// ============================================================
// Tag selector — event delegation
// ============================================================

document.getElementById('tag-selector').addEventListener('click', async (e) => {
  const btn = e.target.closest('button[data-tag]');
  if (!btn || !conversaAtual) return;
  const novaTag = btn.dataset.tag || null; // botão "remover" tem data-tag=""
  btn.disabled = true;
  try {
    await definirTag(conversaAtual, novaTag);
  } catch (err) {
    toast('Erro ao salvar tag: ' + err.message, 'transbordo');
  } finally {
    btn.disabled = false;
  }
});

// ============================================================
// TASK-015: Notas internas
// ============================================================

async function carregarNotas(telefone) {
  const lista = document.getElementById('lista-notas');
  if (!lista) return;
  lista.innerHTML = '<li class="text-xs text-gray-400 italic">Carregando…</li>';
  try {
    const notas = await api(`/admin/notas/${encodeURIComponent(telefone)}`);
    lista.innerHTML = '';
    if (!notas || notas.length === 0) {
      const li = document.createElement('li');
      li.className = 'text-xs text-gray-400 italic';
      li.textContent = 'Nenhuma nota ainda.';
      lista.appendChild(li);
      return;
    }
    for (const n of notas) {
      const li = document.createElement('li');
      li.className = 'bg-yellow-50 border border-yellow-100 rounded-lg px-2.5 py-1.5';
      const hora = n.criado_em
        ? (() => {
            const d = new Date(n.criado_em);
            const dd = String(d.getDate()).padStart(2, '0');
            const mm = String(d.getMonth() + 1).padStart(2, '0');
            const aaaa = d.getFullYear();
            const hh = String(d.getHours()).padStart(2, '0');
            const min = String(d.getMinutes()).padStart(2, '0');
            return `${dd}/${mm}/${aaaa} ${hh}:${min}`;
          })()
        : '';
      li.innerHTML = `
        <p class="text-sm text-gray-800 whitespace-pre-wrap">${escapeHtml(n.texto)}</p>
        <p class="text-[10px] text-gray-400 mt-0.5">${hora}</p>
      `;
      lista.appendChild(li);
    }
  } catch (err) {
    lista.innerHTML = '<li class="text-xs text-red-500">Erro ao carregar notas.</li>';
    console.error('carregarNotas:', err);
  }
}

async function adicionarNota(telefone) {
  const ta = document.getElementById('textarea-nota');
  const btn = document.getElementById('btn-adicionar-nota');
  if (!ta || !btn) return;
  const texto = ta.value.trim();
  if (!texto) { ta.focus(); return; }
  btn.disabled = true;
  try {
    await api(`/admin/notas/${encodeURIComponent(telefone)}`, {
      method: 'POST',
      body: JSON.stringify({ texto }),
    });
    ta.value = '';
    await carregarNotas(telefone);
    toast('Nota adicionada.', 'ok');
  } catch (err) {
    toast('Erro ao salvar nota: ' + err.message, 'transbordo');
  } finally {
    btn.disabled = false;
  }
}

// Toggle abrir/fechar painel de notas
document.getElementById('btn-toggle-notas').addEventListener('click', () => {
  const corpo = document.getElementById('corpo-notas');
  const chevron = document.getElementById('icone-notas-chevron');
  const aberto = !corpo.classList.contains('hidden');
  corpo.classList.toggle('hidden', aberto);
  chevron.classList.toggle('rotate-180', !aberto);
});

// Botão "Adicionar nota"
document.getElementById('btn-adicionar-nota').addEventListener('click', () => {
  if (conversaAtual) adicionarNota(conversaAtual);
});

// Enter no textarea de nota (Shift+Enter = nova linha, Enter = adicionar)
document.getElementById('textarea-nota').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    if (conversaAtual) adicionarNota(conversaAtual);
  }
});

// ============================================================
// Bootstrap
// ============================================================

carregarConversas();
conectarSSE();

// Refresh sidebar a cada 30s pra atualizar horário relativo + casos onde SSE perdeu evento
setInterval(carregarConversas, 30000);
// Refresh apenas dos labels de "agora/5min/etc" a cada 60s sem chamar API
setInterval(() => {
  document.querySelectorAll('#lista-conversas li').forEach(() => {});
  // simples re-render local da lista mantendo dados
  renderListaConversas();
}, 60000);
