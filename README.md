# Desafio Backend — Catálogo (FastAPI + DynamoDB + SQS + S3)
Este projeto é uma adaptação do desafio new-test-backend-nodejs, originalmente em Node.js com MongoDB.
Aqui, a implementação foi reescrita em Python (FastAPI), substituindo o banco de dados por DynamoDB, e integrando com S3 e SQS.

O objetivo principal é aprender e praticar arquitetura backend em Python, explorando serviços AWS no contexto de um catálogo de produtos, sem fugir do escopo do desafio original.

## Tecnologias & Arquitetura
- **FastAPI** → API REST e validação com Pydantic  
- **DynamoDB** → persistência de produtos e categorias  
- **S3** → armazenamento de catálogo gerado em JSON  
- **SQS** → filas de eventos para atualização/consumo do catálogo  
- **LocalStack** → simulação de AWS local  
- **Docker Compose** → orquestração local do ambiente  
- **Pytest** → testes unitários e integração  

## Fluxo de Desenvolvimento
1. Criar produto/categoria → persiste no DynamoDB
2. Evento enviado para SQS → consumer processa
3. Geração de catálogo consolidado (JSON) → salvo no S3
4. API expõe endpoints para consulta de produtos e categorias

## Requisitos
- Python 3.10+

## Setup rápido
```bash
# Criar e ativar venv
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Variáveis de ambiente (local)
- AWS_ENDPOINT_URL=http://localhost:4566
- AWS_ACCESS_KEY_ID=local
- AWS_SECRET_ACCESS_KEY=local
- AWS_REGION=us-east-1
- DYNAMO_TABLE=my-catalog-table
- S3_BUCKET=catalog-bucket
- SQS_CATALOG_TOPIC=catalog-emit.fifo
- JWT_SECRET=changeme
- JWT_ALGORITHM=HS256

## Ambiente Local (LocalStack + Docker)
```bash
# subir ambiente local
docker-compose up -d

# resetar ambiente
./scripts/reset_localstack.sh
```

## ROdando a API
```bash
uvicorn api.main:app --reload
```
API disponível em:
👉 http://localhost:8000/docs

## Comandos úteis (Futuro)
- `make fmt` — formata código
- `make lint` — lints + mypy
- `make test` — roda testes
- `make integration` — testes de integração
- `make reset` — reseta ambiente local