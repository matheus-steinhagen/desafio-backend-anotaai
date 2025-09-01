"""
AwsClientFactory
Factory simples para criar clients apontando para endpoint localstack
Retorna
    - dynamo_resource: boto3.resource("dynamodb")
    - s3_client: boto3.client("s3")
    - sqs_client: boto3.client("sqs")
"""

from __future__ import annotations
from typing import Optional
import boto3, logging, os

log = logging.getLogger(__name__)

class AwsClientFactory:
    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        region: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        self.endpoint_url = endpoint_url
        self.region = region
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key

    def _common_kwargs(self):
        kwargs = {"region_name": self.region}

        if self.aws_access_key_id:
            kwargs["aws_access_key_id"] = self.aws_access_key_id

        if self.aws_secret_access_key:
            kwargs["aws_secret_access_key"] = self.aws_secret_access_key

        if self.endpoint_url:
            kwargs["endpoint_url"] = self.endpoint_url

        return kwargs

    def dynamo_client(self):
        """
        Retorna os recursos DynamoDB do boto3 (Nível acima)
        """
        kwargs = self._common_kwargs()
        log.debug("Criando o recurso DynamoDB com kwargs=%s", {k: v for k, v in kwargs.items() if k != "aws_secret_access_key"})
        
        # Os parâmetros do dicionário kwargs são descompactados com o operador **
        #   -> O que significa que cada par chave-valor do dicionário é passado como argumento da função
        return boto3.client("dynamodb", **kwargs)

    def s3_client(self):
        kwargs = self._common_kwargs()
        log.debug("Criando o cliente S3 com kwargs=%s", {k: v for k, v in kwargs.items() if k != "aws_secret_access_key"})
        return boto3.client("s3", **kwargs)

    def sqs_client(self):
        kwargs = self._common_kwargs()
        log.debug("Criando o cliente SQS com kwargs=%s", {k: v for k, v in kwargs.items() if k != "aws_secret_access_key"})
        return boto3.client("sqs", **kwargs)

# Wrappers convenientes para operações S3 comuns
def put_s3_object(s3_client, bucket: str, key: str, data: bytes, content_type: str = "application/json"):
    """
    Armazenar objetos no S3. Retorna a resposta do put_object
    """
    log.debug("put_s3_object bucket=%s key=%s size=%d", bucket, key, len(data))
    return s3_client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)

def get_s3_object(s3_client, bucket: str, key: str):
    """
    Retorna body bytes (ou raise botocore exception)
    """
    resp = s3_client.get_object(Bucket=bucket, Key=key)
    return resp["body"].read()