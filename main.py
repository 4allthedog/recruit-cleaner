#!/usr/bin/env python3
"""协会招新报名数据清洗工具 —— 命令行入口。

零依赖，直接用系统里的 python3 跑::

    python main.py overview
    python main.py --help

详见 README.md。
"""

from __future__ import annotations

import sys

from recruit_clean.cli import main

if __name__ == "__main__":
    sys.exit(main())
