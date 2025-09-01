from fastapi import APIRouter, Depends, HTTPException, status, Path
from typing import List
from uuid import uuid4
from datetime import datetime

from api.deps import get_current_owner, get_settings, get_aws_clients
from schemas.products import ProductCreate, ProductUpdate, ProductOut
from infra import dynamo, sqs as infra_sqs

router = APIRouter()

@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(
    owner_id: str = Path(...),
    payload: ProductCreate = None,
    current_owner: str = Depends(get_current_owner),
    clients = Depends(get_aws_clients)
):
    # Checagem de autorização do owner
    if owner_id != current_owner:
        raise HTTPException(status_code=403, detail="owner incompatível")
    
    # construindo item
    product_id = str(uuid4())
    now = datetime.utcnow().isoformat()
    item = {
        "id": product_id,
        "owner_id": owner_id,
        "title": payload.title,
        "description": payload.description,
        "price": payload.price,
        "category_id": payload.category_id,
        "version": 1,
        "created_at": now,
        "updated_at": now
    }

    try:
        created = dynamo.create_product(clients["dynamo"], clients["settings"].dynamo_table, item)
    except Exception as exc:
        # Dá raise 500 para errors de infra (error de mapeamento)
        raise HTTPException(status_code=500, detail=str(exc))
    
    # publicar evento no SQS
    try:
        infra_sqs.send_catalog_event(
            clients["sqs"],
            clients["settings"].sqs_queue,
            owner_id=owner_id,
            event_type="PRODUCT_CREATED",
            entity_type="PRODUCT",
            entity_id=product_id
        )
    except Exception as exc:
        # política: Item já armazenado no banco - logar e returnar `created` (documentado)
        # Aqui retorna código 201, mas inclui-se um `warning` header/body no app real
        # Por agora, somente logar e processar retornando a entidade `created`
        print("Envio ao SQS falhou:", exc)

    return ProductOut(**created)

@router.get("/products/{product_id}", response_model=ProductOut)
async def get_product(
    owner_id: str = Path(...),
    product_id: str = Path(...),
    current_owner: str = Depends(get_current_owner),
    clients = Depends(get_aws_clients)
):
    if owner_id != current_owner:
        raise HTTPException(status_code=403, detail="owner incompatível")
    
    item = dynamo.get_product(clients["dynamo"], clients["settings"].dynamo_table, owner_id, product_id)
    if not item:
        raise HTTPException(status_code=404, detail="produto não encontrado")
    return ProductOut(**item)

@router.put("/products/{productid}", response_model=ProductOut)
async def update_product(
    owner_id: str = Path(...),
    product_id: str = Path(...),
    payload: ProductUpdate = None,
    current_owner: str = Depends(get_current_owner),
    clients = Depends(get_aws_clients)
):
    if owner_id != current_owner:
        raise HTTPException(status_code=403, detail="owner incompatível")
    
    now = datetime.utcnow().isoformat()
    updates = payload.dict(exclude_unset=True)
    try:
        updated = dynamo.update_product(
            clients["dynamo"],
            clients["settings"].dynamo_table,
            owner_id,
            product_id,
            updates,
            expected_version=payload.version
        )
    except dynamo.ConditionalCheckFailedError:
        raise HTTPException(status_code=409, detail="conflito de versão")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    
    # publicar evento
    try:
        infra_sqs.send_catalog_event(
            clients["sqs"],
            clients["settings"].sqs_queue,
            owner_id=owner_id,
            event_type="PRODUCT_UPDATED",
            entity_type="PRODUCT",
            entity_id=product_id
        )
    except Exception as exc:
        print("Envio ao SQS falhou:", exc)

    return ProductOut(**updated)

@router.delete("/products/{productid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    owner_id: str = Path(...),
    product_id: str = Path(...),
    current_owner: str = Depends(get_current_owner),
    clients = Depends(get_aws_clients)
):
    if owner_id != current_owner:
        raise HTTPException(status_code=403, detail="owner incompatível")
    
    try:
        dynamo.delete_product(clients["dynamo", clients["settings"].dynamo_table, owner_id, product_id])
    except dynamo.NotFoundError:
        raise HTTPException(status_code=404, detail="produto não encontrado")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    
    # publicar evento
    try:
        infra_sqs.send_catalog_event(
            clients["sqs"],
            clients["settings"].sqs_queue,
            owner_id=owner_id,
            event_type="PRODUCT_DELETED",
            entity_type="PRODUCT",
            entity_id=product_id
        )
    except Exception as exc:
        print("Envio ao SQS falhou:", exc)

    return None