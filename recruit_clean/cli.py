"""命令行入口。

用法见 README，一句话版::

    python main.py overview            # 需求 1：概览
    python main.py validate            # 需求 2：校验 + 导出问题清单
    python main.py stats               # 需求 3：志愿统计
    python main.py export              # 需求 3：导出干净数据
    python main.py all                 # 一条龙
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .loader import CsvFormatError, DEFAULT_ENCODING, load_csv
from . import overview as overview_module

#: 不传路径时默认读仓库自带的样例数据，方便 clone 下来直接跑。
DEFAULT_INPUT = str(Path("data") / "sample_recruits.csv")
DEFAULT_OUT_DIR = "output"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="协会招新报名数据清洗工具（只读原文件，绝不原地修改）",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    overview = subcommands.add_parser("overview", help="需求 1：读入 CSV 并打印概览")
    _add_input_argument(overview)
    overview.add_argument(
        "--encoding", default=DEFAULT_ENCODING, help=f"输入文件编码（默认 {DEFAULT_ENCODING}）"
    )

    return parser


def _add_input_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "csv",
        nargs="?",
        default=DEFAULT_INPUT,
        help=f"输入的报名表 CSV 路径（默认 {DEFAULT_INPUT}）",
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        columns, records = load_csv(args.csv, encoding=args.encoding)
    except (FileNotFoundError, CsvFormatError) as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 1

    if args.command == "overview":
        overview = overview_module.build_overview(records, tuple(columns))
        print(overview_module.format_overview(overview, tuple(columns), source=args.csv))
        return 0

    print(f"[错误] 暂不支持的子命令：{args.command}", file=sys.stderr)
    return 1
