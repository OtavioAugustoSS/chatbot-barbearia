(function() {
  let _conectando = false;
  let _retryDelay = 1000;   // ms — começa em 1s, dobra até 30s
  let _retryCount = 0;
  const _MAX_DELAY = 30000; // 30s

  function _setConnStatus(state, label) {
    document.dispatchEvent(new CustomEvent('sse:connection_status', { detail: { state, label } }));
  }

  function _setStatus(ok, failed) {
    const dot   = document.getElementById('conn-status-dot');
    const label = document.getElementById('conn-status-label');
    const headerDot = document.getElementById('sse-status-dot');
    if (dot) {
      dot.className = ok ? 'connected' : (failed ? 'failed' : 'connecting');
      dot.style.background = ok ? '' : '';
    }
    if (label) label.textContent = ok ? 'Conectado' : 'Reconectando…';
    if (headerDot) {
      headerDot.classList.remove('reconnecting', 'failed');
      headerDot.style.background = '';
      if (ok) {
        headerDot.style.background = 'var(--success-text)';
      } else if (failed) {
        headerDot.classList.add('failed');
      } else {
        headerDot.classList.add('reconnecting');
      }
    }
    if (ok) {
      _setConnStatus('connected', '');
    } else if (failed) {
      _setConnStatus('offline', 'Offline');
    } else {
      _setConnStatus('reconnecting', 'Reconectando...');
    }
  }

  function _agendarReconexao() {
    // Jitter ±20% para evitar thundering herd com múltiplos atendentes
    const jitter = (_retryDelay * 0.2) * (Math.random() * 2 - 1);
    const delay = Math.round(_retryDelay + jitter);
    _retryCount++;
    console.log(`[SSE] Reconectando em ${delay}ms (tentativa ${_retryCount})`);
    _retryDelay = Math.min(_retryDelay * 2, _MAX_DELAY);
    setTimeout(conectar, delay);
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
        _agendarReconexao();
        return;
      }
      // Conexão bem-sucedida: reset backoff
      _setStatus(true);
      _retryDelay = 1000;
      _retryCount = 0;

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
    const permanentlyFailed = _retryDelay >= _MAX_DELAY;
    _setStatus(false, permanentlyFailed);
    _conectando = false;
    _agendarReconexao();
  }

  window.sse = { conectar };
})();
