"""
Exclusão de dados pessoais de um cliente (LGPD).

Helper compartilhado entre o endpoint admin (DELETE /admin/cliente/{telefone})
e o fluxo de autoatendimento no webhook ("apagar meus dados" → confirmação
"APAGAR"). Deleção explícita das dependências — robusta mesmo sem FK cascade
no SQLite (dev/testes).
"""
import logging

from sqlalchemy.orm import Session

from db.models import (
    HistoricoConversa,
    MentionNotificacao,
    NotaInterna,
    Usuario,
    usuario_labels,
)

log = logging.getLogger("barbearia.lgpd")


def apagar_dados_cliente(db: Session, telefone: str) -> bool:
    """Apaga o cliente e TODOS os seus dados pessoais.

    Retorna True se o cliente existia (e foi apagado), False caso contrário.
    O commit é responsabilidade DESTA função — chamadores não devem commitar de novo.
    """
    user = db.query(Usuario).filter(Usuario.telefone == telefone).first()
    if not user:
        return False
    db.query(MentionNotificacao).filter(
        MentionNotificacao.telefone_usuario == telefone
    ).delete(synchronize_session=False)
    db.query(NotaInterna).filter(
        NotaInterna.telefone_usuario == telefone
    ).delete(synchronize_session=False)
    db.execute(usuario_labels.delete().where(usuario_labels.c.telefone_usuario == telefone))
    db.query(HistoricoConversa).filter(
        HistoricoConversa.telefone_usuario == telefone
    ).delete(synchronize_session=False)
    db.delete(user)
    db.commit()
    log.info("[LGPD] Dados do cliente %s apagados.", telefone)
    return True
