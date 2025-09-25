#!/usr/bin/env python3
"""
PTT Stock 爬蟲基本使用範例

此範例展示最基本的使用方式，適合初次使用者學習。
包含基本爬取、狀態查詢、資料匯出等核心功能。
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
sys.path.append(str(Path(__file__).parent.parent))

from src.lib.config_loader import ConfigLoader
from src.lib.logging import setup_logging
from src.lib.redis_client import RedisClient
from src.repositories.article_repository import ArticleRepository
from src.services.crawl_service import CrawlService
from src.services.parser_service import ParserService
from src.services.state_service import StateService


async def basic_crawl_example():
    """基本爬取範例"""
    print("🚀 PTT Stock 爬蟲基本使用範例")
    print("=" * 50)

    # 設定日誌
    setup_logging(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        # 1. 初始化服務
        print("\n📋 步驟 1: 初始化服務...")

        # 載入配置
        config_loader = ConfigLoader()
        config = await config_loader.load_config()

        # 初始化 Redis 客戶端
        redis_client = RedisClient(
            url=config.get("REDIS_URL", "redis://localhost:6379"), retry_attempts=3, retry_delay=1.0
        )

        # 初始化各項服務
        state_service = StateService(redis_client=redis_client)
        parser_service = ParserService()
        article_repository = ArticleRepository(
            connection_string=config.get(
                "DATABASE_URL", "postgresql://ptt_user:password@localhost:5432/ptt_crawler"
            )
        )

        crawl_service = CrawlService(
            state_service=state_service,
            parser_service=parser_service,
            article_repository=article_repository,
            firecrawl_api_url=config.get("FIRECRAWL_API_URL", "http://localhost:3002"),
            firecrawl_api_key=config.get("FIRECRAWL_API_KEY"),
        )

        print("✅ 服務初始化完成")

        # 2. 檢查系統狀態
        print("\n📊 步驟 2: 檢查系統狀態...")

        # 測試 Redis 連線
        redis_status = await redis_client.health_check()
        print(f"   Redis 連線: {'✅ 正常' if redis_status['status'] == 'healthy' else '❌ 異常'}")

        # 測試資料庫連線
        db_status = await article_repository.health_check()
        print(f"   資料庫連線: {'✅ 正常' if db_status else '❌ 異常'}")

        if redis_status["status"] != "healthy" and not db_status:
            print("❌ 系統狀態異常，請檢查配置")
            return

        print("✅ 系統狀態正常")

        # 3. 執行基本爬取
        print("\n🔍 步驟 3: 執行基本爬取...")
        print("   目標: Stock 板")
        print("   分類: 心得")
        print("   頁數: 2 頁")

        result = await crawl_service.crawl_board(
            board="Stock",
            category="心得",
            pages=2,
            incremental=False,  # 不使用增量爬取，獲取最新資料
            force=False,
        )

        # 4. 顯示爬取結果
        print("\n📈 步驟 4: 爬取結果摘要")
        print(f"   執行狀態: {result['status']}")
        print(f"   總執行時間: {result['duration']:.2f} 秒")
        print(f"   爬取文章數: {result['articles_crawled']} 篇")
        print(f"   新增文章數: {result['articles_saved']} 篇")
        print(f"   錯誤數量: {result['errors_count']}")

        if result["errors_count"] > 0:
            print("   錯誤詳情:")
            for error in result.get("errors", [])[:3]:  # 只顯示前 3 個錯誤
                print(f"     - {error}")

        # 5. 查詢爬取狀態
        print("\n📋 步驟 5: 查詢 Stock 板爬取狀態...")

        board_state = await state_service.get_board_state("Stock")
        if board_state:
            print(f"   最後爬取時間: {board_state.last_crawl_time}")
            print(f"   爬取頁數: {board_state.last_page_crawled}")
            print(f"   總文章數: {board_state.total_articles}")
            print(f"   成功率: {board_state.success_rate:.1%}")
        else:
            print("   未找到爬取狀態記錄")

        # 6. 資料匯出範例
        print("\n💾 步驟 6: 資料匯出範例...")

        # 從資料庫查詢最新文章
        latest_articles = await article_repository.get_articles_by_board(board="Stock", limit=5)

        if latest_articles:
            print(f"   查詢到 {len(latest_articles)} 篇最新文章:")
            for i, article in enumerate(latest_articles, 1):
                print(f"     {i}. [{article.category}] {article.title[:30]}...")
                print(f"        作者: {article.author} | 時間: {article.publish_date}")

            # 匯出為 JSON 檔案
            import json

            output_file = Path("examples/output/basic_crawl_result.json")
            output_file.parent.mkdir(exist_ok=True)

            export_data = []
            for article in latest_articles:
                export_data.append(
                    {
                        "title": article.title,
                        "author": article.author,
                        "category": article.category,
                        "content": article.content[:200] + "..."
                        if len(article.content) > 200
                        else article.content,
                        "publish_date": article.publish_date.isoformat(),
                        "board": article.board,
                    }
                )

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            print(f"   ✅ 資料已匯出到: {output_file}")
        else:
            print("   未找到文章資料")

    except Exception as e:
        logger.error(f"範例執行失敗: {e}")
        print(f"\n❌ 執行失敗: {e}")

    finally:
        # 清理資源
        if "redis_client" in locals():
            await redis_client.close()
        if "article_repository" in locals():
            await article_repository.close()

        print("\n🎯 基本使用範例執行完成")
        print("\n💡 提示:")
        print("   - 查看匯出的 JSON 檔案了解資料格式")
        print("   - 可以修改爬取參數（board、category、pages）")
        print("   - 使用 incremental=True 進行增量爬取")
        print("   - 查看日誌檔案了解詳細執行過程")


async def show_configuration_example():
    """顯示配置範例"""
    print("\n⚙️ 配置範例")
    print("-" * 30)

    print("1. 基本配置 (適合開發環境):")
    print(
        """
    DATABASE_URL=postgresql://ptt_user:password@localhost:5432/ptt_crawler
    REDIS_URL=redis://localhost:6379
    FIRECRAWL_API_URL=http://localhost:3002
    LOG_LEVEL=INFO
    CRAWL_RATE_LIMIT=60
    CRAWL_REQUEST_DELAY=1.5
    """
    )

    print("2. 生產環境配置:")
    print(
        """
    DATABASE_URL=postgresql://prod_user:secure_pass@prod_db:5432/ptt_crawler
    REDIS_URL=redis://prod_redis:6379
    FIRECRAWL_API_URL=https://api.firecrawl.dev
    FIRECRAWL_API_KEY=fc-your-api-key
    LOG_LEVEL=WARNING
    CRAWL_RATE_LIMIT=30
    CRAWL_REQUEST_DELAY=2.0
    """
    )


def show_common_commands():
    """顯示常用命令範例"""
    print("\n📝 常用 CLI 命令範例")
    print("-" * 35)

    commands = [
        ("基本爬取", "ptt-crawler crawl Stock --pages 3"),
        ("分類過濾", "ptt-crawler crawl Stock --category '心得' --pages 5"),
        ("增量爬取", "ptt-crawler crawl Stock --incremental"),
        ("匯出 JSON", "ptt-crawler crawl Stock --output json --output-file output.json"),
        ("匯出 CSV", "ptt-crawler crawl Stock --output csv --output-file output.csv"),
        ("系統狀態", "ptt-crawler status"),
        ("看板狀態", "ptt-crawler status Stock"),
        ("清理狀態", "ptt-crawler clean --states --older-than 30"),
        ("查看配置", "ptt-crawler config show"),
        ("設定配置", "ptt-crawler config set crawl.rate_limit 60"),
    ]

    for desc, cmd in commands:
        print(f"   {desc:12} : {cmd}")


if __name__ == "__main__":
    print("🌟 歡迎使用 PTT Stock 爬蟲工具!")
    print("   本範例將演示基本的爬取流程")
    print("   請確保已正確安裝和配置所有依賴服務\n")

    # 顯示配置和命令範例
    show_configuration_example()
    show_common_commands()

    # 詢問是否執行範例
    try:
        user_input = input("\n是否執行基本爬取範例? (y/N): ").strip().lower()
        if user_input in ["y", "yes", "是"]:
            asyncio.run(basic_crawl_example())
        else:
            print("👋 謝謝使用，範例結束")
    except KeyboardInterrupt:
        print("\n\n👋 使用者中斷，範例結束")
    except Exception as e:
        print(f"\n❌ 執行錯誤: {e}")
