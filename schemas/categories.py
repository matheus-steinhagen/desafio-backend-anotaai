from pydantic import BaseModel, Field, validator
from typing import Optional

class CategoryBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=2000)
    
    @validator("title")
    def strip_title(cls, v: str) -> str:
        return v.strip()

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=2000)
    version: int = Field(..., ge=1)

class CategoryOut(BaseModel):
    id: str
    owner_id: str
    title: str
    description: Optional[str]
    version: int
    created_at: str
    updated_at: str