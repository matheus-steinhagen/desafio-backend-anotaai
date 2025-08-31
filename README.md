# Desafio Backend — Catálogo (FastAPI + DynamoDB + SQS + S3)
Este projeto é uma adaptação do desafio new-test-backend-nodejs, originalmente em Node.js com MongoDB.
Aqui, a implementação foi reescrita em Python (FastAPI), substituindo o banco de dados por DynamoDB, e integrando com S3 e SQS.

O objetivo principal é aprender e praticar arquitetura backend em Python, explorando serviços AWS no contexto de um catálogo de produtos, sem fugir do escopo do desafio original.

## Requisitos
- Python 3.10+

## Setup rápido
```bash
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

## Comandos úteis (Futuro)
- `make fmt` — formata código
- `make lint` — lints + mypy
- `make test` — roda testes
- `make integration` — testes de integração
- `make reset` — reseta ambiente local