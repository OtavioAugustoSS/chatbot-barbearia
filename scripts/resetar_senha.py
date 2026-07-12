"""
CLI para resetar a senha de um atendente existente.

Uso:
    python -m scripts.resetar_senha <login>

Pede a nova senha interativamente (getpass, mín. 8 caracteres), igual ao
criar_atendente. Não altera nome, role nem status ativo.
"""
import getpass
import sys

from db.database import SessionLocal
from db.models import Atendente
from api.auth import hash_senha


def main():
    if len(sys.argv) != 2:
        print("Uso: python -m scripts.resetar_senha <login>")
        sys.exit(1)
    login = sys.argv[1].strip().lower()

    sess = SessionLocal()
    try:
        atendente = sess.query(Atendente).filter_by(usuario_login=login).first()
        if not atendente:
            print(f"Erro: login '{login}' não encontrado.")
            sys.exit(1)

        print(f"=== Reset de senha — {atendente.nome} (login={login}, role={atendente.role}) ===")
        senha = getpass.getpass("Nova senha (mín 8 caracteres): ")
        if len(senha) < 8:
            print("Erro: senha precisa de pelo menos 8 caracteres.")
            sys.exit(1)
        confirma = getpass.getpass("Confirme a senha: ")
        if senha != confirma:
            print("Erro: as senhas não conferem.")
            sys.exit(1)

        atendente.senha_hash = hash_senha(senha)
        sess.commit()
        print(f"Senha de '{login}' atualizada com sucesso.")
    finally:
        sess.close()


if __name__ == "__main__":
    main()
