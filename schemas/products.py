from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class ProductBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=2000)
    price: float = Field(..., ge=0)
    category_id: Optional[str] = Field(None)

    @validator("title")
    def strip_title(cls, v: str) -> str:
        return v.strip()
    
class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=2000)
    price: Optional[float] = Field(None, ge=0)
    category_id: Optional[str] = Field(None)
    version: int = Field(..., ge=1)

class ProductOut(BaseModel):
    id: str
    owner_id: str
    title: str
    description: Optional[str]
    price: float
    category_id: Optional[str]
    version: int
    created_at: str
    updated_at: str
