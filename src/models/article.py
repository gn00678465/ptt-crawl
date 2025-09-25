"""Article data model.

This module defines the Article data class and validation logic.
"""
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Article:
    """PTT 文章資料模型."""

    id: int
    title: str
    author: str
    board: str
    url: str
    content: Optional[str]
    publish_date: datetime
    crawl_date: datetime
    category: Optional[str]
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        """Validate article data after initialization."""
        self._validate_title()
        self._validate_author()
        self._validate_board()
        self._validate_url()
        self._validate_dates()

    def _validate_title(self) -> None:
        """Validate article title."""
        if not self.title or not self.title.strip():
            raise ValueError("文章標題不可為空")

        if len(self.title) > 500:
            raise ValueError("文章標題長度不可超過 500 字符")

    def _validate_author(self) -> None:
        """Validate author ID."""
        if not self.author or not self.author.strip():
            raise ValueError("作者 ID 不可為空")

        if len(self.author) > 50:
            raise ValueError("作者 ID 長度不可超過 50 字符")

        # Check for special characters
        if not re.match(r"^[a-zA-Z0-9_-]+$", self.author):
            raise ValueError("作者 ID 不可包含特殊字符")

    def _validate_board(self) -> None:
        """Validate board name."""
        if not self.board or not self.board.strip():
            raise ValueError("看板名稱不可為空")

        if len(self.board) > 50:
            raise ValueError("看板名稱長度不可超過 50 字符")

        # PTT board naming rules: alphanumeric characters
        if not re.match(r"^[a-zA-Z0-9]+$", self.board):
            raise ValueError("看板名稱必須符合 PTT 看板命名規則")

    def _validate_url(self) -> None:
        """Validate article URL."""
        if not self.url or not self.url.strip():
            raise ValueError("文章 URL 不可為空")

        if len(self.url) > 500:
            raise ValueError("文章 URL 長度不可超過 500 字符")

        # Check for valid PTT URL format
        ptt_url_pattern = r"^https://www\.ptt\.cc/bbs/[a-zA-Z0-9]+/M\.\d+\.A\.[a-fA-F0-9]+\.html$"
        if not re.match(ptt_url_pattern, self.url):
            raise ValueError("必須為有效的 PTT URL 格式")

    def _validate_dates(self) -> None:
        """Validate publish and crawl dates."""
        if self.publish_date > self.crawl_date:
            raise ValueError("發表時間不可晚於爬取時間")

    def to_dict(self) -> dict:
        """Convert article to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "board": self.board,
            "url": self.url,
            "content": self.content,
            "publish_date": self.publish_date.isoformat(),
            "crawl_date": self.crawl_date.isoformat(),
            "category": self.category,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Article":
        """Create article from dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            author=data["author"],
            board=data["board"],
            url=data["url"],
            content=data.get("content"),
            publish_date=datetime.fromisoformat(data["publish_date"]),
            crawl_date=datetime.fromisoformat(data["crawl_date"]),
            category=data.get("category"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )

    def extract_category_from_title(self) -> Optional[str]:
        """Extract category from article title."""
        # Pattern to match [category] at the beginning of title
        match = re.match(r"^\[([^\]]+)\]", self.title)
        return match.group(1) if match else None

    def is_valid_content(self) -> bool:
        """Check if article has valid content."""
        if not self.content:
            return False

        # Content should not be empty after stripping whitespace
        return bool(self.content.strip())

    def get_content_length(self) -> int:
        """Get content length in characters."""
        return len(self.content) if self.content else 0

    def get_summary(self, max_length: int = 100) -> str:
        """Get article summary."""
        if not self.content:
            return ""

        # Remove markdown headers and clean content
        clean_content = re.sub(r"^#+\s*", "", self.content, flags=re.MULTILINE)
        clean_content = re.sub(r"\n+", " ", clean_content).strip()

        if len(clean_content) <= max_length:
            return clean_content

        return clean_content[:max_length].rstrip() + "..."
