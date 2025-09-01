from fastapi import APIRouter, Depends, HTTPException, status, Path
from typing import List
from uuid import uuid4
from datetime import datetime

from api.deps import get_current_owner, get_settings, get_aws_clients
from schemas.categories import CategoryCreate, CategoryUpdate, CategoryOut
from infra import dynamo, sqs as infra_sqs

router = APIRouter()

@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    owner_id: str = Path(...),
    payload: CategoryCreate = None,
    current_owner: str = Depends(get_current_owner),
    clients = Depends(get_aws_clients),
):
    if owner_id != current_owner:
        raise HTTPException(status_code=403, detail="owner mismatch")

    category_id = str(uuid4())
    now = datetime.utcnow().isoformat()
    item = {
        "id": category_id,
        "owner_id": owner_id,
        "title": payload.title,
        "description": payload.description,
        "version": 1,
        "created_at": now,
        "updated_at": now,
    }

    try:
        created = dynamo.create_category(clients["dynamo"], clients["settings"].dynamo_table, item)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    try:
        infra_sqs.send_catalog_event(
            clients["sqs"],
            clients["settings"].sqs_queue,
            owner_id=owner_id,
            event_type="CATEGORY_CREATED",
            entity_type="CATEGORY",
            entity_id=category_id,
        )
    except Exception as exc:
        print("SQS send failed:", exc)

    return CategoryOut(**created)


@router.get("/categories/{category_id}", response_model=CategoryOut)
async def get_category(
    owner_id: str = Path(...),
    category_id: str = Path(...),
    current_owner: str = Depends(get_current_owner),
    clients = Depends(get_aws_clients),
):
    if owner_id != current_owner:
        raise HTTPException(status_code=403, detail="owner mismatch")

    item = dynamo.get_category(clients["dynamo"], clients["settings"].dynamo_table, owner_id, category_id)
    if not item:
        raise HTTPException(status_code=404, detail="category not found")
    return CategoryOut(**item)


@router.put("/categories/{category_id}", response_model=CategoryOut)
async def update_category(
    owner_id: str = Path(...),
    category_id: str = Path(...),
    payload: CategoryUpdate = None,
    current_owner: str = Depends(get_current_owner),
    clients = Depends(get_aws_clients),
):
    if owner_id != current_owner:
        raise HTTPException(status_code=403, detail="owner mismatch")

    updates = payload.dict(exclude_unset=True)
    try:
        updated = dynamo.update_category(
            clients["dynamo"],
            clients["settings"].dynamo_table,
            owner_id,
            category_id,
            updates,
            expected_version=payload.version,
        )
    except dynamo.ConditionalCheckFailedError:
        raise HTTPException(status_code=409, detail="version conflict")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    try:
        infra_sqs.send_catalog_event(
            clients["sqs"],
            clients["settings"].sqs_queue,
            owner_id=owner_id,
            event_type="CATEGORY_UPDATED",
            entity_type="CATEGORY",
            entity_id=category_id,
        )
    except Exception as exc:
        print("SQS send failed:", exc)

    return CategoryOut(**updated)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    owner_id: str = Path(...),
    category_id: str = Path(...),
    current_owner: str = Depends(get_current_owner),
    clients = Depends(get_aws_clients),
):
    if owner_id != current_owner:
        raise HTTPException(status_code=403, detail="owner mismatch")

    # business check: forbid deletion if products exist in category
    try:
        linked = dynamo.list_products_by_category(
            clients["dynamo"],
            clients["settings"].dynamo_table,
            owner_id,
            category_id,
        )
        if linked:
            raise HTTPException(status_code=409, detail="category has linked products")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    try:
        dynamo.delete_category(clients["dynamo"], clients["settings"].dynamo_table, owner_id, category_id)
    except dynamo.NotFoundError:
        raise HTTPException(status_code=404, detail="category not found")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    try:
        infra_sqs.send_catalog_event(
            clients["sqs"],
            clients["settings"].sqs_queue,
            owner_id=owner_id,
            event_type="CATEGORY_DELETED",
            entity_type="CATEGORY",
            entity_id=category_id,
        )
    except Exception as exc:
        print("SQS send failed:", exc)

    return None