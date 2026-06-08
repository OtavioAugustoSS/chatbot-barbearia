"""Aplica todas as migrations SQL via SQLAlchemy (sem precisar do mysql CLI)."""
import sys
from pathlib import Path

# Garante que o root do projeto está no path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import engine

MIGRATIONS = [
    "TASK001_add_intencao_historico.sql",
    "TASK002_add_ultimo_login_atendente.sql",
    "TASK003_add_criado_em_usuario.sql",
    "TASK004_add_ativo_servico.sql",
    "TASK005_create_horarios.sql",
    "TASK015_create_notas_internas.sql",
    "TASK017_add_tag_usuario.sql",
]

migrations_dir = Path(__file__).parent / "migrations"

with engine.connect() as conn:
    for filename in MIGRATIONS:
        path = migrations_dir / filename
        sql = path.read_text(encoding="utf-8").strip()
        if not sql:
            print(f"  SKIP {filename} (vazio)")
            continue
        try:
            conn.execute(__import__("sqlalchemy").text(sql))
            conn.commit()
            print(f"  OK   {filename}")
        except Exception as e:
            msg = str(e)
            # Coluna/tabela já existe = não é erro
            if "Duplicate column name" in msg or "already exists" in msg or "1060" in msg or "1050" in msg:
                print(f"  SKIP {filename} (já aplicado)")
            else:
                print(f"  FAIL {filename}: {msg}")
                sys.exit(1)

print("\nMigrations concluídas.")
