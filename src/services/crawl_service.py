"""Crawl service implementation.

This module implements the two-phase crawling logic for PTT articles.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from ..models.article import Article
from ..models.crawl_state import CrawlState, CrawlStatus
from ..database.article_repository import ArticleRepository
from ..database.crawl_state_repository import CrawlStateRepository
from .firecrawl_service import FirecrawlService, FirecrawlError
from .state_service import StateService
from .parser_service import ParserService

logger = logging.getLogger(__name__)


class CrawlService:
    """PTT 爬取服務，實作兩階段爬取邏輯."""

    def __init__(
        self,
        firecrawl_service: FirecrawlService,
        article_repo: ArticleRepository,
        crawl_state_repo: CrawlStateRepository,
        state_service: StateService,
        parser_service: ParserService,
        config: Dict[str, Any],
    ):
        self.firecrawl = firecrawl_service
        self.article_repo = article_repo
        self.crawl_state_repo = crawl_state_repo
        self.state_service = state_service
        self.parser = parser_service
        self.config = config

        # Rate limiting
        self.rate_limit = int(config.get("crawl.rate_limit", 60))
        self.request_delay = float(config.get("crawl.request_delay", 1.5))
        self.max_retries = int(config.get("crawl.max_retries", 3))
        self.concurrent_limit = int(config.get("crawl.concurrent_limit", 3))

        self._semaphore = asyncio.Semaphore(self.concurrent_limit)

    async def crawl_board(
        self,
        board: str,
        category: Optional[str] = None,
        pages: int = 1,
        incremental: bool = True,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        執行看板爬取作業.

        Args:
            board: 看板名稱 (例如: Stock)
            category: 文章分類篩選 (例如: 心得, 標的)
            pages: 爬取頁數
            incremental: 是否使用增量爬取
            force: 是否強制重新爬取

        Returns:
            Dict[str, Any]: 爬取結果摘要
        """
        start_time = datetime.now()
        logger.info(f"開始爬取 PTT {board} 板，分類: {category}, 頁數: {pages}")

        try:
            # 1. 初始化爬取狀態
            await self._initialize_crawl_state(board, force)

            # 2. 取得當前狀態
            crawl_state = await self.crawl_state_repo.get_crawl_state(board)
            if not crawl_state:
                raise ValueError(f"無法初始化爬取狀態: {board}")

            # 3. 檢查是否可以執行爬取
            if not force and crawl_state.status == CrawlStatus.CRAWLING:
                raise ValueError(f"看板 {board} 正在爬取中，請稍後再試或使用 --force 強制執行")

            # 4. 更新狀態為爬取中
            await self.crawl_state_repo.update_crawl_state(
                board, CrawlStatus.CRAWLING, error_message=None
            )

            # 5. 執行兩階段爬取
            phase1_result = await self._phase1_crawl_board_pages(
                board, category, pages, incremental, crawl_state
            )

            phase2_result = await self._phase2_crawl_article_content(
                phase1_result["article_links"], crawl_state
            )

            # 6. 更新最終狀態
            final_state = await self._finalize_crawl_state(
                board, phase1_result, phase2_result
            )

            # 7. 產生結果摘要
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            result = {
                "status": "success",
                "board": board,
                "category": category,
                "pages_crawled": phase1_result["pages_processed"],
                "articles_found": phase1_result["total_links"],
                "articles_new": phase2_result["articles_created"],
                "articles_updated": phase2_result["articles_updated"],
                "articles_skipped": phase2_result["articles_skipped"],
                "articles_failed": phase2_result["articles_failed"],
                "execution_time": duration,
                "incremental": incremental,
                "last_crawl_time": end_time.isoformat(),
            }

            logger.info(f"完成爬取: {result}")
            return result

        except Exception as e:
            logger.error(f"爬取失敗: {e}")

            # 記錄錯誤狀態
            await self.crawl_state_repo.update_crawl_state(
                board, CrawlStatus.ERROR, error_message=str(e)
            )

            # 增加重試次數
            await self.crawl_state_repo.increment_retry_count(board)

            raise

    async def _initialize_crawl_state(self, board: str, force: bool = False) -> None:
        """初始化爬取狀態."""
        existing_state = await self.crawl_state_repo.get_crawl_state(board)

        if not existing_state:
            # 首次爬取，建立新狀態
            await self.crawl_state_repo.init_crawl_state(board)
            logger.info(f"初始化新的爬取狀態: {board}")
        elif force:
            # 強制重新開始
            await self.crawl_state_repo.update_crawl_state(
                board, CrawlStatus.IDLE, error_message=None
            )
            await self.crawl_state_repo.reset_retry_count(board)
            logger.info(f"強制重置爬取狀態: {board}")

    async def _phase1_crawl_board_pages(
        self,
        board: str,
        category: Optional[str],
        pages: int,
        incremental: bool,
        crawl_state: CrawlState,
    ) -> Dict[str, Any]:
        """
        階段一：爬取看板頁面，取得文章連結列表.

        Returns:
            Dict包含: article_links, pages_processed, total_links
        """
        logger.info(f"階段一：開始爬取看板頁面 ({pages} 頁)")

        all_links = []
        pages_processed = 0

        for page_num in range(1, pages + 1):
            try:
                # 建構看板頁面 URL
                if page_num == 1:
                    board_url = f"https://www.ptt.cc/bbs/{board}/index.html"
                else:
                    board_url = f"https://www.ptt.cc/bbs/{board}/index{page_num}.html"

                logger.info(f"爬取頁面 {page_num}: {board_url}")

                # 使用 Firecrawl 爬取頁面
                response = await self.firecrawl.scrape_board_page(board_url)

                if not response.success:
                    logger.warning(f"頁面 {page_num} 爬取失敗: {response.error}")
                    continue

                # 提取文章連結
                page_links = self.firecrawl.extract_article_links(response.data)

                # 分類篩選
                if category:
                    page_links = self.firecrawl.filter_articles_by_category(page_links, category)

                # 增量爬取過濾
                if incremental:
                    page_links = self._filter_processed_links(page_links, crawl_state)

                all_links.extend(page_links)
                pages_processed += 1

                # 更新頁面進度
                await self.crawl_state_repo.update_crawl_state(
                    board, CrawlStatus.CRAWLING, last_page_crawled=page_num
                )

                # 速率限制
                await asyncio.sleep(self.request_delay)

            except FirecrawlError as e:
                logger.error(f"Firecrawl 錯誤 (頁面 {page_num}): {e}")
                if e.error_code in ["UNAUTHORIZED", "QUOTA_EXCEEDED"]:
                    raise  # 嚴重錯誤，停止爬取
                continue  # 其他錯誤繼續下一頁

            except Exception as e:
                logger.error(f"頁面爬取錯誤 (頁面 {page_num}): {e}")
                continue

        logger.info(f"階段一完成：處理 {pages_processed} 頁，找到 {len(all_links)} 個連結")

        return {
            "article_links": all_links,
            "pages_processed": pages_processed,
            "total_links": len(all_links),
        }

    def _filter_processed_links(
        self, links: List[Dict[str, str]], crawl_state: CrawlState
    ) -> List[Dict[str, str]]:
        """篩選出尚未處理的連結."""
        unprocessed_links = []

        for link in links:
            url = link.get("url", "")
            if not crawl_state.is_url_processed(url):
                unprocessed_links.append(link)

        logger.info(f"增量篩選：{len(links)} 個連結中 {len(unprocessed_links)} 個尚未處理")
        return unprocessed_links

    async def _phase2_crawl_article_content(
        self, article_links: List[Dict[str, str]], crawl_state: CrawlState
    ) -> Dict[str, Any]:
        """
        階段二：爬取文章內容並儲存到資料庫.

        Returns:
            Dict包含: articles_created, articles_updated, articles_skipped, articles_failed
        """
        logger.info(f"階段二：開始爬取文章內容 ({len(article_links)} 個連結)")

        articles_created = 0
        articles_updated = 0
        articles_skipped = 0
        articles_failed = 0

        # 使用信號量控制併發
        async def process_link(link_data: Dict[str, str]) -> None:
            nonlocal articles_created, articles_updated, articles_skipped, articles_failed

            async with self._semaphore:
                url = link_data.get("url", "")

                try:
                    # 檢查文章是否已存在
                    exists = await self.article_repo.article_exists(url)

                    if exists and not crawl_state.should_update_article(url):
                        articles_skipped += 1
                        await self.crawl_state_repo.add_processed_url(crawl_state.board, url)
                        return

                    # 爬取文章內容
                    response = await self.firecrawl.scrape_article_with_retry(url)

                    if not response.success:
                        logger.warning(f"文章爬取失敗: {url}")
                        articles_failed += 1
                        await self.crawl_state_repo.add_failed_url(crawl_state.board, url)
                        return

                    # 解析文章內容
                    article_data = await self.parser.parse_article(response.data, url)

                    if not article_data:
                        logger.warning(f"文章解析失敗: {url}")
                        articles_failed += 1
                        await self.crawl_state_repo.add_failed_url(crawl_state.board, url)
                        return

                    # 建立文章物件
                    article = Article(
                        id=0,  # 由資料庫生成
                        title=article_data["title"],
                        author=article_data["author"],
                        board=crawl_state.board,
                        url=url,
                        content=article_data["content"],
                        publish_date=article_data["publish_date"],
                        crawl_date=datetime.now(),
                        category=article_data.get("category"),
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                    )

                    # 儲存到資料庫
                    if exists:
                        success = await self.article_repo.update_article_content(
                            url, article.content
                        )
                        if success:
                            articles_updated += 1
                        else:
                            articles_failed += 1
                    else:
                        article_id = await self.article_repo.insert_article(article)
                        if article_id > 0:
                            articles_created += 1
                        else:
                            articles_failed += 1

                    # 記錄為已處理
                    await self.crawl_state_repo.add_processed_url(crawl_state.board, url)

                    # 速率限制
                    await asyncio.sleep(self.request_delay)

                except Exception as e:
                    logger.error(f"處理文章錯誤 ({url}): {e}")
                    articles_failed += 1
                    await self.crawl_state_repo.add_failed_url(crawl_state.board, url)

        # 並行處理所有連結
        tasks = [process_link(link) for link in article_links]
        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(f"階段二完成：新增 {articles_created}, 更新 {articles_updated}, 跳過 {articles_skipped}, 失敗 {articles_failed}")

        return {
            "articles_created": articles_created,
            "articles_updated": articles_updated,
            "articles_skipped": articles_skipped,
            "articles_failed": articles_failed,
        }

    async def _finalize_crawl_state(
        self,
        board: str,
        phase1_result: Dict[str, Any],
        phase2_result: Dict[str, Any],
    ) -> CrawlState:
        """完成爬取狀態更新."""
        # 判斷最終狀態
        if phase2_result["articles_failed"] == 0:
            final_status = CrawlStatus.COMPLETED
        elif phase2_result["articles_created"] + phase2_result["articles_updated"] > 0:
            final_status = CrawlStatus.COMPLETED  # 部分成功也算完成
        else:
            final_status = CrawlStatus.ERROR

        # 更新狀態
        await self.crawl_state_repo.update_crawl_state(
            board, final_status, error_message=None
        )

        # 重置重試次數（成功時）
        if final_status == CrawlStatus.COMPLETED:
            await self.crawl_state_repo.reset_retry_count(board)

        # 同步到 Redis 和 JSON
        crawl_state = await self.crawl_state_repo.get_crawl_state(board)
        if crawl_state:
            await self.state_service.sync_state_to_redis(crawl_state)
            await self.state_service.save_state_to_json(crawl_state)

        return crawl_state

    async def get_crawl_state(self, board: str) -> Optional[CrawlState]:
        """取得爬取狀態."""
        return await self.crawl_state_repo.get_crawl_state(board)

    async def get_crawl_statistics(self, board: str) -> Dict[str, Any]:
        """取得爬取統計資訊."""
        state = await self.crawl_state_repo.get_crawl_state(board)
        if not state:
            return {}

        article_count = await self.article_repo.count_articles_by_board(board)
        recent_articles = await self.article_repo.get_recent_articles(board, hours=24)

        return {
            "board": board,
            "status": state.status.value,
            "last_crawl_time": state.last_crawl_time,
            "total_articles": article_count,
            "recent_articles": len(recent_articles),
            "processed_urls": len(state.processed_urls),
            "failed_urls": len(state.failed_urls),
            "success_rate": state.get_success_rate(),
            "retry_count": state.retry_count,
        }

    async def retry_failed_urls(self, board: str) -> Dict[str, Any]:
        """重試失敗的 URL."""
        state = await self.crawl_state_repo.get_crawl_state(board)
        if not state or not state.failed_urls:
            return {"status": "no_failed_urls", "urls_retried": 0}

        logger.info(f"重試失敗的 URL: {len(state.failed_urls)} 個")

        # 建立假的連結資料
        failed_links = [{"url": url} for url in state.failed_urls.copy()]

        # 清空失敗列表，重新嘗試
        state.failed_urls.clear()
        await self.crawl_state_repo.update_crawl_state(
            board, CrawlStatus.CRAWLING
        )

        # 執行階段二爬取
        result = await self._phase2_crawl_article_content(failed_links, state)

        # 更新最終狀態
        await self._finalize_crawl_state(board, {"pages_processed": 0, "total_links": 0}, result)

        return {
            "status": "success",
            "urls_retried": len(failed_links),
            "articles_created": result["articles_created"],
            "articles_updated": result["articles_updated"],
            "articles_failed": result["articles_failed"],
        }

    async def get_current_config(self) -> Dict[str, Any]:
        """取得目前的配置."""
        return self.config.copy()

    async def reload_config(self) -> None:
        """重新載入配置."""
        # 這會在 config_loader 中實作
        pass

    async def cleanup_old_states(self, days: int = 30) -> int:
        """清理舊的爬取狀態."""
        return await self.crawl_state_repo.cleanup_old_states(days)