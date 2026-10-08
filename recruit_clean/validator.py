"""需求 2：校验与清洗。

三条硬规则：

1. 学号必须是**纯数字**（ASCII 0-9；全角数字、罗马数字等一律算错）；
2. 邮箱必须是 ``学号@smbu.edu.cn``（域名大小写不敏感，对不上就是填错了）；
3. 同一学号出现两次 = 重复报名。

外加两条提醒（不剔除，只提示补填）：姓名为空、第一志愿为空。

校验**只输出问题清单，不改动原文件**。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .loader import REQUIRED_COLUMNS, Record
from .text import display_width, pad_left, pad_right

#: 学校邮箱域名。
EMAIL_DOMAIN = "smbu.edu.cn"

ERROR = "ERROR"
WARN = "WARN"

#: 问题代码 -> 简短标题。严重级别由代码前缀决定：E = 错误（剔除），W = 提醒（保留）。
ISSUE_CATALOG: dict[str, str] = {
    "E001": "学号为空",
    "E002": "学号不是纯数字",
    "E003": "学号位数不符",
    "E004": "邮箱为空",
    "E005": "邮箱域名或格式错误",
    "E006": "邮箱与学号不匹配",
    "E007": "学号重复报名",
    "E008": "整行完全重复",
    "W101": "姓名为空",
    "W102": "第一志愿为空",
}


def severity_of(code: str) -> str:
    """由问题代码推断严重级别。"""
    return ERROR if code.startswith("E") else WARN


def is_pure_digits(text: str) -> bool:
    """是否是纯 ASCII 数字。

    注意 ``str.isdigit()`` 会把全角数字 ``２０２３``、阿拉伯-印度数字 ``٢٠٢٣``
    也判为 True，这里额外要求 ``isascii()``。
    """
    return text.isascii() and text.isdigit()


@dataclass(frozen=True)
class Issue:
    """一条具体问题。"""

    record: Record
    code: str
    reason: str

    @property
    def severity(self) -> str:
        return severity_of(self.code)

    @property
    def title(self) -> str:
        return ISSUE_CATALOG[self.code]

    @property
    def line_no(self) -> int:
        return self.record.line_no


@dataclass
class ValidationResult:
    """校验结果。"""

    records: list[Record]
    issues: list[Issue] = field(default_factory=list)

    @property
    def issues_by_index(self) -> dict[int, list[Issue]]:
        """数据行序号 -> 该行的全部问题。"""
        bucket: dict[int, list[Issue]] = {}
        for issue in self.issues:
            bucket.setdefault(issue.record.index, []).append(issue)
        return bucket

    @property
    def problem_indexes(self) -> list[int]:
        """有问题的行（含提醒级），按行号升序。"""
        return sorted(self.issues_by_index)

    @property
    def dropped_indexes(self) -> set[int]:
        """被剔除的行：只要有一个 ERROR 级问题就剔除。"""
        return {issue.record.index for issue in self.issues if issue.severity == ERROR}

    @property
    def clean_records(self) -> list[Record]:
        """清洗后的干净数据：剔除所有 ERROR 级行，保留提醒级行。"""
        dropped = self.dropped_indexes
        return [record for record in self.records if record.index not in dropped]

    def count_by_code(self) -> Counter:
        return Counter(issue.code for issue in self.issues)

    def severity_of_index(self, index: int) -> str:
        return (
            ERROR
            if any(issue.severity == ERROR for issue in self.issues_by_index[index])
            else WARN
        )


def _check_student_id(record: Record, id_length: int | None) -> list[tuple[str, str]]:
    student_id = record.value("学号")
    if student_id == "":
        return [("E001", "学号为空，无法确认身份，也无法核对邮箱")]
    if not is_pure_digits(student_id):
        return [("E002", f"学号必须是纯数字，实际填写为「{student_id}」")]
    if id_length is not None and len(student_id) != id_length:
        return [
            (
                "E003",
                f"学号应为 {id_length} 位，实际为 {len(student_id)} 位（{student_id}）",
            )
        ]
    return []


def _check_email(record: Record) -> list[tuple[str, str]]:
    student_id = record.value("学号")
    email = record.value("邮箱")

    if email == "":
        return [("E004", "邮箱为空，无法发送面试通知")]
    if email.count("@") != 1:
        return [("E005", f"邮箱格式不正确（应恰好一个 @）：「{email}」")]

    prefix, domain = email.split("@")
    if domain.casefold() != EMAIL_DOMAIN:
        return [("E005", f"邮箱域名应为 {EMAIL_DOMAIN}，实际填写为 @{domain}")]
    if student_id == "":
        # 学号都空了，无从核对，E001 已经报过，这里不重复报。
        return []
    if prefix.casefold() != student_id.casefold():
        return [
            ("E006", f"邮箱前缀「{prefix}」与学号「{student_id}」不一致，疑似填错")
        ]
    return []


def _find_id_duplicates(records: list[Record]) -> dict[int, int]:
    """同一学号出现多次：返回 {重复行的 index -> 首次出现行的 index}。学号为空的行不参与。"""
    first_seen: dict[str, int] = {}
    duplicates: dict[int, int] = {}
    for record in records:
        student_id = record.value("学号")
        if student_id == "":
            continue
        if student_id in first_seen:
            duplicates[record.index] = first_seen[student_id]
        else:
            first_seen[student_id] = record.index
    return duplicates


def _find_exact_duplicates(
    records: list[Record], columns: tuple[str, ...]
) -> dict[int, int]:
    """整行完全重复：返回 {重复行的 index -> 首次出现行的 index}。"""
    first_seen: dict[tuple[str, ...], int] = {}
    duplicates: dict[int, int] = {}
    for record in records:
        fingerprint = record.fingerprint(columns)
        if fingerprint in first_seen:
            duplicates[record.index] = first_seen[fingerprint]
        else:
            first_seen[fingerprint] = record.index
    return duplicates


def validate(
    records: list[Record],
    columns: tuple[str, ...] = REQUIRED_COLUMNS,
    id_length: int | None = None,
) -> ValidationResult:
    """逐行校验。

    Args:
        records: ``load_csv`` 读出的记录。
        columns: 参与"完全重复"比较的列。
        id_length: 若指定，额外校验学号位数；``None`` 表示不校验位数。

    Returns:
        :class:`ValidationResult`，含问题清单与清洗后的记录。
    """
    id_duplicates = _find_id_duplicates(records)
    exact_duplicates = _find_exact_duplicates(records, columns)

    result = ValidationResult(records=records)
    for record in records:
        found: list[tuple[str, str]] = []
        found.extend(_check_student_id(record, id_length))
        found.extend(_check_email(record))

        if record.index in id_duplicates:
            first = id_duplicates[record.index]
            found.append(
                (
                    "E007",
                    f"学号 {record.value('学号')} 重复报名，"
                    f"首次出现在第 {first} 行（只保留首次那条）",
                )
            )
        if record.index in exact_duplicates:
            first = exact_duplicates[record.index]
            found.append(("E008", f"整行内容与第 {first} 行完全一致，疑似重复提交"))

        if record.is_blank("姓名"):
            found.append(("W101", "姓名为空，需人工补填（该行仍予以保留）"))
        if record.is_blank("志愿1"):
            found.append(("W102", "第一志愿为空，该同学无法参与志愿分组统计"))

        for code, reason in found:
            result.issues.append(Issue(record=record, code=code, reason=reason))

    return result


def format_validation_report(result: ValidationResult) -> str:
    """把校验结果排版成可直接打印的文本。"""
    total = len(result.records)
    problems = result.problem_indexes
    dropped = result.dropped_indexes
    warn_only = [index for index in problems if index not in dropped]

    lines: list[str] = []
    lines.append("=" * 56)
    lines.append(" 校验结果")
    lines.append("=" * 56)
    lines.append(f"总行数     : {total} 行")
    lines.append(f"有问题的行 : {len(problems)} 行")
    lines.append(f"  错误(剔除) : {len(dropped)} 行")
    lines.append(f"  提醒(保留) : {len(warn_only)} 行")
    lines.append(f"清洗后剩余 : {total - len(dropped)} 行")

    lines.append("")
    lines.append("【按问题类型统计】")
    counts = result.count_by_code()
    code_width = max(display_width(code) for code in counts) if counts else 4
    title_width = max(display_width(ISSUE_CATALOG[code]) for code in counts) if counts else 4
    for code, count in sorted(counts.items()):
        lines.append(
            f"  {pad_right(code, code_width)}  {pad_right(ISSUE_CATALOG[code], title_width)}"
            f"  {pad_left(str(count), 3)} 处"
        )

    lines.append("")
    lines.append("【问题明细】")
    if not problems:
        lines.append("  没有发现任何问题，数据很干净。")
    for index in problems:
        record = result.records[index - 1]
        severity = result.severity_of_index(index)
        lines.append(
            f"  第 {record.line_no} 行 [{severity}] {record.summary()}"
        )
        for issue in result.issues_by_index[index]:
            lines.append(f"      - {issue.code} {issue.title}：{issue.reason}")
    return "\n".join(lines)
