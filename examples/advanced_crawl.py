#!/usr/bin/env python3
"""
PTT Stock 爬蟲進階使用範例

此範例展示進階功能，包含：
- 批次爬取多個分類
- 增量爬取與狀態管理
- 錯誤處理與重試機制
- 效能監控與資源管理
- 自訂資料處理與分析
"""

import asyncio
import logging
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil

# 添加專案根目錄到 Python 路徑
sys.path.append(str(Path(__file__).parent.parent))

from src.lib.config_loader import ConfigLoader
from src.lib.logging import setup_logging
from src.lib.redis_client import RedisClient
from src.repositories.article_repository import ArticleRepository
from src.services.crawl_service import CrawlService
from src.services.parser_service import ParserService
from src.services.state_service import StateService


class AdvancedCrawler:
    """進階爬蟲類別，包含豐富的功能和監控"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.start_time = None
        self.start_memory = None
        self.crawl_statistics = defaultdict(int)

    async def initialize_services(self) -> dict[str, Any]:
        """初始化所有服務"""
        self.logger.info("初始化進階爬蟲服務...")

        # 載入配置
        config_loader = ConfigLoader()
        config = await config_loader.load_config()

        # 初始化服務
        services = {
            "redis_client": RedisClient(
                url=config.get("REDIS_URL", "redis://localhost:6379"),
                retry_attempts=3,
                retry_delay=1.0,
            ),
            "state_service": None,
            "parser_service": ParserService(),
            "article_repository": ArticleRepository(
                connection_string=config.get(
                    "DATABASE_URL", "postgresql://ptt_user:password@localhost:5432/ptt_crawler"
                )
            ),
            "crawl_service": None,
            "config": config,
        }

        services["state_service"] = StateService(redis_client=services["redis_client"])
        services["crawl_service"] = CrawlService(
            state_service=services["state_service"],
            parser_service=services["parser_service"],
            article_repository=services["article_repository"],
            firecrawl_api_url=config.get("FIRECRAWL_API_URL", "http://localhost:3002"),
            firecrawl_api_key=config.get("FIRECRAWL_API_KEY"),
        )

        return services

    def start_monitoring(self):
        """開始效能監控"""
        self.start_time = time.time()
        self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        self.logger.info(f"開始監控 - 初始記憶體使用: {self.start_memory:.2f} MB")

    def log_current_stats(self):
        """記錄當前統計資訊"""
        current_time = time.time()
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024

        elapsed = current_time - self.start_time
        memory_delta = current_memory - self.start_memory

        self.logger.info(
            f"執行時間: {elapsed:.2f}s, 記憶體使用: {current_memory:.2f}MB ({memory_delta:+.2f}MB)"
        )

    async def batch_crawl_categories(self, services: dict[str, Any]) -> dict[str, Any]:
        """批次爬取多個分類"""
        print("🎯 批次爬取多個分類")
        print("-" * 30)

        # 定義要爬取的分類
        categories = ["心得", "標的", "請益", "新聞"]
        results = {}

        for category in categories:
            print(f"\n📝 正在爬取分類: {category}")
            self.log_current_stats()

            try:
                result = await services["crawl_service"].crawl_board(
                    board="Stock",
                    category=category,
                    pages=3,  # 每個分類爬 3 頁
                    incremental=True,  # 使用增量爬取
                    force=False,
                )

                results[category] = result
                self.crawl_statistics[f"{category}_articles"] = result["articles_crawled"]
                self.crawl_statistics[f"{category}_errors"] = result["errors_count"]

                print(
                    f"   ✅ {category}: {result['articles_crawled']} 篇文章, {result['errors_count']} 個錯誤"
                )

                # 短暫延遲以避免過度請求
                await asyncio.sleep(2)

            except Exception as e:
                self.logger.error(f"爬取分類 {category} 失敗: {e}")
                results[category] = {"status": "failed", "error": str(e)}
                print(f"   ❌ {category}: 爬取失敗 - {e}")

        return results

    async def incremental_crawl_demo(self, services: dict[str, Any]):
        """增量爬取示範"""
        print("\n🔄 增量爬取示範")
        print("-" * 20)

        # 第一次爬取
        print("第一次爬取（建立基線）...")
        result1 = await services["crawl_service"].crawl_board(
            board="Stock",
            category="心得",
            pages=2,
            incremental=False,  # 不使用增量
            force=True,  # 強制爬取
        )
        print(f"   第一次爬取: {result1['articles_crawled']} 篇文章")

        # 等待一段時間
        print("等待 5 秒後進行增量爬取...")
        await asyncio.sleep(5)

        # 第二次爬取（增量）
        print("第二次爬取（增量模式）...")
        result2 = await services["crawl_service"].crawl_board(
            board="Stock",
            category="心得",
            pages=2,
            incremental=True,  # 使用增量
            force=False,
        )
        print(f"   增量爬取: {result2['articles_crawled']} 篇新文章")

        # 比較結果
        print("\n📊 增量爬取效果:")
        print(f"   第一次爬取: {result1['articles_crawled']} 篇")
        print(f"   增量爬取: {result2['articles_crawled']} 篇")
        print(f"   節省時間: {result1['duration'] - result2['duration']:.2f} 秒")

    async def error_handling_demo(self, services: dict[str, Any]):
        """錯誤處理示範"""
        print("\n🛡️ 錯誤處理示範")
        print("-" * 18)

        # 測試網路錯誤恢復
        print("測試服務降級（Redis 失效時降級到 JSON）...")

        original_redis_url = services["config"].get("REDIS_URL")

        try:
            # 暫時使用錯誤的 Redis URL 來模擬服務不可用
            services["redis_client"]._redis_url = "redis://invalid-host:6379"

            # 執行爬取，應該會自動降級到 JSON 狀態管理
            result = await services["crawl_service"].crawl_board(
                board="Stock", category="心得", pages=1, incremental=True, force=False
            )

            print(f"   ✅ 服務降級成功，爬取 {result['articles_crawled']} 篇文章")
            print(f"   ⚠️ 錯誤數量: {result['errors_count']}")

        except Exception as e:
            print(f"   ⚠️ 預期的錯誤: {e}")

        finally:
            # 恢復原始 Redis URL
            services["redis_client"]._redis_url = original_redis_url

    async def data_analysis_demo(self, services: dict[str, Any]):
        """資料分析示範"""
        print("\n📈 資料分析示範")
        print("-" * 16)

        # 查詢最近的文章
        articles = await services["article_repository"].get_articles_by_board(
            board="Stock", limit=50
        )

        if not articles:
            print("   ⚠️ 沒有找到文章資料")
            return

        # 分析文章分類分布
        category_count = defaultdict(int)
        author_count = defaultdict(int)
        content_lengths = []

        for article in articles:
            if article.category:
                category_count[article.category] += 1
            author_count[article.author] += 1
            content_lengths.append(len(article.content))

        print(f"📊 分析 {len(articles)} 篇文章:")

        # 分類分布
        print("\n   分類分布:")
        for category, count in sorted(category_count.items(), key=lambda x: x[1], reverse=True):
            percentage = count / len(articles) * 100
            print(f"     {category}: {count} 篇 ({percentage:.1f}%)")

        # 活躍作者
        print("\n   最活躍作者 (前5名):")
        for author, count in sorted(author_count.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"     {author}: {count} 篇")

        # 內容長度統計
        if content_lengths:
            avg_length = sum(content_lengths) / len(content_lengths)
            max_length = max(content_lengths)
            min_length = min(content_lengths)
            print("\n   內容長度統計:")
            print(f"     平均: {avg_length:.0f} 字")
            print(f"     最長: {max_length} 字")
            print(f"     最短: {min_length} 字")

    async def export_analysis_results(self, services: dict[str, Any]):
        """匯出分析結果"""
        print("\n💾 匯出分析結果")
        print("-" * 16)

        # 查詢資料
        articles = await services["article_repository"].get_articles_by_board(
            board="Stock", limit=100
        )

        if not articles:
            print("   ⚠️ 沒有資料可匯出")
            return

        # 建立匯出目錄
        output_dir = Path("examples/output/advanced_analysis")
        output_dir.mkdir(parents=True, exist_ok=True)

        # 匯出詳細 JSON
        import json

        detailed_data = []
        for article in articles:
            detailed_data.append(
                {
                    "id": article.id,
                    "title": article.title,
                    "author": article.author,
                    "category": article.category,
                    "board": article.board,
                    "content_length": len(article.content),
                    "content_summary": article.content[:200] + "..."
                    if len(article.content) > 200
                    else article.content,
                    "publish_date": article.publish_date.isoformat(),
                    "crawl_date": article.crawl_date.isoformat(),
                    "keywords": services["parser_service"].extract_keywords(
                        article.content, max_keywords=5
                    ),
                }
            )

        json_file = (
            output_dir / f"detailed_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(detailed_data, f, ensure_ascii=False, indent=2)

        print(f"   ✅ JSON 匯出: {json_file}")

        # 匯出 CSV 摘要
        import csv

        csv_file = output_dir / f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["標題", "作者", "分類", "內容長度", "發布時間"])
            for article in articles:
                writer.writerow(
                    [
                        article.title,
                        article.author,
                        article.category or "無分類",
                        len(article.content),
                        article.publish_date.strftime("%Y-%m-%d %H:%M:%S"),
                    ]
                )

        print(f"   ✅ CSV 匯出: {csv_file}")

    def print_final_statistics(self):
        """顯示最終統計"""
        print("\n📊 執行統計摘要")
        print("=" * 30)

        total_time = time.time() - self.start_time
        total_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_delta = total_memory - self.start_memory

        print(f"總執行時間: {total_time:.2f} 秒")
        print(f"記憶體使用: {total_memory:.2f} MB (變化: {memory_delta:+.2f} MB)")

        if self.crawl_statistics:
            print("\n分類爬取統計:")
            for key, value in self.crawl_statistics.items():
                print(f"  {key}: {value}")

        total_articles = sum(v for k, v in self.crawl_statistics.items() if k.endswith("_articles"))
        total_errors = sum(v for k, v in self.crawl_statistics.items() if k.endswith("_errors"))

        if total_articles > 0:
            success_rate = (total_articles - total_errors) / total_articles * 100
            articles_per_second = total_articles / total_time
            print("\n總體效能:")
            print(f"  爬取文章總數: {total_articles}")
            print(f"  錯誤總數: {total_errors}")
            print(f"  成功率: {success_rate:.1f}%")
            print(f"  爬取速度: {articles_per_second:.2f} 篇/秒")

    async def run_advanced_demo(self):
        """執行進階示範"""
        print("🚀 PTT Stock 爬蟲進階功能示範")
        print("=" * 50)

        services = None
        try:
            # 初始化服務
            self.start_monitoring()
            services = await self.initialize_services()

            print("✅ 服務初始化完成")

            # 執行各項示範
            await self.batch_crawl_categories(services)
            await self.incremental_crawl_demo(services)
            await self.error_handling_demo(services)
            await self.data_analysis_demo(services)
            await self.export_analysis_results(services)

        except Exception as e:
            self.logger.error(f"進階示範執行失敗: {e}")
            print(f"❌ 執行失敗: {e}")

        finally:
            # 清理資源
            if services:
                if services["redis_client"]:
                    await services["redis_client"].close()
                if services["article_repository"]:
                    await services["article_repository"].close()

            self.print_final_statistics()
            print("\n🎯 進階功能示範完成")


async def interactive_menu():
    """互動式選單"""
    print("🌟 PTT Stock 爬蟲進階功能選單")
    print("=" * 40)
    print("1. 執行完整進階示範")
    print("2. 僅執行批次分類爬取")
    print("3. 僅執行增量爬取示範")
    print("4. 僅執行資料分析")
    print("5. 查看效能建議")
    print("0. 離開")

    while True:
        try:
            choice = input("\n請選擇功能 (0-5): ").strip()

            if choice == "0":
                print("👋 謝謝使用!")
                break
            elif choice == "1":
                crawler = AdvancedCrawler()
                await crawler.run_advanced_demo()
                break
            elif choice == "2":
                print("🎯 執行批次分類爬取...")
                crawler = AdvancedCrawler()
                services = await crawler.initialize_services()
                crawler.start_monitoring()
                try:
                    await crawler.batch_crawl_categories(services)
                finally:
                    await services["redis_client"].close()
                    await services["article_repository"].close()
                    crawler.print_final_statistics()
                break
            elif choice == "3":
                print("🔄 執行增量爬取示範...")
                crawler = AdvancedCrawler()
                services = await crawler.initialize_services()
                crawler.start_monitoring()
                try:
                    await crawler.incremental_crawl_demo(services)
                finally:
                    await services["redis_client"].close()
                    await services["article_repository"].close()
                    crawler.print_final_statistics()
                break
            elif choice == "4":
                print("📈 執行資料分析...")
                crawler = AdvancedCrawler()
                services = await crawler.initialize_services()
                crawler.start_monitoring()
                try:
                    await crawler.data_analysis_demo(services)
                    await crawler.export_analysis_results(services)
                finally:
                    await services["redis_client"].close()
                    await services["article_repository"].close()
                    crawler.print_final_statistics()
                break
            elif choice == "5":
                show_performance_tips()
                continue
            else:
                print("❌ 無效選擇，請輸入 0-5")
                continue

        except KeyboardInterrupt:
            print("\n\n👋 使用者中斷，程式結束")
            break
        except Exception as e:
            print(f"❌ 執行錯誤: {e}")
            break


def show_performance_tips():
    """顯示效能建議"""
    print("\n💡 效能最佳化建議")
    print("-" * 25)
    print("1. 調整爬取參數:")
    print("   - request_delay: 1.0-2.0 秒 (根據網路狀況)")
    print("   - rate_limit: 30-100 (每分鐘請求數)")
    print("   - concurrent_limit: 2-5 (並發數)")

    print("\n2. 資料庫最佳化:")
    print("   - 增加 shared_buffers 到 256MB+")
    print("   - 設定 work_mem 到 16MB+")
    print("   - 啟用查詢計畫快取")

    print("\n3. Redis 最佳化:")
    print("   - 啟用 AOF 持久化")
    print("   - 設定適當的 maxmemory")
    print("   - 使用 allkeys-lru 逐出策略")

    print("\n4. 系統資源:")
    print("   - 監控記憶體使用量")
    print("   - 確保足夠的磁碟空間")
    print("   - 網路頻寬至少 10Mbps")


if __name__ == "__main__":
    # 設定日誌
    setup_logging(level=logging.INFO)

    print("🚀 歡迎使用 PTT Stock 爬蟲進階功能!")
    print("   本示範展示批次爬取、增量爬取、錯誤處理等進階功能")
    print("   請確保系統已正確配置並有足夠資源\n")

    try:
        asyncio.run(interactive_menu())
    except KeyboardInterrupt:
        print("\n\n👋 使用者中斷，程式結束")
    except Exception as e:
        print(f"\n❌ 程式錯誤: {e}")
