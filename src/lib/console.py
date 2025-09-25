"""Console utilities for safe character output.

This module provides utilities for handling console output with proper encoding.
"""
import sys
from typing import Any


def safe_echo(message: Any, **kwargs) -> None:
    """
    安全輸出訊息，處理編碼問題.

    Args:
        message: 要輸出的訊息
        **kwargs: 額外參數傳給 print
    """
    try:
        # 嘗試直接輸出
        print(message, **kwargs)
    except UnicodeEncodeError:
        # 如果編碼失敗，轉換為安全格式
        if isinstance(message, str):
            # 將中文字符轉為可顯示格式
            safe_message = message.encode("ascii", "replace").decode("ascii")
            print(f"[ENCODING_ISSUE] {safe_message}", **kwargs)
        else:
            print(f"[OUTPUT] {message!r}", **kwargs)


def format_chinese_safe(template: str, *args, **kwargs) -> str:
    """
    安全格式化包含中文的字串.

    Args:
        template: 模板字串
        *args: 位置參數
        **kwargs: 關鍵字參數

    Returns:
        str: 格式化後的安全字串
    """
    try:
        return template.format(*args, **kwargs)
    except UnicodeError:
        # 如果有編碼問題，使用英文替代
        english_template = (
            template.replace("顯示", "show").replace("配置", "config").replace("設定", "set")
        )
        return english_template.format(*args, **kwargs)


def setup_console_encoding():
    """設定控制台編碼."""
    if sys.platform == "win32":
        try:
            # Windows 系統嘗試設定 UTF-8
            import os

            os.system("chcp 65001 >nul")

            # 設定標準輸出編碼
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8")
            if hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(encoding="utf-8")

        except Exception:
            # 如果設定失敗，繼續執行
            pass


# 提供常用的中英文對照
MESSAGES = {
    "zh": {
        "config_show": "顯示配置",
        "config_set": "設定配置",
        "config_reset": "重置配置",
        "crawl_start": "開始爬取",
        "crawl_category": "篩選分類",
        "crawl_pages": "爬取頁面",
        "status_query": "查詢狀態",
        "clean_start": "開始清理",
        "error_not_implemented": "功能尚未實作",
    },
    "en": {
        "config_show": "Show config",
        "config_set": "Set config",
        "config_reset": "Reset config",
        "crawl_start": "Start crawling",
        "crawl_category": "Filter category",
        "crawl_pages": "Crawl pages",
        "status_query": "Query status",
        "clean_start": "Start cleaning",
        "error_not_implemented": "Feature not implemented yet",
    },
}


def get_message(key: str, lang: str = "zh", fallback_lang: str = "en") -> str:
    """
    取得訊息文字.

    Args:
        key: 訊息鍵
        lang: 語言 (zh/en)
        fallback_lang: 備用語言

    Returns:
        str: 訊息文字
    """
    try:
        return MESSAGES[lang][key]
    except KeyError:
        try:
            return MESSAGES[fallback_lang][key]
        except KeyError:
            return key.upper().replace("_", " ")


def echo_with_prefix(prefix: str, message: str, lang: str = "zh") -> None:
    """
    輸出帶前綴的訊息.

    Args:
        prefix: 前綴 (如 CONFIG, CRAWL 等)
        message: 訊息鍵或直接訊息
        lang: 語言設定
    """
    # 檢查是否為訊息鍵
    if message in MESSAGES.get(lang, {}):
        text = get_message(message, lang)
    else:
        text = message

    safe_echo(f"[{prefix}] {text}")


# 初始化控制台編碼
setup_console_encoding()
