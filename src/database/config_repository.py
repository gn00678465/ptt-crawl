"""Config database repository.

This module provides database operations for Config model.
"""
import logging
from datetime import datetime
from typing import Optional

from ..models.config import DEFAULT_CONFIG, Config, validate_config_value
from .connection import DatabaseConnection

logger = logging.getLogger(__name__)


class ConfigRepository:
    """Config 資料庫操作類別."""

    def __init__(self, db: DatabaseConnection):
        self.db = db

    async def get_config(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        取得配置值.

        Args:
            key: 配置鍵名
            default: 預設值

        Returns:
            Optional[str]: 配置值
        """
        query = "SELECT value FROM configs WHERE key = $1"
        value = await self.db.fetchval(query, key)

        if value is not None:
            return value

        # 如果資料庫中沒有，則返回預設值
        if default is not None:
            return default

        # 返回系統預設值
        return str(DEFAULT_CONFIG.get(key)) if key in DEFAULT_CONFIG else None

    async def set_config(self, key: str, value: str, description: Optional[str] = None) -> None:
        """
        設定配置值.

        Args:
            key: 配置鍵名
            value: 配置值
            description: 配置說明
        """
        # 驗證配置值
        try:
            validate_config_value(key, value)
        except ValueError as e:
            logger.error(f"配置值驗證失敗: {key} = {value}, 錯誤: {e}")
            raise

        query = """
            INSERT INTO configs (key, value, description, created_at, updated_at)
            VALUES ($1, $2, $3, NOW(), NOW())
            ON CONFLICT (key) DO UPDATE SET
                value = EXCLUDED.value,
                description = COALESCE(EXCLUDED.description, configs.description),
                updated_at = NOW()
        """

        await self.db.execute(query, key, value, description)
        logger.info(f"設定配置: {key} = {value}")

    async def delete_config(self, key: str) -> bool:
        """
        刪除配置值.

        Args:
            key: 配置鍵名

        Returns:
            bool: 是否成功刪除
        """
        query = "DELETE FROM configs WHERE key = $1"
        result = await self.db.execute(query, key)
        rows_affected = int(result.split()[-1])

        if rows_affected > 0:
            logger.info(f"刪除配置: {key}")
            return True
        else:
            logger.warning(f"未找到要刪除的配置: {key}")
            return False

    async def get_all_configs(self) -> dict[str, str]:
        """
        取得所有配置值.

        Returns:
            Dict[str, str]: 配置鍵值對
        """
        query = "SELECT key, value FROM configs ORDER BY key"
        rows = await self.db.fetch(query)

        configs = {}
        for row in rows:
            configs[row["key"]] = row["value"]

        # 合併系統預設值（如果資料庫中沒有的話）
        for key, default_value in DEFAULT_CONFIG.items():
            if key not in configs:
                configs[key] = str(default_value)

        return configs

    async def get_config_with_metadata(self, key: str) -> Optional[dict]:
        """
        取得配置值及其元資料.

        Args:
            key: 配置鍵名

        Returns:
            Optional[Dict]: 包含配置值和元資料的字典
        """
        query = """
            SELECT key, value, description, created_at, updated_at
            FROM configs
            WHERE key = $1
        """

        row = await self.db.fetchrow(query, key)

        if row:
            return {
                "key": row["key"],
                "value": row["value"],
                "description": row["description"],
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat(),
            }

        # 如果資料庫中沒有，檢查是否有預設值
        if key in DEFAULT_CONFIG:
            now = datetime.now()
            return {
                "key": key,
                "value": str(DEFAULT_CONFIG[key]),
                "description": "系統預設值",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }

        return None

    async def get_configs_by_prefix(self, prefix: str) -> dict[str, str]:
        """
        根據前綴取得配置值.

        Args:
            prefix: 配置鍵名前綴

        Returns:
            Dict[str, str]: 符合前綴的配置鍵值對
        """
        query = "SELECT key, value FROM configs WHERE key LIKE $1 ORDER BY key"
        rows = await self.db.fetch(query, f"{prefix}%")

        configs = {}
        for row in rows:
            configs[row["key"]] = row["value"]

        # 也檢查系統預設值
        for key, default_value in DEFAULT_CONFIG.items():
            if key.startswith(prefix) and key not in configs:
                configs[key] = str(default_value)

        return configs

    async def initialize_default_configs(self) -> None:
        """初始化預設配置值到資料庫."""
        descriptions = {
            "crawl.rate_limit": "每分鐘最大爬取數量",
            "crawl.request_delay": "請求間隔秒數",
            "crawl.max_retries": "最大重試次數",
            "crawl.timeout": "請求超時時間（秒）",
            "firecrawl.api_url": "Firecrawl API 端點",
            "firecrawl.api_key": "Firecrawl API 金鑰",
            "database.connection_pool_size": "資料庫連接池大小",
            "redis.connection_string": "Redis 連線字串",
            "logging.level": "日誌級別",
            "logging.file_path": "日誌檔案路徑",
            "logging.max_size": "日誌檔案最大大小",
            "logging.backup_count": "日誌檔案備份數量",
        }

        async with self.db.transaction() as conn:
            for key, value in DEFAULT_CONFIG.items():
                query = """
                    INSERT INTO configs (key, value, description, created_at, updated_at)
                    VALUES ($1, $2, $3, NOW(), NOW())
                    ON CONFLICT (key) DO NOTHING
                """

                await conn.execute(query, key, str(value), descriptions.get(key, "系統預設配置"))

        logger.info("初始化預設配置完成")

    async def backup_configs(self) -> list[Config]:
        """
        備份所有配置.

        Returns:
            List[Config]: 配置物件列表
        """
        query = """
            SELECT key, value, description, created_at, updated_at
            FROM configs
            ORDER BY key
        """

        rows = await self.db.fetch(query)
        configs = []

        for row in rows:
            config = Config(
                key=row["key"],
                value=row["value"],
                description=row["description"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            configs.append(config)

        logger.info(f"備份配置: {len(configs)} 項")
        return configs

    async def restore_configs(self, configs: list[Config]) -> None:
        """
        還原配置.

        Args:
            configs: 要還原的配置列表
        """
        async with self.db.transaction() as conn:
            # 清空現有配置
            await conn.execute("DELETE FROM configs")

            # 插入還原的配置
            for config in configs:
                query = """
                    INSERT INTO configs (key, value, description, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5)
                """

                await conn.execute(
                    query,
                    config.key,
                    config.value,
                    config.description,
                    config.created_at,
                    config.updated_at,
                )

        logger.info(f"還原配置: {len(configs)} 項")

    async def reset_config_to_default(self, key: str) -> bool:
        """
        重置配置為預設值.

        Args:
            key: 配置鍵名

        Returns:
            bool: 是否成功重置
        """
        if key not in DEFAULT_CONFIG:
            logger.warning(f"無法重置配置，沒有預設值: {key}")
            return False

        default_value = str(DEFAULT_CONFIG[key])
        await self.set_config(key, default_value, "重置為系統預設值")

        logger.info(f"重置配置為預設值: {key} = {default_value}")
        return True

    async def reset_all_configs_to_default(self) -> None:
        """重置所有配置為預設值."""
        # 清空現有配置
        await self.db.execute("DELETE FROM configs")

        # 重新初始化預設配置
        await self.initialize_default_configs()

        logger.info("重置所有配置為預設值")

    async def validate_all_configs(self) -> list[str]:
        """
        驗證所有配置值.

        Returns:
            List[str]: 驗證錯誤列表
        """
        configs = await self.get_all_configs()
        errors = []

        for key, value in configs.items():
            try:
                validate_config_value(key, value)
            except ValueError as e:
                errors.append(f"{key}: {e}")

        if errors:
            logger.warning(f"發現 {len(errors)} 個配置驗證錯誤")
        else:
            logger.info("所有配置驗證通過")

        return errors

    async def get_config_count(self) -> int:
        """
        取得配置數量.

        Returns:
            int: 配置數量
        """
        query = "SELECT COUNT(*) FROM configs"
        return await self.db.fetchval(query)

    async def search_configs(self, search_term: str) -> dict[str, str]:
        """
        搜尋配置.

        Args:
            search_term: 搜尋關鍵字

        Returns:
            Dict[str, str]: 符合搜尋條件的配置鍵值對
        """
        query = """
            SELECT key, value
            FROM configs
            WHERE key ILIKE $1 OR description ILIKE $1
            ORDER BY key
        """

        rows = await self.db.fetch(query, f"%{search_term}%")

        configs = {}
        for row in rows:
            configs[row["key"]] = row["value"]

        return configs
