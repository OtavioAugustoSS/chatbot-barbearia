"""
CLI para criar um atendente no banco.

Uso:
    python -m scripts.criar_atendente            # cria atendente comum
    python -m scripts.criar_atendente --admin    # cria com perfil administrador

Pede nome, login e senha interativamente. Senha digitada às escondidas (getpass).
Falha se login já existir (constraint UNIQUE).
O PRIMEIRO atendente do banco é promovido a admin automaticamente (com aviso) —
sem isso não haveria ninguém capaz de gerenciar os demais (RBAC).
"""
import argparse
import getpass
import re
import sys

from sqlalchemy.exc import IntegrityError

from db.database import SessionLocal
from db.models import Atendente
from api.auth import hash_senha

# Mesmo pattern exigido pelo endpoint POST /admin/atendentes — CLI e API
# aceitam exatamente os mesmos logins.
_PATTERN_LOGIN = re.compile(r"^[a-z0-9_]+$")


def main():
    parser = argparse.ArgumentParser(description="Cria um atendente no banco.")
    parser.add_argument("--admin", action="store_true",
                        help="cria com perfil administrador (gestão de atendentes/horários/LGPD)")
    args = parser.parse_args()

    print("=== Criação de Atendente ===")
    nome = input("Nome completo: ").strip()
    if not nome:
        print("Erro: nome obrigatório.")
        sys.exit(1)

    login = input("Usuário de login: ").strip().lower()
    if not login or not _PATTERN_LOGIN.match(login):
        print("Erro: login obrigatório, apenas letras minúsculas, números e _ (sem espaços).")
        sys.exit(1)

    senha = getpass.getpass("Senha (mín 8 caracteres): ")
    if len(senha) < 8:
        print("Erro: senha precisa ter ao menos 8 caracteres.")
        sys.exit(1)
    senha_confirm = getpass.getpass("Confirme a senha: ")
    if senha != senha_confirm:
        print("Erro: senhas não conferem.")
        sys.exit(1)

    db = SessionLocal()
    try:
        role = "admin" if args.admin else "atendente"
        if role != "admin" and db.query(Atendente).count() == 0:
            role = "admin"
            print("Aviso: primeiro atendente do banco — promovido a ADMIN automaticamente.")

        novo = Atendente(
            nome=nome,
            usuario_login=login,
            senha_hash=hash_senha(senha),
            role=role,
            ativo=True,
        )
        db.add(novo)
        db.commit()
        db.refresh(novo)
        print(f"Atendente '{novo.nome}' (login={novo.usuario_login}, id={novo.id}, role={novo.role}) criado com sucesso.")
    except IntegrityError:
        db.rollback()
        print(f"Erro: login '{login}' já existe.")
        sys.exit(2)
    except Exception as e:
        db.rollback()
        print(f"Erro inesperado: {e}")
        sys.exit(3)
    finally:
        db.close()


if __name__ == "__main__":
    main()
