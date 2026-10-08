"""导出工具：问题清单（需求 2）。

导出统一用 **带 BOM 的 UTF-8**：不带 BOM 的话 Excel 双击打开中文会乱码，
而招新负责人几乎一定会用 Excel 看这份清单。
"""

from __future__ import annotations

import csv
from pathlib import Path

from .loader import REQUIRED_COLUMNS, Record
from .stats import FILL_ORDER, Stats
from .validator import ValidationResult

#: 导出文件编码。
OUTPUT_ENCODING = "utf-8-sig"


def write_csv(path: str | Path, header: list[str], rows: list[list[object]]) -> Path:
    """写一张 CSV 表（自动创建父目录）。返回实际写入的路径。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=OUTPUT_ENCODING, newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def write_issues_csv(
    result: ValidationResult,
    path: str | Path,
    columns: tuple[str, ...] = REQUIRED_COLUMNS,
) -> Path:
    """导出问题清单：一行一条有问题的记录，并写清每一行的判错理由。

    列：数据行号、源文件行号、原始各字段、严重级别、问题代码、问题说明。
    一行可能同时命中多个问题，问题代码用 ``;`` 连接，问题说明用 `` | `` 连接。
    """
    records_by_index = {record.index: record for record in result.records}

    header = ["数据行号", "源文件行号", *columns, "严重级别", "问题代码", "问题说明"]
    rows: list[list[object]] = []
    for index in result.problem_indexes:
        record = records_by_index[index]
        issues = result.issues_by_index[index]
        rows.append(
            [
                record.index,
                record.line_no,
                *[record.value(column) for column in columns],
                result.severity_of_index(index),
                ";".join(issue.code for issue in issues),
                " | ".join(f"[{issue.code}] {issue.reason}" for issue in issues),
            ]
        )
    return write_csv(path, header, rows)


def write_records_csv(
    records: list[Record],
    path: str | Path,
    columns: tuple[str, ...] = REQUIRED_COLUMNS,
) -> Path:
    """导出干净数据。

    写入的是 strip 后的值——脏空格已经被清掉了。除此之外不改写原值
    （比如邮箱域名的大小写保持原样，方便跟问题清单对照）。
    """
    rows = [[record.value(column) for column in columns] for record in records]
    return write_csv(path, list(columns), rows)


def write_stats_csv(stats: Stats, path: str | Path) -> Path:
    """导出第一志愿汇总表：第一志愿 / 人数 / 占比。"""
    total = stats.total or 1
    rows = [
        [name, count, f"{count / total * 100:.1f}%"] for name, count in stats.first_choice
    ]
    return write_csv(path, ["第一志愿", "人数", "占比"], rows)


def write_fill_csv(stats: Stats, path: str | Path) -> Path:
    """导出志愿填写情况：填写情况 / 人数 / 占比。"""
    total = stats.total or 1
    rows = [
        [label, stats.fill[label], f"{stats.fill[label] / total * 100:.1f}%"]
        for label in FILL_ORDER
    ]
    return write_csv(path, ["填写情况", "人数", "占比"], rows)


def issues_csv_path(out_dir: str | Path) -> Path:
    """问题清单的默认输出路径。"""
    return Path(out_dir) / "issues.csv"


def clean_csv_path(out_dir: str | Path) -> Path:
    """干净数据的默认输出路径。"""
    return Path(out_dir) / "clean.csv"


def stats_csv_path(out_dir: str | Path) -> Path:
    """第一志愿汇总表的默认输出路径。"""
    return Path(out_dir) / "stats_first_choice.csv"


def fill_csv_path(out_dir: str | Path) -> Path:
    """志愿填写情况的默认输出路径。"""
    return Path(out_dir) / "stats_choice_fill.csv"
