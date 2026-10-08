"""需求 3：志愿统计。

统计一律基于**清洗后的数据**（剔除了 ERROR 行的那部分），否则
"张三重复报了两次名"会把技术部的人数虚增一个。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .loader import Record
from .text import display_width, pad_left, pad_right

#: 第一志愿为空时在汇总表里的显示名。
UNFILLED_LABEL = "(未填)"

FILL_BOTH = "两个志愿都填了"
FILL_SINGLE = "只填了一个志愿"
FILL_NONE = "两个志愿都没填"

#: 汇总表里填写情况的展示顺序。
FILL_ORDER = (FILL_BOTH, FILL_SINGLE, FILL_NONE)


@dataclass
class Stats:
    """统计结果。"""

    total: int
    first_choice: list[tuple[str, int]]
    fill: dict[str, int]

    @property
    def choice_count(self) -> int:
        """第一志愿一共有几个不同的部门。"""
        return len(self.first_choice)


def build_stats(records: list[Record]) -> Stats:
    """按第一志愿分组统计人数，并统计志愿填写完整度。"""
    counter: Counter[str] = Counter(
        record.value("志愿1") or UNFILLED_LABEL for record in records
    )
    # 人数降序；人数相同按部门名升序，保证输出稳定可复现。
    first_choice = sorted(counter.items(), key=lambda item: (-item[1], item[0]))

    fill = {label: 0 for label in FILL_ORDER}
    for record in records:
        has_first = not record.is_blank("志愿1")
        has_second = not record.is_blank("志愿2")
        if has_first and has_second:
            fill[FILL_BOTH] += 1
        elif has_first or has_second:
            fill[FILL_SINGLE] += 1
        else:
            fill[FILL_NONE] += 1

    return Stats(total=len(records), first_choice=first_choice, fill=fill)


def _ratio(part: int, total: int) -> str:
    return "0.0%" if total == 0 else f"{part / total * 100:.1f}%"


def format_stats(stats: Stats, *, source_rows: int | None = None) -> str:
    """把统计结果排版成可直接打印的文本。"""
    lines: list[str] = []
    lines.append("=" * 56)
    lines.append(" 志愿统计（基于清洗后的数据）")
    lines.append("=" * 56)
    if source_rows is not None:
        lines.append(f"原始数据 : {source_rows} 行")
        lines.append(f"清洗后   : {stats.total} 行")

    lines.append("")
    lines.append(f"【第一志愿分组统计】共 {stats.choice_count} 个部门")
    name_width = max(
        [display_width(name) for name, _ in stats.first_choice] + [display_width("第一志愿")]
    )
    header = (
        f"{pad_right('第一志愿', name_width)}  {pad_left('人数', 5)}  {pad_left('占比', 7)}"
    )
    lines.append(header)
    lines.append("-" * display_width(header))
    for name, count in stats.first_choice:
        lines.append(
            f"{pad_right(name, name_width)}  {pad_left(str(count), 5)}  "
            f"{pad_left(_ratio(count, stats.total), 7)}"
        )
    lines.append(
        f"{pad_right('合计', name_width)}  {pad_left(str(stats.total), 5)}  "
        f"{pad_left('100.0%' if stats.total else '0.0%', 7)}"
    )

    lines.append("")
    lines.append("【志愿填写情况】")
    label_width = max(display_width(label) for label in FILL_ORDER)
    for label in FILL_ORDER:
        count = stats.fill[label]
        lines.append(
            f"  {pad_right(label, label_width)} : {pad_left(str(count), 4)} 人"
            f"  ({_ratio(count, stats.total)})"
        )
    return "\n".join(lines)
