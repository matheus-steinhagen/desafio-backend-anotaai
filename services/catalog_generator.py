from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types  import TypeDeserializer
from datetime import datetime
from typing import Dict, Any
import boto3

def generate_catalog(dynamo_client: boto3.client, table_name: str, owner_id: str) -> Dict[str, Any]:
    """
    Monta o catálogo consolidado para um owner_id.
    Varre a tabela DynamoDB e organiza products e categories
    """

    # buca todos os itens do owner
    response = dynamo_client.query(
        TableName=table_name,
        KeyConditionExpression=Key("ownerId").eq(owner_id),
        ExpressionAttributeValues={"owner_id": {"S": owner_id}}
    )
    deserializer = TypeDeserializer()
    items = [{k: deserializer.deserialize(v) for k, v in item.items()} for item in response["Items"]]

    categories = [i for i in items if i.get("entityType") == "CATEGORY"]
    products = [i for i in items if i.get("entityType") == "PRODUCT"]

    return {
        "owner_id": owner_id,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "categories": categories,
        "products": products,
    }