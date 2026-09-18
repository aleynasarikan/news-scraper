"""
    Pydantic models for Google News scraper.
"""

from datetime import datetime

from pydantic import BaseModel


class Article(BaseModel):
    title: str | None
    url: str | None
    source: str | None = None
    published_at: datetime | None = None
    relative_time: str | None = None
    authors: str | None = None
    image_url: str | None = None
    topic_id: str | None = None
