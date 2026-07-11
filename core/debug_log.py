"""
Logger único de debug de erros de IA/background (erro_ia_debug.txt).

Antes havia DOIS escritores no mesmo arquivo: um RotatingFileHandler (ai_service)
e um open(..., "a") cru (webhook background task) — o append cru ignorava a
rotação e o arquivo podia crescer sem limite. Agora todo escritor usa este
singleton com rotação (5MB x 3 backups = máx. 20MB em disco).

Nome do arquivo mantido ("erro_ia_debug.txt") para compatibilidade com
monitoramento existente.
"""
import logging
import logging.handlers
import os

_NOME_LOGGER = "barbearia.ai.debug"


def get_debug_logger() -> logging.Logger:
    logger = logging.getLogger(_NOME_LOGGER)
    if not logger.handlers:
        caminho = os.path.normpath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "erro_ia_debug.txt")
        )
        handler = logging.handlers.RotatingFileHandler(
            caminho,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%Y-%m-%dT%H:%M:%S"))
        logger.addHandler(handler)
        logger.setLevel(logging.ERROR)
        logger.propagate = False  # evita duplicar no root logger
    return logger
