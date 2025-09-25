#!/usr/bin/env python3
"""
PTT Stock 爬蟲系統健康檢查腳本

此腳本用於監控爬蟲系統的各個組件狀態，包含：
- 資料庫連線狀態
- Redis 連線狀態
- Firecrawl API 可用性
- 磁碟空間使用
- 記憶體使用狀況
- 日誌檔案大小
- 爬取狀態統計

使用方式:
    python health_check.py                    # 基本健康檢查
    python health_check.py --detailed         # 詳細檢查
    python health_check.py --json            # JSON 格式輸出
    python health_check.py --alert           # 檢查異常時發送告警
    python health_check.py --fix             # 嘗試自動修復問題
"""

import asyncio
import json
import logging
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import aiohttp
import psutil

# 添加專案根目錄到 Python 路徑
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.lib.config_loader import ConfigLoader
from src.lib.logging import setup_logging
from src.lib.redis_client import RedisClient
from src.repositories.article_repository import ArticleRepository


@dataclass
class HealthStatus:
    """健康狀態資料類別"""

    component: str
    status: str  # healthy, warning, critical
    message: str
    details: dict[str, Any] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.details is None:
            self.details = {}


class SystemHealthChecker:
    """系統健康檢查器"""

    def __init__(self, config: dict[str, str]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.health_results: list[HealthStatus] = []

        # 閾值設定
        self.thresholds = {
            "disk_usage_warning": 80,  # 磁碟使用率警告閾值 (%)
            "disk_usage_critical": 90,  # 磁碟使用率危險閾值 (%)
            "memory_usage_warning": 80,  # 記憶體使用率警告閾值 (%)
            "memory_usage_critical": 90,  # 記憶體使用率危險閾值 (%)
            "log_file_warning": 100,  # 日誌檔案大小警告閾值 (MB)
            "log_file_critical": 500,  # 日誌檔案大小危險閾值 (MB)
            "redis_latency_warning": 100,  # Redis 延遲警告閾值 (ms)
            "redis_latency_critical": 500,  # Redis 延遲危險閾值 (ms)
        }

    async def check_database_health(self) -> HealthStatus:
        """檢查資料庫健康狀態"""
        try:
            repository = ArticleRepository(
                connection_string=self.config.get(
                    "DATABASE_URL", "postgresql://ptt_user:password@localhost:5432/ptt_crawler"
                )
            )

            start_time = datetime.now()
            is_healthy = await repository.health_check()
            latency = (datetime.now() - start_time).total_seconds() * 1000

            if is_healthy:
                # 獲取資料庫統計
                try:
                    stats = await repository.get_database_stats()
                    await repository.close()

                    return HealthStatus(
                        component="database",
                        status="healthy",
                        message="資料庫連線正常",
                        details={
                            "latency_ms": round(latency, 2),
                            "total_articles": stats.get("total_articles", 0),
                            "total_boards": stats.get("total_boards", 0),
                            "last_crawl": stats.get("last_crawl_time"),
                            "connection_string": self._mask_password(
                                self.config.get("DATABASE_URL", "")
                            ),
                        },
                    )
                except Exception as e:
                    await repository.close()
                    return HealthStatus(
                        component="database",
                        status="warning",
                        message="資料庫連線正常但統計資料獲取失敗",
                        details={"error": str(e), "latency_ms": round(latency, 2)},
                    )
            else:
                await repository.close()
                return HealthStatus(
                    component="database",
                    status="critical",
                    message="資料庫連線失敗",
                    details={"latency_ms": round(latency, 2)},
                )

        except Exception as e:
            return HealthStatus(
                component="database",
                status="critical",
                message=f"資料庫檢查失敗: {e!s}",
                details={"error": str(e)},
            )

    async def check_redis_health(self) -> HealthStatus:
        """檢查 Redis 健康狀態"""
        try:
            redis_client = RedisClient(
                url=self.config.get("REDIS_URL", "redis://localhost:6379"),
                retry_attempts=1,
                retry_delay=0.5,
            )

            start_time = datetime.now()
            health = await redis_client.health_check()
            latency = (datetime.now() - start_time).total_seconds() * 1000

            await redis_client.close()

            if health["status"] == "healthy":
                status = "healthy"
                if latency > self.thresholds["redis_latency_critical"]:
                    status = "critical"
                elif latency > self.thresholds["redis_latency_warning"]:
                    status = "warning"

                return HealthStatus(
                    component="redis",
                    status=status,
                    message=f"Redis 連線正常 (延遲: {latency:.2f}ms)",
                    details={
                        "latency_ms": round(latency, 2),
                        "redis_version": health.get("version"),
                        "memory_used": health.get("memory_used"),
                        "connected_clients": health.get("connected_clients"),
                        "url": self._mask_password(self.config.get("REDIS_URL", "")),
                    },
                )
            else:
                return HealthStatus(
                    component="redis",
                    status="critical",
                    message=f"Redis 連線失敗: {health.get('error', 'Unknown error')}",
                    details={"error": health.get("error"), "latency_ms": round(latency, 2)},
                )

        except Exception as e:
            return HealthStatus(
                component="redis",
                status="critical",
                message=f"Redis 檢查失敗: {e!s}",
                details={"error": str(e)},
            )

    async def check_firecrawl_health(self) -> HealthStatus:
        """檢查 Firecrawl API 健康狀態"""
        try:
            api_url = self.config.get("FIRECRAWL_API_URL", "http://localhost:3002")
            health_endpoint = f"{api_url}/health"

            start_time = datetime.now()

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(health_endpoint, timeout=10) as response:
                        latency = (datetime.now() - start_time).total_seconds() * 1000

                        if response.status == 200:
                            try:
                                data = await response.json()
                                return HealthStatus(
                                    component="firecrawl",
                                    status="healthy",
                                    message="Firecrawl API 運行正常",
                                    details={
                                        "latency_ms": round(latency, 2),
                                        "status_code": response.status,
                                        "api_url": api_url,
                                        "response_data": data,
                                    },
                                )
                            except:
                                # JSON 解析失敗，但狀態碼正常
                                return HealthStatus(
                                    component="firecrawl",
                                    status="warning",
                                    message="Firecrawl API 回應格式異常",
                                    details={
                                        "latency_ms": round(latency, 2),
                                        "status_code": response.status,
                                        "api_url": api_url,
                                    },
                                )
                        else:
                            return HealthStatus(
                                component="firecrawl",
                                status="critical",
                                message=f"Firecrawl API 回應異常 (狀態碼: {response.status})",
                                details={
                                    "latency_ms": round(latency, 2),
                                    "status_code": response.status,
                                    "api_url": api_url,
                                },
                            )

                except asyncio.TimeoutError:
                    return HealthStatus(
                        component="firecrawl",
                        status="critical",
                        message="Firecrawl API 連線逾時",
                        details={"api_url": api_url, "timeout": 10},
                    )

        except Exception as e:
            return HealthStatus(
                component="firecrawl",
                status="critical",
                message=f"Firecrawl API 檢查失敗: {e!s}",
                details={"error": str(e), "api_url": api_url},
            )

    def check_disk_usage(self) -> HealthStatus:
        """檢查磁碟空間使用狀況"""
        try:
            project_root = Path(__file__).parent.parent.parent
            disk_usage = psutil.disk_usage(str(project_root))

            used_percent = (disk_usage.used / disk_usage.total) * 100
            free_gb = disk_usage.free / (1024**3)

            status = "healthy"
            if used_percent >= self.thresholds["disk_usage_critical"]:
                status = "critical"
            elif used_percent >= self.thresholds["disk_usage_warning"]:
                status = "warning"

            return HealthStatus(
                component="disk",
                status=status,
                message=f"磁碟使用率 {used_percent:.1f}% (可用: {free_gb:.1f} GB)",
                details={
                    "used_percent": round(used_percent, 2),
                    "total_gb": round(disk_usage.total / (1024**3), 2),
                    "used_gb": round(disk_usage.used / (1024**3), 2),
                    "free_gb": round(free_gb, 2),
                    "path": str(project_root),
                },
            )

        except Exception as e:
            return HealthStatus(
                component="disk",
                status="critical",
                message=f"磁碟檢查失敗: {e!s}",
                details={"error": str(e)},
            )

    def check_memory_usage(self) -> HealthStatus:
        """檢查記憶體使用狀況"""
        try:
            memory = psutil.virtual_memory()
            used_percent = memory.percent
            available_gb = memory.available / (1024**3)

            status = "healthy"
            if used_percent >= self.thresholds["memory_usage_critical"]:
                status = "critical"
            elif used_percent >= self.thresholds["memory_usage_warning"]:
                status = "warning"

            return HealthStatus(
                component="memory",
                status=status,
                message=f"記憶體使用率 {used_percent:.1f}% (可用: {available_gb:.1f} GB)",
                details={
                    "used_percent": round(used_percent, 2),
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "available_gb": round(available_gb, 2),
                },
            )

        except Exception as e:
            return HealthStatus(
                component="memory",
                status="critical",
                message=f"記憶體檢查失敗: {e!s}",
                details={"error": str(e)},
            )

    def check_log_files(self) -> HealthStatus:
        """檢查日誌檔案大小"""
        try:
            project_root = Path(__file__).parent.parent.parent
            log_dir = project_root / "logs"

            if not log_dir.exists():
                return HealthStatus(
                    component="logs",
                    status="warning",
                    message="日誌目錄不存在",
                    details={"log_dir": str(log_dir)},
                )

            log_files = list(log_dir.glob("*.log"))
            total_size_mb = 0
            large_files = []

            for log_file in log_files:
                size_mb = log_file.stat().st_size / (1024 * 1024)
                total_size_mb += size_mb

                if size_mb > self.thresholds["log_file_critical"]:
                    large_files.append({"file": log_file.name, "size_mb": round(size_mb, 2)})

            status = "healthy"
            message = f"日誌檔案總大小: {total_size_mb:.1f} MB ({len(log_files)} 個檔案)"

            if total_size_mb > self.thresholds["log_file_critical"]:
                status = "critical"
                message += " - 檔案過大，建議清理"
            elif total_size_mb > self.thresholds["log_file_warning"]:
                status = "warning"
                message += " - 檔案較大，建議關注"

            return HealthStatus(
                component="logs",
                status=status,
                message=message,
                details={
                    "total_size_mb": round(total_size_mb, 2),
                    "file_count": len(log_files),
                    "log_dir": str(log_dir),
                    "large_files": large_files,
                },
            )

        except Exception as e:
            return HealthStatus(
                component="logs",
                status="critical",
                message=f"日誌檢查失敗: {e!s}",
                details={"error": str(e)},
            )

    async def check_crawl_statistics(self) -> HealthStatus:
        """檢查爬取統計"""
        try:
            repository = ArticleRepository(
                connection_string=self.config.get(
                    "DATABASE_URL", "postgresql://ptt_user:password@localhost:5432/ptt_crawler"
                )
            )

            # 獲取爬取統計
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            week_ago = today - timedelta(days=7)

            stats = {
                "total_articles": await repository.count_articles(),
                "today_articles": await repository.count_articles_by_date(today),
                "yesterday_articles": await repository.count_articles_by_date(yesterday),
                "week_articles": await repository.count_articles_since_date(week_ago),
            }

            await repository.close()

            # 判斷狀態
            status = "healthy"
            message = f"總文章數: {stats['total_articles']}, 今日: {stats['today_articles']}"

            if stats["today_articles"] == 0 and datetime.now().hour > 12:
                status = "warning"
                message += " - 今日尚無新文章"

            return HealthStatus(
                component="crawl_stats", status=status, message=message, details=stats
            )

        except Exception as e:
            return HealthStatus(
                component="crawl_stats",
                status="critical",
                message=f"爬取統計檢查失敗: {e!s}",
                details={"error": str(e)},
            )

    async def run_all_checks(self, detailed: bool = False) -> dict[str, Any]:
        """執行所有健康檢查"""
        self.logger.info("開始執行系統健康檢查...")

        # 基本檢查項目
        basic_checks = [
            self.check_database_health(),
            self.check_redis_health(),
            self.check_firecrawl_health(),
        ]

        # 詳細檢查項目
        detailed_checks = [
            self.check_disk_usage(),
            self.check_memory_usage(),
            self.check_log_files(),
            self.check_crawl_statistics(),
        ]

        # 執行檢查
        if detailed:
            all_checks = basic_checks + detailed_checks
        else:
            all_checks = basic_checks

        self.health_results = await asyncio.gather(*all_checks)

        # 統計結果
        healthy_count = sum(1 for r in self.health_results if r.status == "healthy")
        warning_count = sum(1 for r in self.health_results if r.status == "warning")
        critical_count = sum(1 for r in self.health_results if r.status == "critical")

        overall_status = "healthy"
        if critical_count > 0:
            overall_status = "critical"
        elif warning_count > 0:
            overall_status = "warning"

        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "summary": {
                "total_checks": len(self.health_results),
                "healthy": healthy_count,
                "warning": warning_count,
                "critical": critical_count,
            },
            "checks": [asdict(result) for result in self.health_results],
        }

    def _mask_password(self, connection_string: str) -> str:
        """遮罩連線字串中的密碼"""
        import re

        return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", connection_string)

    async def attempt_auto_fix(self) -> dict[str, str]:
        """嘗試自動修復問題"""
        fixes = {}

        for result in self.health_results:
            if result.status in ["warning", "critical"]:
                fix_result = await self._auto_fix_component(result)
                if fix_result:
                    fixes[result.component] = fix_result

        return fixes

    async def _auto_fix_component(self, health_status: HealthStatus) -> Optional[str]:
        """嘗試修復特定組件問題"""
        component = health_status.component

        try:
            if component == "logs" and "大" in health_status.message:
                # 清理大型日誌檔案
                project_root = Path(__file__).parent.parent.parent
                log_dir = project_root / "logs"

                # 壓縮舊日誌檔案
                import gzip
                import shutil

                fixed_count = 0
                for log_file in log_dir.glob("*.log"):
                    if log_file.stat().st_size > 50 * 1024 * 1024:  # 50MB
                        with open(log_file, "rb") as f_in:
                            with gzip.open(f"{log_file}.gz", "wb") as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        log_file.unlink()
                        fixed_count += 1

                if fixed_count > 0:
                    return f"已壓縮 {fixed_count} 個大型日誌檔案"

            elif component == "disk" and "critical" in health_status.status:
                # 清理暫時檔案
                project_root = Path(__file__).parent.parent.parent
                tmp_dir = project_root / "tmp"

                if tmp_dir.exists():
                    import shutil

                    shutil.rmtree(tmp_dir)
                    tmp_dir.mkdir()
                    return "已清理暫時檔案目錄"

        except Exception as e:
            self.logger.error(f"自動修復 {component} 失敗: {e}")
            return None

        return None


def print_health_report(health_data: dict[str, Any], detailed: bool = False):
    """印出健康檢查報告"""
    print("\n" + "=" * 60)
    print("🏥 PTT Stock 爬蟲系統健康檢查報告")
    print("=" * 60)
    print(f"檢查時間: {health_data['timestamp']}")
    print(
        f"整體狀態: {get_status_emoji(health_data['overall_status'])} {health_data['overall_status'].upper()}"
    )

    summary = health_data["summary"]
    print(f"檢查項目: {summary['total_checks']} 項")
    print(f"正常: {summary['healthy']} | 警告: {summary['warning']} | 嚴重: {summary['critical']}")
    print()

    # 顯示各組件狀態
    for check in health_data["checks"]:
        emoji = get_status_emoji(check["status"])
        print(f"{emoji} {check['component'].upper()}: {check['message']}")

        if detailed and check["details"]:
            for key, value in check["details"].items():
                if key != "error":  # 錯誤資訊單獨顯示
                    print(f"    {key}: {value}")

            if "error" in check["details"]:
                print(f"    ❌ 錯誤: {check['details']['error']}")
        print()


def get_status_emoji(status: str) -> str:
    """獲取狀態表情符號"""
    return {"healthy": "✅", "warning": "⚠️", "critical": "❌"}.get(status, "❓")


async def main():
    """主程式"""
    import argparse

    parser = argparse.ArgumentParser(description="PTT Stock 爬蟲系統健康檢查")
    parser.add_argument("--detailed", action="store_true", help="執行詳細檢查")
    parser.add_argument("--json", action="store_true", help="JSON 格式輸出")
    parser.add_argument("--alert", action="store_true", help="異常時發送告警")
    parser.add_argument("--fix", action="store_true", help="嘗試自動修復問題")
    parser.add_argument("--config-file", type=str, help="配置檔案路徑")

    args = parser.parse_args()

    # 設定日誌
    setup_logging(level=logging.WARNING if args.json else logging.INFO)

    try:
        # 載入配置
        config_loader = ConfigLoader()
        config = await config_loader.load_config(
            config_file=Path(args.config_file) if args.config_file else None
        )

        # 建立健康檢查器
        checker = SystemHealthChecker(config)

        # 執行檢查
        health_data = await checker.run_all_checks(detailed=args.detailed)

        # 自動修復
        if args.fix:
            fixes = await checker.attempt_auto_fix()
            if fixes:
                health_data["auto_fixes"] = fixes
                # 重新檢查
                health_data = await checker.run_all_checks(detailed=args.detailed)

        # 輸出結果
        if args.json:
            print(json.dumps(health_data, indent=2, ensure_ascii=False))
        else:
            print_health_report(health_data, detailed=args.detailed)

            if health_data.get("auto_fixes"):
                print("🔧 自動修復結果:")
                for component, fix_msg in health_data["auto_fixes"].items():
                    print(f"  {component}: {fix_msg}")

        # 告警處理
        if args.alert and health_data["overall_status"] in ["warning", "critical"]:
            # 這裡可以整合告警系統，如發送郵件、Slack 通知等
            print("\n📢 系統狀態異常，需要關注！")

        # 設定退出碼
        if health_data["overall_status"] == "critical":
            sys.exit(2)
        elif health_data["overall_status"] == "warning":
            sys.exit(1)
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        print("\n👋 健康檢查被中斷")
        sys.exit(130)
    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}, ensure_ascii=False))
        else:
            print(f"❌ 健康檢查執行失敗: {e}")
        sys.exit(3)


if __name__ == "__main__":
    asyncio.run(main())
