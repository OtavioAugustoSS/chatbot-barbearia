"""
limpeza.py — manutenção periódica do banco (P2-3).

Roda como cron/timer. Garante limpeza determinística do que a limpeza
oportunista de 1% em api/webhook.py não cobre de forma confiável:

  1. mensagens_processadas (dedupe): registros têm TTL útil de 1h. Tudo mais
     velho que --dedupe-dias é lixo seguro de remover.
  2. historico_conversas (opcional, opt-in): retenção de dados pessoais.
     O webhook já mantém no máx. 50 msgs/cliente na escrita; este purge
     remove conversas antigas além de --historico-dias para minimização
     de dados (LGPD). DESLIGADO por padrão (0) — é decisão do dono.

Uso:
    python scripts/limpeza.py                      # só dedupe (>=2 dias)
    python scripts/limpeza.py --dedupe-dias 1
    python scripts/limpeza.py --historico-dias 180 # também purga histórico >180d
    python scripts/limpeza.py --dry-run            # mostra o que faria, sem deletar

Cron diário (3h da manhã), exemplo:
    0 3 * * *  cd /opt/barbearia-bot && ./venv/bin/python scripts/limpeza.py >> /var/log/barbearia-limpeza.log 2>&1
"""

import sys
import os
import argparse
import logging
from datetime import datetime, timezone, timedelta

# Garante que o diretório raiz do projeto esteja no path para importar db.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal
from db.models import MensagemProcessada, HistoricoConversa

logging.basicConfig(
    level="INFO",
    format="%(asctime)s [%(levelname)s] limpeza: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("limpeza")


def _purgar(db, model, coluna_data, limite: datetime, dry_run: bool) -> int:
    """Conta e (se não dry-run) deleta registros com coluna_data < limite. Retorna a contagem."""
    q = db.query(model).filter(coluna_data < limite)
    total = q.count()
    if total and not dry_run:
        q.delete(synchronize_session=False)
        db.commit()
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description="Limpeza periódica do banco da Barbearia Bolshoi.")
    parser.add_argument("--dedupe-dias", type=int, default=2,
                        help="Remove mensagens_processadas mais antigas que N dias (default 2).")
    parser.add_argument("--historico-dias", type=int, default=0,
                        help="Remove historico_conversas mais antigo que N dias (0 = desligado).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Apenas reporta as contagens, sem deletar nada.")
    args = parser.parse_args()

    agora = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        lim_dedupe = agora - timedelta(days=args.dedupe_dias)
        n_dedupe = _purgar(db, MensagemProcessada, MensagemProcessada.processada_em, lim_dedupe, args.dry_run)
        verbo = "removeria" if args.dry_run else "removidos"
        log.info("mensagens_processadas: %s %d registro(s) anteriores a %s.",
                 verbo, n_dedupe, lim_dedupe.date().isoformat())

        if args.historico_dias > 0:
            lim_hist = agora - timedelta(days=args.historico_dias)
            n_hist = _purgar(db, HistoricoConversa, HistoricoConversa.criado_em, lim_hist, args.dry_run)
            log.info("historico_conversas: %s %d registro(s) anteriores a %s.",
                     verbo, n_hist, lim_hist.date().isoformat())
        else:
            log.info("historico_conversas: purge desligado (--historico-dias 0).")

        return 0
    except Exception:
        db.rollback()
        log.exception("Falha na limpeza — rollback aplicado.")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
