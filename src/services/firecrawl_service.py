"""Firecrawl API integration service.

This module provides integration with Firecrawl API for web scraping.
"""
import asyncio
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Optional

import aiohttp

from firecrawl import FirecrawlApp

logger = logging.getLogger(__name__)


@dataclass
class FirecrawlResponse:
    """Firecrawl API response."""

    success: bool
    data: dict[str, Any]
    error: Optional[dict[str, Any]] = None
    warning: Optional[str] = None

    @classmethod
    def from_dict(cls, response_data: dict) -> "FirecrawlResponse":
        """Create response from dictionary."""
        return cls(
            success=response_data.get("success", False),
            data=response_data.get("data", {}),
            error=response_data.get("error"),
            warning=response_data.get("warning"),
        )


class FirecrawlError(Exception):
    """Firecrawl API error."""

    def __init__(self, message: str, error_code: str = "UNKNOWN", details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def __str__(self) -> str:
        return f"{self.error_code}: {self.message}"


class FirecrawlService:
    """Firecrawl API 整合服務."""

    def __init__(self, config: dict[str, Any]):
        self.api_url = config.get("api_url")
        self.api_key = config.get("api_key")
        self.timeout = config.get("timeout", 30)
        self.max_retries = config.get("max_retries", 3)

        if not self.api_url:
            raise ValueError("api_url 為必填欄位")

        # Initialize Firecrawl client
        self.client = (
            FirecrawlApp(api_url=self.api_url, api_key=self.api_key) if self.api_key else None
        )

        # Rate limiting
        self._request_times: list[float] = []
        self._max_requests_per_minute = 100
        self._concurrent_limit = 5
        self._semaphore = asyncio.Semaphore(self._concurrent_limit)

        logger.info(f"Firecrawl 服務初始化: {self.api_url}")

    async def scrape_board_page(self, url: str) -> FirecrawlResponse:
        """
        爬取 PTT 看板頁面.

        Args:
            url: 看板頁面 URL

        Returns:
            FirecrawlResponse: API 回應
        """
        payload = {
            "url": url,
            "formats": ["markdown", "html"],
            "onlyMainContent": True,
            "includeTags": ["a", "div"],
            "timeout": self.timeout * 1000,  # Convert to milliseconds
            "waitFor": 2000,
        }

        return await self._make_request(payload)

    async def scrape_article(self, url: str) -> FirecrawlResponse:
        """
        爬取單篇文章內容.

        Args:
            url: 文章 URL

        Returns:
            FirecrawlResponse: API 回應
        """
        payload = {
            "url": url,
            "formats": ["markdown"],
            "onlyMainContent": True,
            "removeBase64Images": False,
            "includeTags": ["div", "span", "time"],
            "timeout": self.timeout * 1000,
            "waitFor": 3000,
        }

        return await self._make_request(payload)

    async def _make_request(self, payload: dict[str, Any]) -> FirecrawlResponse:
        """
        發送 API 請求.

        Args:
            payload: 請求參數

        Returns:
            FirecrawlResponse: API 回應
        """
        await self._check_rate_limit()

        async with self._semaphore:  # Limit concurrent requests
            try:
                # Use firecrawl-py client if available
                if self.client:
                    result = self.client.scrape_url(**payload)

                    if result.get("success"):
                        return FirecrawlResponse.from_dict(result)
                    else:
                        error = result.get("error", {})
                        raise FirecrawlError(
                            error.get("message", "Unknown error"),
                            error.get("code", "UNKNOWN"),
                            error,
                        )

                # Fallback to direct HTTP request
                return await self._make_http_request(payload)

            except aiohttp.ClientTimeout:
                raise FirecrawlError("請求超時", "TIMEOUT")
            except aiohttp.ClientConnectionError:
                raise FirecrawlError("連線失敗", "CONNECTION_FAILED")
            except Exception as e:
                logger.error(f"Firecrawl 請求失敗: {e}")
                raise FirecrawlError(str(e), "UNKNOWN")

    async def _make_http_request(self, payload: dict[str, Any]) -> FirecrawlResponse:
        """
        發送 HTTP 請求 (備用方案).

        Args:
            payload: 請求參數

        Returns:
            FirecrawlResponse: API 回應
        """
        headers = {
            "Content-Type": "application/json",
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        timeout = aiohttp.ClientTimeout(total=self.timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{self.api_url}/v0/scrape", json=payload, headers=headers
            ) as response:
                data = await response.json()

                if response.status == 200:
                    return FirecrawlResponse.from_dict(data)
                elif response.status == 401:
                    raise FirecrawlError("API 金鑰無效", "UNAUTHORIZED")
                elif response.status == 429:
                    raise FirecrawlError("超過使用限制", "RATE_LIMITED")
                elif response.status == 503:
                    raise FirecrawlError("服務暫時無法使用", "SERVICE_UNAVAILABLE")
                else:
                    error_msg = data.get("error", {}).get("message", f"HTTP {response.status}")
                    raise FirecrawlError(error_msg, "HTTP_ERROR")

    async def _check_rate_limit(self) -> None:
        """檢查並執行速率限制."""
        now = time.time()

        # 清理超過一分鐘的記錄
        self._request_times = [t for t in self._request_times if now - t < 60]

        # 檢查是否超過限制
        if len(self._request_times) >= self._max_requests_per_minute:
            # 需要等待到最早的請求超過一分鐘
            wait_time = 60 - (now - self._request_times[0])
            if wait_time > 0:
                logger.warning(f"達到速率限制，等待 {wait_time:.2f} 秒")
                await asyncio.sleep(wait_time)

        # 記錄當前請求時間
        self._request_times.append(now)

    def extract_article_links(self, response_data: dict[str, Any]) -> list[dict[str, str]]:
        """
        從看板頁面回應中提取文章連結.

        Args:
            response_data: API 回應資料

        Returns:
            List[Dict[str, str]]: 文章連結列表
        """
        if not response_data.get("success"):
            return []

        data = response_data.get("data", {})
        markdown = data.get("markdown", "")

        # 從 Markdown 中提取文章連結
        links = []

        # 使用正則表達式匹配 PTT 文章連結模式
        article_pattern = r"\[([^\]]+)\]\s*([^\n]+)\n.*?(https://www\.ptt\.cc/bbs/[^/]+/M\.[^\.]+\.A\.[^\.]+\.html)"
        matches = re.findall(article_pattern, markdown, re.MULTILINE | re.DOTALL)

        for match in matches:
            category = match[0].strip()
            title = match[1].strip()
            url = match[2].strip()

            links.append(
                {"text": f"[{category}] {title}", "category": category, "title": title, "url": url}
            )

        # 也從 links 欄位提取（如果有的話）
        api_links = data.get("links", [])
        for link in api_links:
            if isinstance(link, dict) and "url" in link:
                if "ptt.cc/bbs/" in link["url"]:
                    links.append({"text": link.get("text", ""), "url": link["url"]})

        logger.info(f"從看板頁面提取到 {len(links)} 個文章連結")
        return links

    def filter_articles_by_category(
        self, links: list[dict[str, str]], category: str
    ) -> list[dict[str, str]]:
        """
        根據分類篩選文章.

        Args:
            links: 文章連結列表
            category: 要篩選的分類

        Returns:
            List[Dict[str, str]]: 篩選後的文章連結列表
        """
        if not category:
            return links

        filtered_links = []

        for link in links:
            text = link.get("text", "")
            link_category = link.get("category", "")

            # 多種篩選方式
            if category in text or category in link_category or text.startswith(f"[{category}]"):
                filtered_links.append(link)

        logger.info(f"分類 '{category}' 篩選後剩餘 {len(filtered_links)} 個文章")
        return filtered_links

    def parse_article_metadata(self, response_data: dict[str, Any]) -> dict[str, Any]:
        """
        解析文章元資料.

        Args:
            response_data: API 回應資料

        Returns:
            Dict[str, Any]: 解析後的元資料
        """
        if not response_data.get("success"):
            return {}

        data = response_data.get("data", {})
        metadata = data.get("metadata", {})
        markdown = data.get("markdown", "")

        # 從 metadata 取得基本資訊
        parsed_metadata = {
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "publishTime": metadata.get("publishTime", ""),
            "board": metadata.get("board", ""),
            "sourceURL": metadata.get("sourceURL", ""),
        }

        # 從 Markdown 內容中解析額外資訊
        if markdown:
            # 解析標題
            title_match = re.search(r"# \[(.*?)\] (.*?)(?:\n|$)", markdown)
            if title_match:
                parsed_metadata["category"] = title_match.group(1)
                parsed_metadata["title"] = title_match.group(2)

            # 解析作者
            author_match = re.search(r"作者[：:]\s*([^\s\n]+)", markdown)
            if author_match:
                parsed_metadata["author"] = author_match.group(1)

            # 解析時間
            time_match = re.search(r"時間[：:]\s*([^\n]+)", markdown)
            if time_match:
                parsed_metadata["publishTime"] = time_match.group(1)

        return parsed_metadata

    def clean_article_content(self, content: str) -> str:
        """
        清理文章內容.

        Args:
            content: 原始內容

        Returns:
            str: 清理後的內容
        """
        if not content:
            return ""

        # 移除 PTT 系統訊息
        content = re.sub(r"※ 發信站:.*?$", "", content, flags=re.MULTILINE)
        content = re.sub(r"※ 文章網址:.*?$", "", content, flags=re.MULTILINE)
        content = re.sub(r"※ 編輯:.*?$", "", content, flags=re.MULTILINE)

        # 移除推文區塊（簡單版本，可能需要更複雜的邏輯）
        content = re.sub(r"^(推|噓|→).*?$", "", content, flags=re.MULTILINE)

        # 標準化換行格式
        content = re.sub(r"\n{3,}", "\n\n", content)
        content = content.strip()

        return content

    async def scrape_article_with_retry(self, url: str) -> FirecrawlResponse:
        """
        帶重試機制的文章爬取.

        Args:
            url: 文章 URL

        Returns:
            FirecrawlResponse: API 回應
        """
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                return await self.scrape_article(url)
            except FirecrawlError as e:
                last_error = e

                # 不重試的錯誤類型
                if e.error_code in [
                    "UNAUTHORIZED",
                    "INVALID_URL",
                    "CONTENT_NOT_FOUND",
                    "QUOTA_EXCEEDED",
                ]:
                    raise

                if attempt < self.max_retries:
                    # 指數退避
                    wait_time = (2**attempt) + (time.time() % 1)  # Add jitter
                    logger.warning(
                        f"重試 {attempt + 1}/{self.max_retries}: {url}, 等待 {wait_time:.2f} 秒"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"重試次數用盡: {url}")

        if last_error:
            raise last_error

        raise FirecrawlError("未知錯誤", "UNKNOWN")

    async def test_connection(self) -> bool:
        """
        測試 Firecrawl API 連線.

        Returns:
            bool: 連線是否正常
        """
        try:
            # 使用簡單的測試頁面
            test_url = "https://www.ptt.cc/bbs/Stock/index.html"
            response = await self.scrape_board_page(test_url)
            return response.success
        except Exception as e:
            logger.error(f"Firecrawl 連線測試失敗: {e}")
            return False

    def get_service_info(self) -> dict[str, Any]:
        """
        取得服務資訊.

        Returns:
            Dict[str, Any]: 服務資訊
        """
        return {
            "api_url": self.api_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "concurrent_limit": self._concurrent_limit,
            "rate_limit": self._max_requests_per_minute,
            "current_request_count": len(self._request_times),
        }
