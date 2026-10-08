"""需求 1：数据概览 —— 多少行、每列多少空值、有没有完全重复的行。"""

from __future__ import annotations

from dataclasses import dataclass, field

from .loader import REQUIRED_COLUMNS, Record
from .text import display_width, pad_left, pad_right


@dataclass
class DuplicateGroup:
    """一组内容完全相同的行。

    ``indexes`` 按出现顺序排列，第一个是"首次出现"，其余是"重复出现"。
    """

    fingerprint: tuple[str, ...]
    indexes: list[int] = field(default_factory=list)

    @property
    def first_index(self) -> int:
        return self.indexes[0]

    @property
    def duplicate_indexes(self) -> list[int]:
        """重复出现的行（不含首次出现的那一行）。"""
        return self.indexes[1:]

    @property
    def size(self) -> int:
        return len(self.indexes)


@dataclass
class Overview:
    """概览结果。"""

    total_rows: int
    blank_counts: dict[str, int]
    duplicate_groups: list[DuplicateGroup]

    @property
    def has_duplicate_rows(self) -> bool:
        return bool(self.duplicate_groups)

    @property
    def duplicate_row_count(self) -> int:
        """重复出现的行总数（每组首次出现的那一行不算重复）。"""
        return sum(len(group.duplicate_indexes) for group in self.duplicate_groups)

    @property
    def blank_cell_total(self) -> int:
        return sum(self.blank_counts.values())


def build_overview(
    records: list[Record],
    columns: tuple[str, ...] = REQUIRED_COLUMNS,
) -> Overview:
    """统计总行数、每列空值数、完全重复的行。

    "完全重复"指 strip 之后所有字段都完全一致的行（表头行不参与比较）。
    """
    blank_counts = {
        column: sum(1 for record in records if record.is_blank(column))
        for column in columns
    }

    buckets: dict[tuple[str, ...], list[int]] = {}
    for record in records:
        buckets.setdefault(record.fingerprint(columns), []).append(record.index)

    duplicate_groups = [
        DuplicateGroup(fingerprint=fingerprint, indexes=indexes)
        for fingerprint, indexes in buckets.items()
        if len(indexes) > 1
    ]
    duplicate_groups.sort(key=lambda group: group.first_index)

    return Overview(
        total_rows=len(records),
        blank_counts=blank_counts,
        duplicate_groups=duplicate_groups,
    )


def _ratio(part: int, total: int) -> str:
    return "0.0%" if total == 0 else f"{part / total * 100:.1f}%"


def format_overview(
    overview: Overview,
    columns: tuple[str, ...] = REQUIRED_COLUMNS,
    source: str = "",
) -> str:
    """把概览结果排版成可直接打印的文本。"""
    lines: list[str] = []
    lines.append("=" * 56)
    lines.append(" 数据概览")
    lines.append("=" * 56)
    if source:
        lines.append(f"输入文件 : {source}")
    lines.append(f"数据行数 : {overview.total_rows} 行（不含表头）")
    lines.append(f"统计列数 : {len(columns)} 列")

    lines.append("")
    lines.append("【每列空值】空值 = 空字符串或只有空白字符")
    name_width = max(display_width(column) for column in columns)
    header = f"{pad_right('列名', name_width)}  {pad_left('空值数', 6)}  {pad_left('空值占比', 8)}"
    lines.append(header)
    lines.append("-" * display_width(header))
    for column in columns:
        blank = overview.blank_counts[column]
        lines.append(
            f"{pad_right(column, name_width)}  {pad_left(str(blank), 6)}  "
            f"{pad_left(_ratio(blank, overview.total_rows), 8)}"
        )
    lines.append(f"合计空单元格：{overview.blank_cell_total} 个")

    lines.append("")
    lines.append("【完全重复的行】")
    if not overview.has_duplicate_rows:
        lines.append("未发现完全重复的行。")
    else:
        lines.append(
            f"发现 {len(overview.duplicate_groups)} 组完全重复的行，"
            f"共 {overview.duplicate_row_count} 行属于重复出现："
        )
        for group in overview.duplicate_groups:
            for index in group.duplicate_indexes:
                lines.append(
                    f"  · 第 {index} 行 与 第 {group.first_index} 行 完全相同"
                )
    return "\n".join(lines)
