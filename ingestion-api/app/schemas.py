from pydantic import BaseModel, Field, HttpUrl

class ArticleIn(BaseModel):
    """A simple, beginner-friendly schema for documents we want to store."""

    title: str = Field(min_length=3, max_length=200)
    url: HttpUrl
    source: str = Field(min_length=2, max_length=80)
    published_date: str = Field(min_length=8, max_length=30)
    text: str = Field(min_length=50, max_length=20000)

class ChatIn(BaseModel):
    message: str = Field(min_length=2, max_length=2000)
