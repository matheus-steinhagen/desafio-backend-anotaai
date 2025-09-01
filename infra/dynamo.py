"""
Auxiliares de wrapper para operações DynamoDB usadas pelo API

Convenções
    - Nome da Partition Key: 'ownerId'
    - Nome da Sort Key: 'sk' (formato: 'PRODUCT#<id>' ou 'CATEGORY#<id>')
    - Itens armazenam os dados principais nos atributos de nível superior (id, ownerId, sk, entityType, version, createdAt, updateAt...)
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import logging
from botocore.exceptions import ClientError

log = logging.getLogger(__name__)

# Domain-style exception for mapping to HTTP codes in API layer
class ConditionalCheckFailedError(Exception):
    pass

class NotFoundError(Exception):
    pass

def _table(dynamo_resource, table_name: str):
    return dynamo_resource.Table(table_name)

# --------------------------------------------------
# Produtos
# --------------------------------------------------

def create_product(dynamo_resource, table_name: str, item: Dict[str, Any]):
    """
    Criar um novo produto na tabela.
    Assumindo que 'item' já contém id, owner_id e campos de versão
    O item será armazenado como estiver
    """
    t = _table(dynamo_resource, table_name)
    sk = f"PRODUCT#{item['id']}"
    db_item = {
        "ownerId": item["owner_id"],
        "sk": sk,
        "id": item["id"],
        "entityType": "PRODUCT",
        "title": item["title"],
        "description": item.get("description"),
        "price": item["price"],
        "category_id": item.get("category_id"),
        "version": int(item.get("version", 1)),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at")
    }
    log.debug("Creating product item: owner=%s id=%s", item["owner_id"], item["id"])
    t.put_item(Item=db_item)
    return db_item

def get_product(dynamo_resource, table_name: str, owner_id: str, product_id: str) -> Optional[Dict[str, Any]]:
    t = _table(dynamo_resource, table_name)
    sk = f"PRODUCT#{product_id}"

    try:
        resp = t.get_item(Key={"ownerId": owner_id, "sk": sk})
    except ClientError as e:
        log.exception("DynamoDB get_item error")
        raise

    item = resp.get("Item")
    return item

def update_product(
    dynamo_resource,
    table_name: str,
    owner_id: str,
    product_id: str,
    updates: Dict[str, Any],
    expected_version: int
) -> Dict[str, Any]:
    """
    Update condicional: só se concretizará se version == expected_version
    Incrementa versão em 1 e atualiza o campo updated_at
    Dá raise ConditionalCheckFailedError na version incompatível
    """
    t = _table(dynamo_resource, table_name)
    sk = f"PRODUCT#{product_id}"

    # Construir expressão de update
    expr_parts = []
    expr_attr_vals = {}
    expr_attr_names = {}

    for i, (k, v) in enumerate(updates.items()):
        # mapear nomes dos campos que estão vindo para os nomes dos atributos do DB (armazena-se title, description, price e category_id)
        attr_name = k
        placeholder = f":v{i}"
        name_placeholder = f"#n{i}"
        expr_parts.append(f"{name_placeholder} = {placeholder}")
        expr_attr_names[name_placeholder] = attr_name
        expr_attr_vals[placeholder] = v

    # Atualizando version e updated_at
    expr_parts.append("version = version + :v_version")
    expr_attr_vals[":v_version"] = 1

    from datetime import datetime

    expr_parts.append("updated_at = :updated_at")
    expr_attr_vals[":updated_at"] = datetime.utcnow().isoformat()

    update_expression = "SET " + ", ".join(expr_parts)

    condition_expression = "attribute_exists(ownerId) AND attribute_exists(sk) AND version = :expected_version"
    expr_attr_vals[":expected_version"] = int(expected_version)

    try:
        resp = t.update_item(
            Key={"ownerId": owner_id, "sk": sk},
            UpdateExpression=update_expression,
            ConditionExpression=condition_expression,
            ExpressionAttributeValues=expr_attr_vals,
            ExpressionAttributeNames=expr_attr_names or None,
            ReturnValues="ALL_NEW"
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        log.exception("DynamoDB update_item failed: %s", code)
        if code in ("ConditionalCheckFailException",):
            raise ConditionalCheckFailedError(str(e))
        raise

    return resp.get("Attributes", {})

def delete_product(dynamo_resource, table_name: str, owner_id: str, product_id: str):
    """
    Deleção do produto.
    Dá Raise NotFoundError e o item não existir
    """
    t = _table(dynamo_resource, table_name)
    sk = f"PRODUCT#{product_id}"
    try:
        t.delete_item(
            Key={"ownerId": owner_id, "sk": sk},
            ConditionExpression="attribute_exists(ownerId) AND attribute_exists(sk)",
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        log.exception("DynamoDB delete_item failed: %s", code)
        if code in ("ConditionalCheckFailedException",):
            raise NotFoundError("product not found")
        raise

# --------------------------------------------------
# Categorias
# --------------------------------------------------

def create_category(dynamo_resource, table_name: str, item: Dict[str, Any]) -> Dict[str, Any]:
    t = _table(dynamo_resource, table_name)
    sk = f"CATEGORY#{item['id']}"
    db_item = {
        "ownerId": item["owner_id"],
        "sk": sk,
        "id": item["id"],
        "entityType": "CATEGORY",
        "title": item.get("title"),
        "description": item.get("description"),
        "version": int(item.get("version", 1)),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
    }
    t.put_item(Item=db_item)
    return db_item

def get_category(dynamo_resource, table_name: str, owner_id: str, category_id: str) -> Optional[Dict[str, Any]]:
    t = _table(dynamo_resource, table_name)
    sk = f"CATEGORY#{category_id}"
    resp = t.get_item(Key={"ownerId": owner_id, "sk": sk})
    return resp.get("Item")

def update_category(
    dynamo_resource,
    table_name: str,
    owner_id: str,
    category_id: str,
    updates: Dict[str, Any],
    expected_version: int,
) -> Dict[str, Any]:
    t = _table(dynamo_resource, table_name)
    sk = f"CATEGORY#{category_id}"

    expr_parts = []
    expr_attr_vals = {}
    expr_attr_names = {}
    for i, (k, v) in enumerate(updates.items()):
        attr_name = k
        placeholder = f":v{i}"
        name_placeholder = f"#n{i}"
        expr_parts.append(f"{name_placeholder} = {placeholder}")
        expr_attr_names[name_placeholder] = attr_name
        expr_attr_vals[placeholder] = v

    expr_parts.append("version = version + :v_version")
    expr_attr_vals[":v_version"] = 1
    from datetime import datetime

    expr_parts.append("updated_at = :updated_at")
    expr_attr_vals[":updated_at"] = datetime.utcnow().isoformat()

    update_expression = "SET " + ", ".join(expr_parts)
    condition_expression = "attribute_exists(ownerId) AND attribute_exists(sk) AND version = :expected_version"
    expr_attr_vals[":expected_version"] = int(expected_version)

    try:
        resp = t.update_item(
            Key={"ownerId": owner_id, "sk": sk},
            UpdateExpression=update_expression,
            ConditionExpression=condition_expression,
            ExpressionAttributeValues=expr_attr_vals,
            ExpressionAttributeNames=expr_attr_names or None,
            ReturnValues="ALL_NEW",
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        log.exception("DynamoDB update_item failed: %s", code)
        if code in ("ConditionalCheckFailedException",):
            raise ConditionalCheckFailedError(str(e))
        raise

    return resp.get("Attributes", {})

def delete_category(dynamo_resource, table_name: str, owner_id: str, category_id: str):
    t = _table(dynamo_resource, table_name)
    sk = f"CATEGORY#{category_id}"
    try:
        t.delete_item(
            Key={"ownerId": owner_id, "sk": sk},
            ConditionExpression="attribute_exists(ownerId) AND attribute_exists(sk)"
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        log.exception("DynamoDB delete_item failed: %s", code)

        if code in ("ConditionalCheckFailedException",):
            raise NotFoundError("category not found")
        raise

def list_products_by_category(dynamo_resource, table_name: str, owner_id: str, category_id: str) -> List[Dict[str, Any]]:
    """
    Busca por todos os produtos do owner filtrando por category_id
    Nota:
        Esta função performa uma query por PK e um FilterExpression;
        Para tabelas com grande volume de dados, considerar modelar com GSI para buscar por categoria
    """
    from boto3.dynamodb.conditions import Attr
    t = _table(dynamo_resource, table_name)
    # Busca por PK (ownerId)
    resp = t.query(KeyConditionExpression="ownerID = :owner", ExpressionAttributeValues={":owner": owner_id})
    items = resp.get("Items", [])
    # Filtra localmente (ou via FilterExpression); filtra-se aqui por simplicidade
    linked = [it for it in items if it.get("entityType") == "PRODUCT" and it.get("category_id") == category_id]
    return linked