from fastapi import FastAPI

from api.routers import products, categories
from api.deps import get_settings, get_aws_clients

app = FastAPI(title="Desafio Backend Anota Aí!")

@app.on_event("startup")
async def startup():
    # carrega settings e inicializa clients AWS (se necessário)
    settings = get_settings()
    # get_aws_clients(settings) realiza side-effects de inicialização se preciso
    get_aws_clients(settings)

app.include_router(products.router, prefix="/owners/{owner_id}", tags=["products"])
app.include_router(categories.router, prefix="/owners/{owner_id}", tags=["categories"])

@app.get("/")
async def health():
    return {"status": "ok"}