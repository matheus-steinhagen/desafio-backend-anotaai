from typing import Dict, Any
import os
from pydantic import BaseSettings, Field
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Settings
class Settings(BaseSettings):
    aws_endpoint_url: str = Field(..., env="AWS_ENDPOINT_URL")
    aws_region: str = Field("us-east-1", env="AWS_REGION")
    dynamo_table: str = Field("my-catalog-table", env="DYNAMO_TABLE")
    s3_bucket: str = Field("catalog-bucket", env="S3_BUCKET")
    sqs_queue: str = Field("catalog-emit.fifo", env="SQS_CATALOG_TOPIC")
    jwt_secret: str = Field("changeme", env="JWT_SECRET")
    jwt_alg: str = Field("HS256", env="JWT_ALGORITHM")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

_settings: Settings | None = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

# Simple JWT auth dependency
bearer_scheme = HTTPBearer(auto_error=False)

def get_current_owner(
        creds: HTTPAuthorizationCredentials = Security(bearer_scheme),
        settings: Settings = Depends(get_settings)
) -> str:
    """
    Espera-se um JWT cujo payload contem 'sub' ou 'owner_id' identificando o owner
    Raises 401 se for inválido ou inexistente
    """
    if creds is None:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    token = creds.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secrets, algorithms=[settings.jwt_alq])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    owner_id = payload.get("owner_id") or payload.get("sub")
    if not owner_id:
        raise HTTPException(status_code=401, detail="token missing owner info")
    return owner_id

# AWS clients factory (wrapper)
_aws_clients: Dict[str, Any] | None = None

def get_aws_clients(settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    """
    Inicializa e cacheia AWS clients ou warppers (infra.aws_clients expõe funções construtoras)
    Essa função apenas importa infra.awsclient para evitar dependências pesadas na fase de importação
    """
    global _aws_clients
    if _aws_clients is None:
        # Lazy import para evitar boto3/AWS seja chamada no momento da importação dos módulos
        try:
            from infra.aws_client import AwsClientFactory
        except Exception:
            # Se infra ainda não estiver pronto, retorne configurações básicas
            _aws_clients = {"settings": settings}
            return _aws_clients

        factory = AwsClientFactory(
            endpoint_url=settings.aws_endpoint_url,
            region=settings.aws_region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secrets_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )
        _aws_clients = {
            "settings": settings,
            "dynamo": factory.dynamo_client(),
            "s3": factory.s3_client(),
            "sqs": factory.sqs_client(),
        }
    return _aws_clients