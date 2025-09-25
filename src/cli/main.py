"""PTT Crawler CLI main entry point.

This module provides the main CLI application using Typer.
"""
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import typer

# 設定 UTF-8 編碼
if sys.platform == "win32":
    # Windows 系統設定
    try:
        # 嘗試設定控制台編碼
        os.system("chcp 65001 >nul")
    except:
        pass

from .clean_command import clean
from .config_command import config
from .crawl_command import crawl
from .status_command import status

# Create main app
app = typer.Typer(
    name="ptt-crawler",
    help="PTT Stock 板爬蟲工具，支援依分類篩選文章並使用 Firecrawl API 爬取內容",
    no_args_is_help=True,
)

# Add subcommands
app.add_typer(config, name="config", help="配置管理")
app.command()(crawl)
app.command()(status)
app.command()(clean)

# Global context storage
global_config = {
    "config_file": None,
    "log_level": "INFO",
    "dry_run": False,
}


# Global options
@app.callback()
def main(
    config_file: Optional[Path] = typer.Option(None, "--config-file", help="配置檔案路徑"),
    log_level: str = typer.Option(
        "INFO", "--log-level", help="日誌級別 [DEBUG|INFO|WARNING|ERROR]"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="模擬執行，不實際爬取或寫入資料庫"),
):
    """PTT Crawler - PTT Stock 板爬蟲工具."""
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Store global options
    global_config["config_file"] = config_file
    global_config["log_level"] = log_level
    global_config["dry_run"] = dry_run


if __name__ == "__main__":
    app()
