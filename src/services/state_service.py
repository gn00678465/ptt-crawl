"""State management service implementation.

This module implements the Redis + JSON dual-layer state management.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import redis.asyncio as redis

from ..models.crawl_state import CrawlState, CrawlStatus

logger = logging.getLogger(__name__)


class StateService:
    """狀態管理服務，實作 Redis + JSON 雙層狀態管理."""

    def __init__(self, redis_url: str, json_state_dir: str = "data/state"):
        self.redis_url = redis_url
        self.json_state_dir = Path(json_state_dir)
        self.redis_client: Optional[redis.Redis] = None
        self._redis_available = True

        # 確保 JSON 狀態目錄存在
        self.json_state_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"狀態服務初始化: Redis={redis_url}, JSON dir={json_state_dir}")

    async def initialize(self) -> None:
        """初始化 Redis 連線."""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                retry_on_timeout=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )

            # 測試連線
            await self.redis_client.ping()
            self._redis_available = True
            logger.info("Redis 連線成功")

        except Exception as e:
            logger.warning(f"Redis 連線失敗，將使用 JSON fallback: {e}")
            self._redis_available = False
            self.redis_client = None

    async def close(self) -> None:
        """關閉連線."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis 連線已關閉")

    async def sync_state_to_redis(self, crawl_state: CrawlState) -> bool:
        """同步爬取狀態到 Redis."""
        if not self._redis_available or not self.redis_client:
            logger.debug("Redis 不可用，跳過同步")
            return False

        try:
            key = f"crawl_state:{crawl_state.board}"
            state_data = {
                "id": crawl_state.id,
                "board": crawl_state.board,
                "last_crawl_time": crawl_state.last_crawl_time.isoformat()
                if crawl_state.last_crawl_time
                else None,
                "last_page_crawled": crawl_state.last_page_crawled,
                "processed_urls": crawl_state.processed_urls,
                "failed_urls": crawl_state.failed_urls,
                "retry_count": crawl_state.retry_count,
                "max_retries": crawl_state.max_retries,
                "status": crawl_state.status.value,
                "error_message": crawl_state.error_message,
                "created_at": crawl_state.created_at.isoformat(),
                "updated_at": crawl_state.updated_at.isoformat(),
            }

            await self.redis_client.setex(
                key,
                3600 * 24,  # 24 小時過期
                json.dumps(state_data, ensure_ascii=False),
            )

            logger.debug(f"狀態已同步到 Redis: {crawl_state.board}")
            return True

        except Exception as e:
            logger.error(f"同步到 Redis 失敗: {e}")
            self._redis_available = False
            return False

    async def get_redis_state(self, board: str) -> Optional[dict[str, Any]]:
        """從 Redis 取得爬取狀態."""
        if not self._redis_available or not self.redis_client:
            return None

        try:
            key = f"crawl_state:{board}"
            data = await self.redis_client.get(key)

            if not data:
                return None

            state_data = json.loads(data)
            logger.debug(f"從 Redis 取得狀態: {board}")
            return state_data

        except Exception as e:
            logger.error(f"從 Redis 取得狀態失敗: {e}")
            self._redis_available = False
            return None

    async def save_state_to_json(self, crawl_state: CrawlState) -> bool:
        """儲存爬取狀態到 JSON 檔案."""
        try:
            json_file = self.json_state_dir / f"{crawl_state.board}.json"

            state_data = {
                "id": crawl_state.id,
                "board": crawl_state.board,
                "last_crawl_time": crawl_state.last_crawl_time.isoformat()
                if crawl_state.last_crawl_time
                else None,
                "last_page_crawled": crawl_state.last_page_crawled,
                "processed_urls": crawl_state.processed_urls,
                "failed_urls": crawl_state.failed_urls,
                "retry_count": crawl_state.retry_count,
                "max_retries": crawl_state.max_retries,
                "status": crawl_state.status.value,
                "error_message": crawl_state.error_message,
                "created_at": crawl_state.created_at.isoformat(),
                "updated_at": crawl_state.updated_at.isoformat(),
                "saved_at": datetime.now().isoformat(),
            }

            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)

            logger.debug(f"狀態已儲存到 JSON: {json_file}")
            return True

        except Exception as e:
            logger.error(f"儲存 JSON 狀態失敗: {e}")
            return False

    async def get_json_state(self, board: str) -> Optional[dict[str, Any]]:
        """從 JSON 檔案讀取爬取狀態."""
        try:
            json_file = self.json_state_dir / f"{board}.json"

            if not json_file.exists():
                return None

            with open(json_file, encoding="utf-8") as f:
                state_data = json.load(f)

            logger.debug(f"從 JSON 讀取狀態: {json_file}")
            return state_data

        except Exception as e:
            logger.error(f"讀取 JSON 狀態失敗: {e}")
            return None

    async def recover_state_from_json(self, board: str) -> Optional[CrawlState]:
        """從 JSON 恢復爬取狀態."""
        state_data = await self.get_json_state(board)
        if not state_data:
            return None

        try:
            # 轉換回 CrawlState 物件
            crawl_state = CrawlState(
                id=state_data["id"],
                board=state_data["board"],
                last_crawl_time=datetime.fromisoformat(state_data["last_crawl_time"])
                if state_data["last_crawl_time"]
                else None,
                last_page_crawled=state_data["last_page_crawled"],
                processed_urls=state_data["processed_urls"],
                failed_urls=state_data["failed_urls"],
                retry_count=state_data["retry_count"],
                max_retries=state_data["max_retries"],
                status=CrawlStatus(state_data["status"]),
                error_message=state_data["error_message"],
                created_at=datetime.fromisoformat(state_data["created_at"]),
                updated_at=datetime.fromisoformat(state_data["updated_at"]),
            )

            logger.info(f"從 JSON 恢復狀態: {board}")
            return crawl_state

        except Exception as e:
            logger.error(f"恢復 JSON 狀態失敗: {e}")
            return None

    async def sync_redis_from_json(self, board: str) -> bool:
        """從 JSON 同步狀態到 Redis."""
        crawl_state = await self.recover_state_from_json(board)
        if not crawl_state:
            return False

        return await self.sync_state_to_redis(crawl_state)

    async def cleanup_expired_states(self, days: int = 7) -> int:
        """清理過期的狀態檔案."""
        cleaned_count = 0
        cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)

        try:
            for json_file in self.json_state_dir.glob("*.json"):
                if json_file.stat().st_mtime < cutoff_time:
                    json_file.unlink()
                    cleaned_count += 1
                    logger.debug(f"清理過期狀態檔案: {json_file}")

            logger.info(f"清理了 {cleaned_count} 個過期狀態檔案")
            return cleaned_count

        except Exception as e:
            logger.error(f"清理過期狀態失敗: {e}")
            return 0

    async def get_all_board_states(self) -> dict[str, dict[str, Any]]:
        """取得所有看板的狀態."""
        states = {}

        # 優先從 Redis 讀取
        if self._redis_available and self.redis_client:
            try:
                keys = await self.redis_client.keys("crawl_state:*")
                for key in keys:
                    board = key.replace("crawl_state:", "")
                    state_data = await self.get_redis_state(board)
                    if state_data:
                        states[board] = state_data
            except Exception as e:
                logger.warning(f"從 Redis 讀取所有狀態失敗: {e}")

        # 從 JSON 補充缺失的狀態
        try:
            for json_file in self.json_state_dir.glob("*.json"):
                board = json_file.stem
                if board not in states:
                    state_data = await self.get_json_state(board)
                    if state_data:
                        states[board] = state_data
        except Exception as e:
            logger.error(f"從 JSON 讀取所有狀態失敗: {e}")

        return states

    async def delete_state(self, board: str) -> bool:
        """刪除指定看板的狀態."""
        success = True

        # 從 Redis 刪除
        if self._redis_available and self.redis_client:
            try:
                key = f"crawl_state:{board}"
                await self.redis_client.delete(key)
                logger.debug(f"從 Redis 刪除狀態: {board}")
            except Exception as e:
                logger.error(f"從 Redis 刪除狀態失敗: {e}")
                success = False

        # 從 JSON 刪除
        try:
            json_file = self.json_state_dir / f"{board}.json"
            if json_file.exists():
                json_file.unlink()
                logger.debug(f"刪除 JSON 狀態檔案: {json_file}")
        except Exception as e:
            logger.error(f"刪除 JSON 狀態失敗: {e}")
            success = False

        return success

    async def health_check(self) -> dict[str, Any]:
        """健康檢查."""
        health = {
            "redis_available": self._redis_available,
            "json_dir_exists": self.json_state_dir.exists(),
            "json_dir_writable": False,
        }

        # 測試 JSON 目錄寫入權限
        try:
            test_file = self.json_state_dir / "test_write.json"
            test_file.write_text('{"test": true}')
            test_file.unlink()
            health["json_dir_writable"] = True
        except Exception:
            pass

        # 測試 Redis 連線
        if self.redis_client:
            try:
                await self.redis_client.ping()
                health["redis_available"] = True
                self._redis_available = True
            except Exception:
                health["redis_available"] = False
                self._redis_available = False

        return health

    # 測試和模擬方法

    async def simulate_redis_failure(self) -> None:
        """模擬 Redis 失敗（測試用）."""
        self._redis_available = False
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
        logger.warning("模擬 Redis 失敗")

    async def recover_redis_connection(self) -> bool:
        """恢復 Redis 連線（測試用）."""
        try:
            await self.initialize()
            return self._redis_available
        except Exception as e:
            logger.error(f"恢復 Redis 連線失敗: {e}")
            return False

    async def simulate_redis_corruption(self, board: str) -> None:
        """模擬 Redis 資料損壞（測試用）."""
        if not self._redis_available or not self.redis_client:
            return

        try:
            key = f"crawl_state:{board}"
            await self.redis_client.set(key, "corrupted_data")
            logger.warning(f"模擬 Redis 資料損壞: {board}")
        except Exception as e:
            logger.error(f"模擬 Redis 損壞失敗: {e}")

    async def simulate_json_corruption(self, board: str) -> None:
        """模擬 JSON 檔案損壞（測試用）."""
        try:
            json_file = self.json_state_dir / f"{board}.json"
            json_file.write_text("corrupted json data")
            logger.warning(f"模擬 JSON 檔案損壞: {board}")
        except Exception as e:
            logger.error(f"模擬 JSON 損壞失敗: {e}")
