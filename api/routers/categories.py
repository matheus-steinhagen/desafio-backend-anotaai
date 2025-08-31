from fastapi import APIRouter, Depends, HTTPException, status, Path
from typing import List
from uuid import uuid4
from datetime import datetime

from api.deps import get_current_owner, get_settings, get_aws_clients
from schemas.categories import CategoryCreate, CategoryUpdate, CategoryOut
from infra import dynamo, sqs as infra_sqs

router = APIRouter()