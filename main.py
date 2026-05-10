import logging
import os
from fastapi import FastAPI
from api import webhook
from db.database import engine, Base

# Logging estruturado: substitui prints espalhados.
# LOG_LEVEL configurável via env (default INFO; DEBUG mostra payload IA).
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# SQLAlchemy cria tabelas que ainda não existem no MySQL (porta 3306).
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Barbearia Bot API",
    description="Motor de conversação de Whatsapp usando NVIDIA NIM (Llama 3.1 70B) e FastAPI"
)

# Inclui as rotas do webhook no caminho raiz
app.include_router(webhook.router)

@app.get("/")
def read_root():
    return {"status": "Online", "mensagem": "API do Bot da Barbearia rodando perfeitamente!"}

if __name__ == "__main__":
    import uvicorn
    # Inicializa o servidor Uvicorn se for rodado diretamente (python main.py)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
