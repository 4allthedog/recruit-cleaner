"""需求 1：读入报名 CSV。

问卷导出的 CSV 有两个常见坑，这里一并处理掉：

1. **BOM**：问卷星/腾讯问卷导出的 UTF-8 文件常带 BOM，直接 ``utf-8`` 打开
   会把第一列表头读成 ``\\ufeff姓名``。统一用 ``utf-8-sig`` 读取可自动去掉。
2. **看不见的空格**：字段里可能混着首尾空格或全角空格，导致"看起来是空的
   但其实有个空格"。读取时保留原值，同时提供 ``value()`` 取 strip 后的值。
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

#: 报名表约定的列。顺序即输出时的默认顺序。
REQUIRED_COLUMNS: tuple[str, ...] = ("姓名", "学号", "邮箱", "志愿1", "志愿2", "推荐人")

#: 默认编码。utf-8-sig 同时兼容"带 BOM"和"不带 BOM"的 UTF-8 文件。
DEFAULT_ENCODING = "utf-8-sig"


class CsvFormatError(Exception):
    """输入 CSV 的结构不符合约定（空文件、缺列等）时抛出。"""


@dataclass(frozen=True)
class Record:
    """一行报名记录。

    Attributes:
        index: 数据行序号，从 1 开始（不含表头）。
        line_no: 在源文件中的行号，从 2 开始（表头占第 1 行）。
            报错时用它定位到 Excel 里确切的那一行。
        values: 列名 -> 原始字段值（未 strip）。
    """

    index: int
    line_no: int
    values: dict[str, str]

    def raw(self, column: str) -> str:
        """字段原始值（保留首尾空格）。"""
        return self.values.get(column, "")

    def value(self, column: str) -> str:
        """字段值，去掉首尾空白（含全角空格）。"""
        return self.raw(column).strip()

    def is_blank(self, column: str) -> bool:
        """该字段是否为空。空字符串和纯空白都算空。"""
        return self.value(column) == ""

    def fingerprint(self, columns: tuple[str, ...] = REQUIRED_COLUMNS) -> tuple[str, ...]:
        """判断"完全重复的行"用的指纹：所有字段 strip 后拼成的元组。"""
        return tuple(self.value(column) for column in columns)

    def summary(self) -> str:
        """给人类看的一行摘要，用于在报错里指出是哪条记录。"""
        return f"{self.value('姓名') or '(无姓名)'} / {self.value('学号') or '(无学号)'}"


def load_csv(
    path: str | Path,
    encoding: str = DEFAULT_ENCODING,
) -> tuple[list[str], list[Record]]:
    """读入报名 CSV。

    Args:
        path: CSV 文件路径。
        encoding: 文件编码，默认 ``utf-8-sig``（兼容带 BOM 的问卷导出文件）。

    Returns:
        ``(表头列名列表, 记录列表)``。

    Raises:
        FileNotFoundError: 文件不存在。
        CsvFormatError: 文件为空、没有表头，或缺少必需的列。
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"找不到输入文件：{path}")

    with path.open("r", encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle)
        header = reader.fieldnames
        if not header:
            raise CsvFormatError(f"{path} 是空文件，或者缺少表头行")

        header = [name.strip() for name in header if name is not None]
        missing = [column for column in REQUIRED_COLUMNS if column not in header]
        if missing:
            raise CsvFormatError(
                f"表头缺少必需的列：{'、'.join(missing)}。实际表头为：{header}"
            )

        records: list[Record] = []
        for offset, row in enumerate(reader, start=1):
            values = {column: (row.get(column) or "") for column in header}
            records.append(Record(index=offset, line_no=offset + 1, values=values))

    return header, records
