"""终端表格排版用到的字符宽度工具。

中文字形在等宽终端里占两格，但 ``len("中")`` 是 1，
直接用 ``str.ljust`` 拼表格会歪。这里按 East Asian Width 计算显示宽度。
"""

from __future__ import annotations

import unicodedata


def display_width(text: str) -> int:
    """按终端显示宽度计算字符串长度（全角字符算 2 格）。"""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def pad_right(text: str, width: int) -> str:
    """按显示宽度右侧补空格。"""
    return text + " " * max(0, width - display_width(text))


def pad_left(text: str, width: int) -> str:
    """按显示宽度左侧补空格（数字列右对齐用）。"""
    return " " * max(0, width - display_width(text)) + text
