from fastapi import FastAPI
from api import webhook
from db.database import engine, Base

# Ao rodar esse comando, o SQLAlchemy verifica as tabelas criadas no models.py
# e, se não existirem no seu Banco MySQL (da porta 3306), ele as cria!
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
