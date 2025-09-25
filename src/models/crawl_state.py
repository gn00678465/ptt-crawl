"""CrawlState data model.

This module defines the CrawlState data class and status enum.
"""
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class CrawlStatus(Enum):
    """爬取狀態枚舉."""

    IDLE = "idle"
    CRAWLING = "crawling"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"

    def __str__(self) -> str:
        """Return string representation of status."""
        return self.value

    @classmethod
    def from_string(cls, status: str) -> "CrawlStatus":
        """Create status from string."""
        for item in cls:
            if item.value == status.lower():
                return item
        raise ValueError(f"無效的爬取狀態: {status}")


@dataclass
class CrawlState:
    """爬取狀態資料模型."""

    id: int
    board: str
    last_crawl_time: Optional[datetime]
    last_page_crawled: int
    processed_urls: list[str]
    failed_urls: list[str]
    retry_count: int
    max_retries: int
    status: CrawlStatus
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        """Validate crawl state data after initialization."""
        self._validate_board()
        self._validate_retry_counts()
        self._validate_urls()
        self._validate_dates()

    def _validate_board(self) -> None:
        """Validate board name."""
        if not self.board or not self.board.strip():
            raise ValueError("看板名稱不可為空")

        if len(self.board) > 50:
            raise ValueError("看板名稱長度不可超過 50 字符")

        # PTT board naming rules
        if not re.match(r"^[a-zA-Z0-9]+$", self.board):
            raise ValueError("看板名稱必須符合 PTT 看板命名規則")

    def _validate_retry_counts(self) -> None:
        """Validate retry count constraints."""
        if self.retry_count < 0:
            raise ValueError("重試次數不可為負數")

        if self.max_retries < 0:
            raise ValueError("最大重試次數不可為負數")

        if self.retry_count > self.max_retries:
            raise ValueError("重試次數不可超過最大重試次數")

    def _validate_urls(self) -> None:
        """Validate URL lists."""
        # Validate processed URLs
        for url in self.processed_urls:
            if not self._is_valid_url(url):
                raise ValueError(f"無效的已處理 URL: {url}")

        # Validate failed URLs
        for url in self.failed_urls:
            if not self._is_valid_url(url):
                raise ValueError(f"無效的失敗 URL: {url}")

    def _validate_dates(self) -> None:
        """Validate date constraints."""
        if self.last_crawl_time and self.last_crawl_time > datetime.now():
            raise ValueError("最後爬取時間不可晚於當前時間")

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid."""
        if not url or not url.strip():
            return False

        # Basic URL validation
        url_pattern = r"^https?://[^\s]+$"
        return bool(re.match(url_pattern, url))

    def to_dict(self) -> dict:
        """Convert crawl state to dictionary."""
        return {
            "id": self.id,
            "board": self.board,
            "last_crawl_time": self.last_crawl_time.isoformat() if self.last_crawl_time else None,
            "last_page_crawled": self.last_page_crawled,
            "processed_urls": self.processed_urls,
            "failed_urls": self.failed_urls,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "status": self.status.value,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CrawlState":
        """Create crawl state from dictionary."""
        return cls(
            id=data["id"],
            board=data["board"],
            last_crawl_time=(
                datetime.fromisoformat(data["last_crawl_time"])
                if data.get("last_crawl_time")
                else None
            ),
            last_page_crawled=data["last_page_crawled"],
            processed_urls=data.get("processed_urls", []),
            failed_urls=data.get("failed_urls", []),
            retry_count=data["retry_count"],
            max_retries=data["max_retries"],
            status=CrawlStatus.from_string(data["status"]),
            error_message=data.get("error_message"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )

    def add_processed_url(self, url: str) -> None:
        """Add URL to processed list."""
        if not self._is_valid_url(url):
            raise ValueError(f"無效的 URL: {url}")

        if url not in self.processed_urls:
            self.processed_urls.append(url)
            self.updated_at = datetime.now()

    def add_failed_url(self, url: str) -> None:
        """Add URL to failed list."""
        if not self._is_valid_url(url):
            raise ValueError(f"無效的 URL: {url}")

        if url not in self.failed_urls:
            self.failed_urls.append(url)
            self.updated_at = datetime.now()

    def remove_failed_url(self, url: str) -> bool:
        """Remove URL from failed list."""
        if url in self.failed_urls:
            self.failed_urls.remove(url)
            self.updated_at = datetime.now()
            return True
        return False

    def increment_retry_count(self) -> None:
        """Increment retry count."""
        if self.retry_count < self.max_retries:
            self.retry_count += 1
            self.updated_at = datetime.now()
        else:
            raise ValueError("已達到最大重試次數")

    def reset_retry_count(self) -> None:
        """Reset retry count to zero."""
        self.retry_count = 0
        self.updated_at = datetime.now()

    def is_url_processed(self, url: str) -> bool:
        """Check if URL has been processed."""
        return url in self.processed_urls

    def is_url_failed(self, url: str) -> bool:
        """Check if URL has failed."""
        return url in self.failed_urls

    def get_unprocessed_urls(self, all_urls: list[str]) -> list[str]:
        """Get list of unprocessed URLs from a given list."""
        return [url for url in all_urls if not self.is_url_processed(url)]

    def can_retry(self) -> bool:
        """Check if crawl can be retried."""
        return self.status == CrawlStatus.ERROR and self.retry_count < self.max_retries

    def set_error(self, error_message: str) -> None:
        """Set error status and message."""
        self.status = CrawlStatus.ERROR
        self.error_message = error_message
        self.updated_at = datetime.now()

    def clear_error(self) -> None:
        """Clear error status and message."""
        if self.status == CrawlStatus.ERROR:
            self.status = CrawlStatus.IDLE
            self.error_message = None
            self.updated_at = datetime.now()

    def set_completed(self) -> None:
        """Set status to completed."""
        self.status = CrawlStatus.COMPLETED
        self.last_crawl_time = datetime.now()
        self.updated_at = datetime.now()
        self.clear_error()

    def get_success_rate(self) -> float:
        """Get crawling success rate."""
        total_urls = len(self.processed_urls) + len(self.failed_urls)
        if total_urls == 0:
            return 0.0

        return (len(self.processed_urls) / total_urls) * 100.0

    def get_statistics(self) -> dict:
        """Get crawl state statistics."""
        return {
            "total_processed": len(self.processed_urls),
            "total_failed": len(self.failed_urls),
            "success_rate": self.get_success_rate(),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "last_crawl_time": self.last_crawl_time,
            "status": self.status.value,
        }
