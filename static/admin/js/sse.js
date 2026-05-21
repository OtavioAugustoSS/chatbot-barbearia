(function() {
  let _conectando = false;

  function _setStatus(ok) {
    const dot   = document.getElementById('conn-status-dot');
    const label = document.getElementById('conn-status-label');
    if (dot) {
      dot.className = ok
        ? 'w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0'
        : 'w-2 h-2 rounded-full bg-gray-500 animate-pulse flex-shrink-0';
    }
    if (label) label.textContent = ok ? 'Conectado' : 'Reconectando…';
  }

  async function conectar() {
    if (_conectando) return;
    _conectando = true;
    _setStatus(false);
    try {
      const res = await fetch('/admin/eventos/stream', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (res.status === 401) {
        localStorage.clear();
        location.href = '/static/admin/login.html';
        return;
      }
      if (!res.ok || !res.body) {
        _conectando = false;
        setTimeout(conectar, 3000);
        return;
      }
      _setStatus(true);
      const reader  = res.body.getReader();
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
            const ev = JSON.parse(linha.slice(6));
            document.dispatchEvent(new CustomEvent(`sse:${ev.tipo}`, { detail: ev }));
          } catch(_) {}
        }
      }
    } catch(e) {
      console.warn('[SSE] caiu:', e);
    }
    _setStatus(false);
    _conectando = false;
    setTimeout(conectar, 3000);
  }

  window.sse = { conectar };
})();
