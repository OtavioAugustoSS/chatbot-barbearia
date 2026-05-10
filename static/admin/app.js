// Painel atendente — Barbearia Bolshoi
// Usa fetch + EventSource. Sem build, sem framework.

const TOKEN = localStorage.getItem('token');
const ATENDENTE_ID = parseInt(localStorage.getItem('atendente_id') || '0');
const ATENDENTE_NOME = localStorage.getItem('atendente_nome') || '';

if (!TOKEN) {
  window.location.href = '/static/admin/login.html';
}

document.getElementById('nome-atendente').textContent = ATENDENTE_NOME;

document.getElementById('btn-sair').addEventListener('click', () => {
  localStorage.clear();
  window.location.href = '/static/admin/login.html';
});

let conversaAtual = null;
let conversas = [];

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

function toast(texto) {
  const el = document.getElementById('toast');
  el.textContent = texto;
  el.classList.remove('hidden');
  setTimeout(() => el.classList.add('hidden'), 4000);
}

function tocarBeep() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const o = ctx.createOscillator();
    o.type = 'sine';
    o.frequency.value = 880;
    o.connect(ctx.destination);
    o.start();
    setTimeout(() => { o.stop(); ctx.close(); }, 150);
  } catch (e) { /* ignora */ }
}

function renderListaConversas() {
  const filtro = document.getElementById('filtro').value.toLowerCase().trim();
  const ul = document.getElementById('lista-conversas');
  ul.innerHTML = '';

  const visiveis = conversas.filter(c => {
    if (!filtro) return true;
    return (c.nome || '').toLowerCase().includes(filtro) || c.telefone.includes(filtro);
  });

  for (const c of visiveis) {
    const li = document.createElement('li');
    li.className = `px-3 py-2 border-b cursor-pointer hover:bg-gray-50 ${conversaAtual === c.telefone ? 'bg-amber-50' : ''}`;

    let badge = '';
    if (c.aguardando_humano) badge = '<span class="inline-block w-2 h-2 bg-red-500 rounded-full mr-2 animate-pulse"></span>';
    else if (c.assumida_por_mim) badge = '<span class="inline-block w-2 h-2 bg-green-500 rounded-full mr-2"></span>';
    else if (c.atendente_id) badge = '<span class="inline-block w-2 h-2 bg-gray-400 rounded-full mr-2"></span>';
    else badge = '<span class="inline-block w-2 h-2 bg-blue-400 rounded-full mr-2"></span>';

    let etiqueta = '';
    if (c.aguardando_humano) etiqueta = '<span class="text-[10px] uppercase font-bold text-red-600">Aguardando</span>';
    else if (c.assumida_por_mim) etiqueta = '<span class="text-[10px] uppercase font-bold text-green-700">Eu</span>';
    else if (c.atendente_id) etiqueta = '<span class="text-[10px] uppercase font-bold text-gray-500">Outro atendente</span>';
    else etiqueta = '<span class="text-[10px] uppercase font-bold text-blue-600">Bot</span>';

    li.innerHTML = `
      <div class="flex items-center justify-between">
        <span class="font-medium text-sm text-gray-800 truncate">${badge}${escapeHtml(c.nome || c.telefone)}</span>
      </div>
      <div class="flex items-center justify-between mt-1">
        <span class="text-xs text-gray-500">${escapeHtml(c.telefone)}</span>
        ${etiqueta}
      </div>
    `;
    li.addEventListener('click', () => abrirConversa(c.telefone));
    ul.appendChild(li);
  }
}

async function carregarConversas() {
  try {
    conversas = await api('/admin/conversas');
    renderListaConversas();
  } catch (e) { console.error(e); }
}

async function abrirConversa(telefone) {
  conversaAtual = telefone;
  renderListaConversas();
  try {
    const data = await api(`/admin/conversa/${encodeURIComponent(telefone)}`);
    renderThread(data);
  } catch (e) { console.error(e); }
}

function renderThread(data) {
  const u = data.usuario;
  document.getElementById('thread-header').classList.remove('hidden');
  document.getElementById('thread-nome').textContent = u.nome || u.telefone;
  document.getElementById('thread-telefone').textContent = u.telefone;

  const status = document.getElementById('thread-status');
  const btnAssumir = document.getElementById('btn-assumir');
  const btnDevolver = document.getElementById('btn-devolver');
  const footer = document.getElementById('thread-footer');

  btnAssumir.classList.add('hidden');
  btnDevolver.classList.add('hidden');
  footer.classList.add('hidden');

  if (u.atendente_id === ATENDENTE_ID) {
    status.textContent = 'Você está atendendo essa conversa.';
    status.className = 'text-xs mt-1 text-green-700';
    btnDevolver.classList.remove('hidden');
    footer.classList.remove('hidden');
  } else if (u.atendente_id) {
    status.textContent = `Conversa atendida por outro atendente (id=${u.atendente_id}).`;
    status.className = 'text-xs mt-1 text-gray-500';
  } else if (u.aguardando_humano) {
    status.textContent = 'Cliente aguardando atendente humano.';
    status.className = 'text-xs mt-1 text-red-600 font-semibold';
    btnAssumir.classList.remove('hidden');
  } else if (u.bot_ativo) {
    status.textContent = 'Bot ativo. Você pode assumir a conversa se quiser.';
    status.className = 'text-xs mt-1 text-blue-600';
    btnAssumir.classList.remove('hidden');
  } else {
    status.textContent = 'Bot inativo, sem atendente designado.';
    status.className = 'text-xs mt-1 text-gray-500';
    btnAssumir.classList.remove('hidden');
  }

  const cont = document.getElementById('thread-mensagens');
  cont.innerHTML = '';
  for (const m of data.mensagens) {
    if (m.cliente) {
      cont.appendChild(bolha(m.cliente, 'cliente', m.criado_em));
    }
    if (m.resposta) {
      cont.appendChild(bolha(m.resposta.replace(/<\s*br\s*\/?>/gi, '\n'), m.origem, m.criado_em));
    }
  }
  cont.scrollTop = cont.scrollHeight;
}

function bolha(texto, origem, criado_em) {
  const div = document.createElement('div');
  let cls = '';
  let label = '';
  if (origem === 'cliente') {
    cls = 'bg-white border self-start';
    label = 'Cliente';
  } else if (origem === 'humano') {
    cls = 'bg-green-100 border-green-200 self-end ml-auto';
    label = 'Atendente';
  } else {
    cls = 'bg-amber-50 border-amber-200 self-end ml-auto';
    label = 'Bot';
  }
  div.className = `max-w-md px-3 py-2 rounded-lg shadow-sm border ${cls} flex flex-col`;
  const ts = criado_em ? new Date(criado_em).toLocaleString('pt-BR') : '';
  div.innerHTML = `
    <span class="text-[10px] uppercase font-bold text-gray-500 mb-1">${label}</span>
    <span class="text-sm whitespace-pre-wrap text-gray-800">${escapeHtml(texto)}</span>
    <span class="text-[10px] text-gray-400 mt-1">${ts}</span>
  `;
  return div;
}

function escapeHtml(s) {
  return (s || '').replace(/[&<>"']/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
}

document.getElementById('filtro').addEventListener('input', renderListaConversas);

document.getElementById('btn-assumir').addEventListener('click', async () => {
  if (!conversaAtual) return;
  try {
    await api(`/admin/assumir/${encodeURIComponent(conversaAtual)}`, { method: 'POST' });
    await carregarConversas();
    await abrirConversa(conversaAtual);
  } catch (e) { alert('Erro ao assumir: ' + e.message); }
});

document.getElementById('btn-devolver').addEventListener('click', async () => {
  if (!conversaAtual) return;
  if (!confirm('Devolver essa conversa para a IA? O cliente será avisado.')) return;
  try {
    await api(`/admin/devolver/${encodeURIComponent(conversaAtual)}`, { method: 'POST' });
    await carregarConversas();
    await abrirConversa(conversaAtual);
  } catch (e) { alert('Erro ao devolver: ' + e.message); }
});

document.getElementById('form-enviar').addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!conversaAtual) return;
  const input = document.getElementById('texto-msg');
  const texto = input.value.trim();
  if (!texto) return;
  try {
    await api(`/admin/enviar/${encodeURIComponent(conversaAtual)}`, {
      method: 'POST',
      body: JSON.stringify({ texto }),
    });
    input.value = '';
    await abrirConversa(conversaAtual);
  } catch (e) { alert('Erro ao enviar: ' + e.message); }
});

// SSE: EventSource não suporta header Authorization → passamos token na query.
// Backend aceita os dois (Bearer header padrão; query como fallback simples).
// Implementação atual exige header → fallback: usar fetch+ReadableStream.
async function conectarSSE() {
  try {
    const res = await fetch('/admin/eventos/stream', { headers: headersAuth() });
    if (!res.ok || !res.body) return;
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const linhas = buffer.split('\n\n');
      buffer = linhas.pop() || '';
      for (const bloco of linhas) {
        const linha = bloco.split('\n').find(l => l.startsWith('data: '));
        if (!linha) continue;
        try {
          const evento = JSON.parse(linha.slice(6));
          tratarEvento(evento);
        } catch {}
      }
    }
  } catch (e) {
    console.warn('SSE caiu, reconectando em 3s...', e);
    setTimeout(conectarSSE, 3000);
  }
}

function tratarEvento(ev) {
  if (ev.tipo === 'novo_transbordo') {
    toast(`🔔 Novo cliente aguardando: ${ev.nome || ev.telefone}`);
    tocarBeep();
    carregarConversas();
  } else if (ev.tipo === 'nova_mensagem') {
    if (conversaAtual === ev.telefone) abrirConversa(ev.telefone);
    carregarConversas();
  } else if (ev.tipo === 'atendente_assumiu' || ev.tipo === 'bot_devolveu') {
    carregarConversas();
    if (conversaAtual === ev.telefone) abrirConversa(ev.telefone);
  }
}

carregarConversas();
conectarSSE();
setInterval(carregarConversas, 30000);
