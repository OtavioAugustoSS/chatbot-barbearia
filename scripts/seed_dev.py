"""
seed_dev.py — dados de demonstração para o MODO DEV (rodando sem .env).

Chamado automaticamente por main.py quando config.MODO_DEV é True. Idempotente:
cada bloco só insere se a tabela correspondente estiver vazia, então re-boots não
duplicam dados e um banco já populado nunca é alterado.

Guard duro: nunca roda com APP_ENV=production.
"""
import logging

from core import config
from db.models import Atendente, Barbeiro, CannedResponse, Horario, Label, Servico
from scripts.seed_horarios import _HORARIOS_SEED

log = logging.getLogger("barbearia.seed_dev")

SENHA_DEMO = "admin123"  # SÓ existe em modo dev; produção usa scripts/criar_atendente.py


def seed_demo(session_factory=None) -> None:
    if config.APP_ENV == "production":
        return
    if session_factory is None:
        from db.database import SessionLocal

        session_factory = SessionLocal

    db = session_factory()
    try:
        if db.query(Servico).count() == 0:
            corte = Servico(nome_servico="Corte Masculino", preco=45.00, tempo_estimado_minutos=40,
                            categoria="barbearia", descricao="Corte na tesoura ou máquina, com finalização.")
            barba = Servico(nome_servico="Barba Completa", preco=35.00, tempo_estimado_minutos=30,
                            categoria="barbearia", descricao="Barba desenhada com toalha quente e navalha.")
            combo = Servico(nome_servico="Combo Corte + Barba", preco=70.00, tempo_estimado_minutos=70,
                            categoria="barbearia", descricao=None)  # descricao None de propósito (exercita formatação)
            pigmentacao = Servico(nome_servico="Pigmentação", preco=25.00, tempo_estimado_minutos=20,
                                  categoria="barbearia", descricao="Disfarce de falhas em barba ou cabelo.")
            limpeza = Servico(nome_servico="Limpeza de Pele", preco=80.00, tempo_estimado_minutos=50,
                              categoria="estetica", descricao="Limpeza profunda com extração e hidratação.")
            sobrancelha = Servico(nome_servico="Design de Sobrancelha", preco=20.00, tempo_estimado_minutos=15,
                                  categoria="estetica", descricao="Design na pinça ou navalha.")
            db.add_all([corte, barba, combo, pigmentacao, limpeza, sobrancelha])

            if db.query(Barbeiro).count() == 0:
                fred = Barbeiro(nome="Fred", dias_trabalho="terça a sábado",
                                servicos=[corte, barba, combo, pigmentacao])
                joao = Barbeiro(nome="João Pedro", dias_trabalho="segunda a sexta",
                                servicos=[corte, barba, combo])
                isabella = Barbeiro(nome="Isabella", dias_trabalho="terça a sábado",
                                    servicos=[limpeza, sobrancelha])
                db.add_all([fred, joao, isabella])

        if db.query(Horario).count() == 0:
            for dia, horario in _HORARIOS_SEED.items():
                if horario is None:
                    db.add(Horario(dia_semana=dia, abertura=None, fechamento=None, fechado=True))
                else:
                    db.add(Horario(dia_semana=dia, abertura=horario[0], fechamento=horario[1], fechado=False))

        if config.MODO_HIBRIDO:
            if db.query(Label).count() == 0:
                db.add_all([
                    Label(nome="VIP", cor="#F59E0B", descricao="Cliente frequente"),
                    Label(nome="Novo cliente", cor="#10B981", descricao="Primeira visita"),
                ])
            if db.query(CannedResponse).count() == 0:
                db.add(CannedResponse(
                    atalho="/horario",
                    texto="Nosso horário: segunda 14h-21h, terça a sexta 9h-21h, sábado 9h-18h. Domingo fechado.",
                    atendente_id=None,
                ))
            if db.query(Atendente).count() == 0:
                from api.auth import hash_senha

                db.add(Atendente(
                    nome="Admin Demo",
                    usuario_login="admin",
                    senha_hash=hash_senha(SENHA_DEMO),
                    ativo=True,
                ))
                log.warning("Atendente demo criado: login 'admin' / senha '%s' (APENAS modo dev).", SENHA_DEMO)

        db.commit()
        log.info("Seed de dados demo aplicado (blocos vazios populados).")
    except Exception:
        db.rollback()
        log.exception("Falha ao aplicar seed demo — seguindo sem dados de demonstração.")
    finally:
        db.close()
