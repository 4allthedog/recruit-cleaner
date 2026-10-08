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

from . import overview as overview_module
from . import validator as validator_module
from .exporter import issues_csv_path, write_issues_csv
from .loader import CsvFormatError, DEFAULT_ENCODING, load_csv

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
    _add_encoding_argument(overview)

    validate = subcommands.add_parser(
        "validate", help="需求 2：校验学号/邮箱/重复报名，并导出问题清单"
    )
    _add_input_argument(validate)
    _add_encoding_argument(validate)
    _add_out_dir_argument(validate)
    _add_id_length_argument(validate)

    return parser


def _add_input_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "csv",
        nargs="?",
        default=DEFAULT_INPUT,
        help=f"输入的报名表 CSV 路径（默认 {DEFAULT_INPUT}）",
    )


def _add_encoding_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--encoding",
        default=DEFAULT_ENCODING,
        help=f"输入文件编码（默认 {DEFAULT_ENCODING}，GBK 老文件请用 gbk）",
    )


def _add_out_dir_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--out-dir",
        default=DEFAULT_OUT_DIR,
        help=f"产物输出目录（默认 {DEFAULT_OUT_DIR}）",
    )


def _add_id_length_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--id-length",
        type=int,
        default=None,
        help="学号位数。默认不校验位数；若确认学号统一为 N 位，传 --id-length N",
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        columns, records = load_csv(args.csv, encoding=args.encoding)
    except (FileNotFoundError, CsvFormatError) as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 1

    column_tuple = tuple(columns)

    if args.command == "overview":
        overview = overview_module.build_overview(records, column_tuple)
        print(overview_module.format_overview(overview, column_tuple, source=args.csv))
        return 0

    if args.command == "validate":
        result = validator_module.validate(records, column_tuple, id_length=args.id_length)
        print(validator_module.format_validation_report(result))
        path = write_issues_csv(result, issues_csv_path(args.out_dir), column_tuple)
        print()
        print(f"问题清单已导出：{path}")
        return 0

    print(f"[错误] 暂不支持的子命令：{args.command}", file=sys.stderr)
    return 1
