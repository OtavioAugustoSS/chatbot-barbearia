"""
CLI para criar um atendente no banco.

Uso:
    python -m scripts.criar_atendente

Pede nome, login e senha interativamente. Senha digitada às escondidas (getpass).
Falha se login já existir (constraint UNIQUE).
"""
import sys
import getpass
from sqlalchemy.exc import IntegrityError

from db.database import SessionLocal
from db.models import Atendente
from api.auth import hash_senha


def main():
    print("=== Criação de Atendente ===")
    nome = input("Nome completo: ").strip()
    if not nome:
        print("Erro: nome obrigatório.")
        sys.exit(1)

    login = input("Usuário de login: ").strip().lower()
    if not login or " " in login:
        print("Erro: login obrigatório, sem espaços.")
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
        novo = Atendente(
            nome=nome,
            usuario_login=login,
            senha_hash=hash_senha(senha),
            ativo=True,
        )
        db.add(novo)
        db.commit()
        db.refresh(novo)
        print(f"Atendente '{novo.nome}' (login={novo.usuario_login}, id={novo.id}) criado com sucesso.")
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
