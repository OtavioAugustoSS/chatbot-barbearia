"""
Fonte única de horários de funcionamento (B9).

Antes havia TRÊS fontes do mesmo dado que podiam divergir em silêncio:
  1. tabela `horarios` no banco (fonte canônica em runtime);
  2. dict hardcoded `_HORARIOS` em services/ai_service.py (fallback da IA);
  3. texto fixo `_CORPO_HORARIO` em core/respostas_canonicas.py (fallback da FAQ).

Agora o fallback vive apenas aqui (HORARIOS_FALLBACK) e os consumidores derivam
os formatos de que precisam (minutos para a IA, texto <br> para a canônica,
seed para scripts/seed_horarios.py). O cache de leitura do banco também mora
aqui, compartilhado por todos os consumidores.
"""
import logging
import threading
import time

log = logging.getLogger("barbearia.horarios")

# Calendário fixo da Barbearia Bolshoi — ÚNICO fallback quando a tabela
# `horarios` está vazia ou inacessível. weekday(): 0=segunda ... 6=domingo.
# Tupla ("HH:MM", "HH:MM") — None = dia fechado.
HORARIOS_FALLBACK: dict[int, tuple[str, str] | None] = {
    0: ("14:00", "21:00"),  # segunda
    1: ("09:00", "21:00"),  # terça
    2: ("09:00", "21:00"),  # quarta
    3: ("09:00", "21:00"),  # quinta
    4: ("09:00", "21:00"),  # sexta
    5: ("09:00", "18:00"),  # sábado
    6: None,                # domingo (fechado)
}

_DIAS_SEMANA_PT = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


def fallback_em_minutos() -> dict[int, tuple[int, int] | None]:
    """Deriva {dia: (abre_min, fecha_min) | None} de HORARIOS_FALLBACK."""

    def _min(h: str) -> int:
        hh, mm = h.split(":")
        return int(hh) * 60 + int(mm)

    return {
        dia: (None if faixa is None else (_min(faixa[0]), _min(faixa[1])))
        for dia, faixa in HORARIOS_FALLBACK.items()
    }


def corpo_horario_fallback() -> str:
    """Texto <br> do calendário fallback, agrupando dias consecutivos iguais.

    Produz o mesmo formato do antigo texto fixo de respostas_canonicas:
    "Segunda: 14:00 às 21:00<br>Terça a Sexta: 09:00 às 21:00<br>..."
    """
    grupos: list[tuple[int, int, tuple[str, str] | None]] = []
    for dia in range(7):
        faixa = HORARIOS_FALLBACK.get(dia)
        if grupos and grupos[-1][2] == faixa:
            grupos[-1] = (grupos[-1][0], dia, faixa)
        else:
            grupos.append((dia, dia, faixa))

    partes = []
    for inicio, fim, faixa in grupos:
        nome = _DIAS_SEMANA_PT[inicio] if inicio == fim else f"{_DIAS_SEMANA_PT[inicio]} a {_DIAS_SEMANA_PT[fim]}"
        if faixa is None:
            partes.append(f"{nome}: fechado")
        else:
            partes.append(f"{nome}: {faixa[0]} às {faixa[1]}")
    return "*Nosso horário de funcionamento:*<br><br>" + "<br>".join(partes)


# ---------------------------------------------------------------------------
# Cache de leitura da tabela `horarios` (compartilhado IA + canônicas + admin).
# TTL idêntico ao cache de serviços/barbeiros (5 min) para consistência.
# Estrutura: {"data": dict|None, "expira_em": float (epoch seconds)}
# ---------------------------------------------------------------------------
_cache_horarios: dict = {"data": None, "expira_em": 0.0}
_HORARIOS_CACHE_TTL = 300  # 5 minutos
# TD-005: lock para proteger leitura/escrita do cache de módulo em background tasks.
_cache_horarios_lock = threading.Lock()


def carregar_horarios_db() -> dict:
    """
    Retorna dict {dia_semana: Horario} consultando o banco, com cache de 5 min.
    Retorna {} em caso de erro — consumidores usam HORARIOS_FALLBACK.
    Thread-safe via _cache_horarios_lock (TD-005).
    """
    agora = time.time()
    with _cache_horarios_lock:
        if _cache_horarios["data"] is not None and agora < _cache_horarios["expira_em"]:
            return _cache_horarios["data"]

    from db.database import SessionLocal
    from db.models import Horario

    db = SessionLocal()
    try:
        registros = db.query(Horario).all()
        resultado = {r.dia_semana: r for r in registros}
        with _cache_horarios_lock:
            _cache_horarios["data"] = resultado
            _cache_horarios["expira_em"] = agora + _HORARIOS_CACHE_TTL
        return resultado
    except Exception as e:
        log.warning("Falha ao carregar horarios do banco, usando fallback hardcoded: %s", e)
        # Não atualiza o cache em caso de erro — próxima chamada tentará de novo.
        with _cache_horarios_lock:
            return _cache_horarios["data"] if _cache_horarios["data"] is not None else {}
    finally:
        db.close()


def invalidar_cache_horarios() -> None:
    """Zera o cache de horários — a próxima leitura recarrega do banco.
    Chamado pelo endpoint admin de edição de horário (reflete a mudança na hora)."""
    with _cache_horarios_lock:
        _cache_horarios["data"] = None
        _cache_horarios["expira_em"] = 0.0
