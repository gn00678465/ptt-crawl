"""CrawlState database repository.

This module provides database operations for CrawlState model.
"""
import json
import logging
from typing import Optional

from ..models.crawl_state import CrawlState, CrawlStatus
from .connection import DatabaseConnection

logger = logging.getLogger(__name__)


class CrawlStateRepository:
    """CrawlState 資料庫操作類別."""

    def __init__(self, db: DatabaseConnection):
        self.db = db

    async def init_crawl_state(self, board: str) -> None:
        """
        初始化看板爬取狀態.

        Args:
            board: 看板名稱
        """
        query = """
            INSERT INTO crawl_states (board, status, created_at, updated_at)
            VALUES ($1, $2, NOW(), NOW())
            ON CONFLICT (board) DO NOTHING
        """

        await self.db.execute(query, board, CrawlStatus.IDLE.value)
        logger.info(f"初始化看板爬取狀態: {board}")

    async def get_crawl_state(self, board: str) -> Optional[CrawlState]:
        """
        取得看板爬取狀態.

        Args:
            board: 看板名稱

        Returns:
            Optional[CrawlState]: 爬取狀態，不存在時回傳 None
        """
        query = """
            SELECT id, board, last_crawl_time, last_page_crawled,
                   processed_urls, failed_urls, retry_count, max_retries,
                   status, error_message, created_at, updated_at
            FROM crawl_states
            WHERE board = $1
        """

        row = await self.db.fetchrow(query, board)

        if row:
            return CrawlState(
                id=row["id"],
                board=row["board"],
                last_crawl_time=row["last_crawl_time"],
                last_page_crawled=row["last_page_crawled"],
                processed_urls=row["processed_urls"] or [],
                failed_urls=row["failed_urls"] or [],
                retry_count=row["retry_count"],
                max_retries=row["max_retries"],
                status=CrawlStatus.from_string(row["status"]),
                error_message=row["error_message"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

        return None

    async def update_crawl_state(
        self,
        board: str,
        status: CrawlStatus,
        last_page_crawled: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """
        更新爬取狀態.

        Args:
            board: 看板名稱
            status: 新的狀態
            last_page_crawled: 最後爬取頁面
            error_message: 錯誤訊息
        """
        query = """
            UPDATE crawl_states
            SET status = $1,
                last_crawl_time = CASE WHEN $1 = 'completed' THEN NOW() ELSE last_crawl_time END,
                last_page_crawled = COALESCE($2, last_page_crawled),
                error_message = $3,
                updated_at = NOW()
            WHERE board = $4
        """

        result = await self.db.execute(query, status.value, last_page_crawled, error_message, board)

        rows_affected = int(result.split()[-1])
        if rows_affected == 0:
            # 如果不存在，則初始化
            await self.init_crawl_state(board)
            await self.update_crawl_state(board, status, last_page_crawled, error_message)
        else:
            logger.info(f"更新爬取狀態: {board} -> {status.value}")

    async def add_processed_url(self, board: str, url: str) -> None:
        """
        新增已處理的 URL.

        Args:
            board: 看板名稱
            url: 處理過的 URL
        """
        query = """
            UPDATE crawl_states
            SET processed_urls = COALESCE(processed_urls, '[]'::jsonb) || $1::jsonb,
                updated_at = NOW()
            WHERE board = $2
        """

        # 包裝為 JSON 數組格式
        url_json = json.dumps([url])

        result = await self.db.execute(query, url_json, board)
        rows_affected = int(result.split()[-1])

        if rows_affected == 0:
            logger.warning(f"未找到看板狀態進行 URL 更新: {board}")
        else:
            logger.debug(f"新增已處理 URL: {board} - {url}")

    async def add_failed_url(self, board: str, url: str) -> None:
        """
        新增失敗的 URL.

        Args:
            board: 看板名稱
            url: 失敗的 URL
        """
        query = """
            UPDATE crawl_states
            SET failed_urls = COALESCE(failed_urls, '[]'::jsonb) || $1::jsonb,
                updated_at = NOW()
            WHERE board = $2
        """

        # 包裝為 JSON 數組格式
        url_json = json.dumps([url])

        result = await self.db.execute(query, url_json, board)
        rows_affected = int(result.split()[-1])

        if rows_affected == 0:
            logger.warning(f"未找到看板狀態進行失敗 URL 更新: {board}")
        else:
            logger.debug(f"新增失敗 URL: {board} - {url}")

    async def remove_failed_url(self, board: str, url: str) -> bool:
        """
        從失敗列表中移除 URL.

        Args:
            board: 看板名稱
            url: 要移除的 URL

        Returns:
            bool: 是否成功移除
        """
        # 先取得當前的失敗 URL 列表
        state = await self.get_crawl_state(board)
        if not state or url not in state.failed_urls:
            return False

        # 移除指定的 URL
        updated_failed_urls = [u for u in state.failed_urls if u != url]

        query = """
            UPDATE crawl_states
            SET failed_urls = $1::jsonb,
                updated_at = NOW()
            WHERE board = $2
        """

        await self.db.execute(query, json.dumps(updated_failed_urls), board)
        logger.debug(f"移除失敗 URL: {board} - {url}")
        return True

    async def increment_retry_count(self, board: str) -> None:
        """
        增加重試次數.

        Args:
            board: 看板名稱
        """
        query = """
            UPDATE crawl_states
            SET retry_count = retry_count + 1,
                updated_at = NOW()
            WHERE board = $1 AND retry_count < max_retries
        """

        result = await self.db.execute(query, board)
        rows_affected = int(result.split()[-1])

        if rows_affected > 0:
            logger.info(f"增加重試次數: {board}")
        else:
            logger.warning(f"無法增加重試次數，可能已達最大重試次數: {board}")

    async def reset_retry_count(self, board: str) -> None:
        """
        重置重試次數.

        Args:
            board: 看板名稱
        """
        query = """
            UPDATE crawl_states
            SET retry_count = 0,
                updated_at = NOW()
            WHERE board = $1
        """

        await self.db.execute(query, board)
        logger.info(f"重置重試次數: {board}")

    async def get_all_states(self) -> list[CrawlState]:
        """
        取得所有爬取狀態.

        Returns:
            List[CrawlState]: 所有爬取狀態列表
        """
        query = """
            SELECT id, board, last_crawl_time, last_page_crawled,
                   processed_urls, failed_urls, retry_count, max_retries,
                   status, error_message, created_at, updated_at
            FROM crawl_states
            ORDER BY updated_at DESC
        """

        rows = await self.db.fetch(query)
        states = []

        for row in rows:
            state = CrawlState(
                id=row["id"],
                board=row["board"],
                last_crawl_time=row["last_crawl_time"],
                last_page_crawled=row["last_page_crawled"],
                processed_urls=row["processed_urls"] or [],
                failed_urls=row["failed_urls"] or [],
                retry_count=row["retry_count"],
                max_retries=row["max_retries"],
                status=CrawlStatus.from_string(row["status"]),
                error_message=row["error_message"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            states.append(state)

        return states

    async def delete_state(self, board: str) -> bool:
        """
        刪除看板爬取狀態.

        Args:
            board: 看板名稱

        Returns:
            bool: 是否成功刪除
        """
        query = "DELETE FROM crawl_states WHERE board = $1"
        result = await self.db.execute(query, board)
        rows_affected = int(result.split()[-1])

        if rows_affected > 0:
            logger.info(f"刪除爬取狀態: {board}")
            return True
        else:
            logger.warning(f"未找到要刪除的爬取狀態: {board}")
            return False

    async def cleanup_old_states(self, days_old: int = 30) -> int:
        """
        清理舊的爬取狀態.

        Args:
            days_old: 清理多少天前的狀態

        Returns:
            int: 清理的數量
        """
        query = (
            """
            DELETE FROM crawl_states
            WHERE status = 'completed'
              AND last_crawl_time < NOW() - INTERVAL '%s days'
        """
            % days_old
        )

        result = await self.db.execute(query)
        rows_affected = int(result.split()[-1])

        logger.info(f"清理舊爬取狀態: {rows_affected} 筆記錄")
        return rows_affected

    async def get_states_by_status(self, status: CrawlStatus) -> list[CrawlState]:
        """
        根據狀態取得爬取狀態列表.

        Args:
            status: 爬取狀態

        Returns:
            List[CrawlState]: 符合狀態的爬取狀態列表
        """
        query = """
            SELECT id, board, last_crawl_time, last_page_crawled,
                   processed_urls, failed_urls, retry_count, max_retries,
                   status, error_message, created_at, updated_at
            FROM crawl_states
            WHERE status = $1
            ORDER BY updated_at DESC
        """

        rows = await self.db.fetch(query, status.value)
        states = []

        for row in rows:
            state = CrawlState(
                id=row["id"],
                board=row["board"],
                last_crawl_time=row["last_crawl_time"],
                last_page_crawled=row["last_page_crawled"],
                processed_urls=row["processed_urls"] or [],
                failed_urls=row["failed_urls"] or [],
                retry_count=row["retry_count"],
                max_retries=row["max_retries"],
                status=CrawlStatus.from_string(row["status"]),
                error_message=row["error_message"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            states.append(state)

        return states

    async def batch_update_processed_urls(self, board: str, urls: list[str]) -> None:
        """
        批次更新已處理的 URL.

        Args:
            board: 看板名稱
            urls: URL 列表
        """
        if not urls:
            return

        query = """
            UPDATE crawl_states
            SET processed_urls = COALESCE(processed_urls, '[]'::jsonb) || $1::jsonb,
                updated_at = NOW()
            WHERE board = $2
        """

        urls_json = json.dumps(urls)
        await self.db.execute(query, urls_json, board)
        logger.info(f"批次更新已處理 URL: {board}, 數量: {len(urls)}")

    async def get_crawl_statistics(self, board: str) -> dict:
        """
        取得爬取統計資訊.

        Args:
            board: 看板名稱

        Returns:
            dict: 統計資訊
        """
        state = await self.get_crawl_state(board)
        if not state:
            return {}

        return state.get_statistics()
