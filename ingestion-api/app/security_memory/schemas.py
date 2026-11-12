from pydantic import BaseModel, Field
from typing import List, Optional


class MemoryQueryIn(BaseModel):
    query: str = Field(min_length=2, max_length=5000)
    tags: Optional[List[str]] = None
    top_k: Optional[int] = Field(default=None, ge=1, le=25)


class MemoryChunk(BaseModel):
    score: float
    title: str
    source: str
    tags: List[str]
    text: str
    chunk_index: int
    doc_path: str


class MemoryQueryOut(BaseModel):
    query: str
    class_name: str = Field(alias="class")
    top_k: int
    results: List[MemoryChunk]

    class Config:
        populate_by_name = True


class MemoryHealthOut(BaseModel):
    ok: bool
    class_name: str = Field(alias="class")
    weaviate_url: str
    object_count: Optional[int] = None
    note: Optional[str] = None

    class Config:
        populate_by_name = True
