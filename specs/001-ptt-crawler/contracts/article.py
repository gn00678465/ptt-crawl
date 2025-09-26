from dataclasses import dataclass
from datetime import datetime

@dataclass
class Article:
    """Data contract representing a single PTT article."""
    category: str | None
    author: str | None
    title: str
    publish_date: datetime
    content: str
    url: str
