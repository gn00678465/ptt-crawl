"""Article database repository.

This module provides database operations for Article model.
"""
import logging
from typing import Optional

import asyncpg

from ..models.article import Article
from .connection import DatabaseConnection

logger = logging.getLogger(__name__)


class ArticleRepository:
    """Article 資料庫操作類別."""

    def __init__(self, db: DatabaseConnection):
        self.db = db

    async def insert_article(self, article: Article) -> int:
        """
        插入新文章記錄.

        Args:
            article: 文章物件

        Returns:
            int: 新插入記錄的 ID

        Raises:
            IntegrityError: URL 重複
            ValidationError: 欄位驗證失敗
        """
        query = """
            INSERT INTO articles (title, author, board, url, content,
                                publish_date, category, crawl_date)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
        """

        try:
            article_id = await self.db.fetchval(
                query,
                article.title,
                article.author,
                article.board,
                article.url,
                article.content,
                article.publish_date,
                article.category,
                article.crawl_date,
            )

            logger.info(f"成功插入文章: {article.title} (ID: {article_id})")
            return article_id

        except asyncpg.UniqueViolationError as e:
            logger.warning(f"文章 URL 重複: {article.url}")
            raise IntegrityError(f"文章 URL 已存在: {article.url}") from e
        except Exception as e:
            logger.error(f"插入文章失敗: {e}")
            raise

    async def article_exists(self, url: str) -> bool:
        """
        檢查文章是否已存在.

        Args:
            url: 文章 URL

        Returns:
            bool: 是否存在
        """
        query = "SELECT EXISTS(SELECT 1 FROM articles WHERE url = $1)"
        return await self.db.fetchval(query, url)

    async def get_articles_by_board(
        self, board: str, limit: int = 100, offset: int = 0, category: Optional[str] = None
    ) -> list[Article]:
        """
        根據看板查詢文章.

        Args:
            board: 看板名稱
            limit: 回傳數量限制
            offset: 偏移量
            category: 分類篩選

        Returns:
            List[Article]: 文章列表
        """
        base_query = """
            SELECT id, title, author, board, url, content,
                   publish_date, crawl_date, category, created_at, updated_at
            FROM articles
            WHERE board = $1
        """

        params = [board]

        if category:
            base_query += " AND (category = $2 OR title ILIKE $3)"
            params.extend([category, f"%[{category}]%"])

        base_query += " ORDER BY publish_date DESC LIMIT $" + str(len(params) + 1)
        params.append(limit)

        if offset > 0:
            base_query += " OFFSET $" + str(len(params) + 1)
            params.append(offset)

        rows = await self.db.fetch(base_query, *params)

        articles = []
        for row in rows:
            article = Article(
                id=row["id"],
                title=row["title"],
                author=row["author"],
                board=row["board"],
                url=row["url"],
                content=row["content"],
                publish_date=row["publish_date"],
                crawl_date=row["crawl_date"],
                category=row["category"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            articles.append(article)

        return articles

    async def update_article_content(self, url: str, content: str) -> bool:
        """
        更新文章內容.

        Args:
            url: 文章 URL
            content: 新的內容

        Returns:
            bool: 是否成功更新
        """
        query = """
            UPDATE articles
            SET content = $1, updated_at = NOW()
            WHERE url = $2
        """

        result = await self.db.execute(query, content, url)
        rows_affected = int(result.split()[-1])

        if rows_affected > 0:
            logger.info(f"成功更新文章內容: {url}")
            return True
        else:
            logger.warning(f"未找到要更新的文章: {url}")
            return False

    async def get_article_by_url(self, url: str) -> Optional[Article]:
        """
        根據 URL 取得文章.

        Args:
            url: 文章 URL

        Returns:
            Optional[Article]: 文章物件或 None
        """
        query = """
            SELECT id, title, author, board, url, content,
                   publish_date, crawl_date, category, created_at, updated_at
            FROM articles
            WHERE url = $1
        """

        row = await self.db.fetchrow(query, url)

        if row:
            return Article(
                id=row["id"],
                title=row["title"],
                author=row["author"],
                board=row["board"],
                url=row["url"],
                content=row["content"],
                publish_date=row["publish_date"],
                crawl_date=row["crawl_date"],
                category=row["category"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

        return None

    async def batch_insert_articles(self, articles: list[Article]) -> list[int]:
        """
        批次插入文章.

        Args:
            articles: 文章列表

        Returns:
            List[int]: 插入成功的 ID 列表
        """
        if not articles:
            return []

        query = """
            INSERT INTO articles (title, author, board, url, content,
                                publish_date, category, crawl_date)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
        """

        inserted_ids = []

        async with self.db.transaction() as conn:
            for article in articles:
                try:
                    article_id = await conn.fetchval(
                        query,
                        article.title,
                        article.author,
                        article.board,
                        article.url,
                        article.content,
                        article.publish_date,
                        article.category,
                        article.crawl_date,
                    )
                    inserted_ids.append(article_id)

                except asyncpg.UniqueViolationError:
                    logger.warning(f"跳過重複文章: {article.url}")
                    continue
                except Exception as e:
                    logger.error(f"批次插入文章失敗: {e}")
                    raise

        logger.info(f"批次插入完成，成功插入 {len(inserted_ids)} 篇文章")
        return inserted_ids

    async def delete_article(self, article_id: int) -> bool:
        """
        刪除文章.

        Args:
            article_id: 文章 ID

        Returns:
            bool: 是否成功刪除
        """
        query = "DELETE FROM articles WHERE id = $1"
        result = await self.db.execute(query, article_id)
        rows_affected = int(result.split()[-1])

        if rows_affected > 0:
            logger.info(f"成功刪除文章: {article_id}")
            return True
        else:
            logger.warning(f"未找到要刪除的文章: {article_id}")
            return False

    async def count_articles(self, board: str, category: Optional[str] = None) -> int:
        """
        統計文章數量.

        Args:
            board: 看板名稱
            category: 分類篩選

        Returns:
            int: 文章數量
        """
        query = "SELECT COUNT(*) FROM articles WHERE board = $1"
        params = [board]

        if category:
            query += " AND (category = $2 OR title ILIKE $3)"
            params.extend([category, f"%[{category}]%"])

        return await self.db.fetchval(query, *params)

    async def get_recent_articles(
        self, board: str, hours: int = 24, limit: int = 100
    ) -> list[Article]:
        """
        取得最近的文章.

        Args:
            board: 看板名稱
            hours: 時間範圍（小時）
            limit: 數量限制

        Returns:
            List[Article]: 文章列表
        """
        query = (
            """
            SELECT id, title, author, board, url, content,
                   publish_date, crawl_date, category, created_at, updated_at
            FROM articles
            WHERE board = $1 AND crawl_date >= NOW() - INTERVAL '%s hours'
            ORDER BY crawl_date DESC
            LIMIT $2
        """
            % hours
        )

        rows = await self.db.fetch(query, board, limit)

        articles = []
        for row in rows:
            article = Article(
                id=row["id"],
                title=row["title"],
                author=row["author"],
                board=row["board"],
                url=row["url"],
                content=row["content"],
                publish_date=row["publish_date"],
                crawl_date=row["crawl_date"],
                category=row["category"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            articles.append(article)

        return articles

    async def update_crawl_progress(
        self, board: str, processed_urls: list[str], new_articles: list[Article]
    ) -> None:
        """
        原子性更新爬取進度和文章.

        Args:
            board: 看板名稱
            processed_urls: 已處理 URL 列表
            new_articles: 新文章列表
        """
        async with self.db.transaction() as conn:
            # 1. 批次插入新文章
            if new_articles:
                await self.batch_insert_articles(new_articles)

            # 2. 更新爬取狀態會在 CrawlStateRepository 中處理
            # 這裡只處理文章相關的操作

            logger.info(f"完成爬取進度更新: {board}, 新增 {len(new_articles)} 篇文章")


class IntegrityError(Exception):
    """資料完整性錯誤."""
