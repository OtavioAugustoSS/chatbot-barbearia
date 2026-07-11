"""
seed_horarios.py — popula a tabela horarios com o calendário fixo da Barbearia Bolshoi.

Fonte original: ai_service._HORARIOS (agora migrado para o banco).
Execute uma vez após rodar TASK005_create_horarios.sql (ou deixar o SQLAlchemy criar a tabela).

Uso:
    python scripts/seed_horarios.py
"""

import sys
import os

# Garante que o diretório raiz do projeto esteja no path para importar db.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal
from db.models import Horario

# B9: fonte única em services/horarios.py — o seed usa o MESMO calendário
# que o fallback da IA e o texto canônico. Nome mantido para compatibilidade.
from services.horarios import HORARIOS_FALLBACK as _HORARIOS_SEED

_NOMES_DIA = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def seed():
    db = SessionLocal()
    try:
        for dia, horario in _HORARIOS_SEED.items():
            if horario is None:
                registro = Horario(
                    dia_semana=dia,
                    abertura=None,
                    fechamento=None,
                    fechado=True,
                )
            else:
                abertura, fechamento = horario
                registro = Horario(
                    dia_semana=dia,
                    abertura=abertura,
                    fechamento=fechamento,
                    fechado=False,
                )

            # merge() = INSERT se não existe, UPDATE se já existe (upsert por PK)
            db.merge(registro)
            nome = _NOMES_DIA[dia]
            status = "FECHADO" if horario is None else f"{horario[0]}–{horario[1]}"
            print(f"  [{dia}] {nome}: {status}")

        db.commit()
        print("\nSeed concluído com sucesso.")
    except Exception as e:
        db.rollback()
        print(f"\nErro durante seed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    print("Populando tabela horarios...\n")
    seed()
