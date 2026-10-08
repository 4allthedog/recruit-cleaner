"""需求 2 的校验规则测试。

跑法（仓库根目录）：

    python -m unittest discover -s tests -t .
"""

from __future__ import annotations

import unittest

from recruit_clean.loader import REQUIRED_COLUMNS, Record
from recruit_clean.validator import validate

COLUMNS = REQUIRED_COLUMNS


def make_record(
    index: int,
    *,
    name: str = "张三",
    student_id: str = "2023010101",
    email: str = "2023010101@smbu.edu.cn",
    first: str = "技术部",
    second: str = "",
    referrer: str = "",
) -> Record:
    """造一条记录，默认是一份完全合法的报名。"""
    return Record(
        index=index,
        line_no=index + 1,
        values={
            "姓名": name,
            "学号": student_id,
            "邮箱": email,
            "志愿1": first,
            "志愿2": second,
            "推荐人": referrer,
        },
    )


def codes_of(result, index: int) -> set[str]:
    return {issue.code for issue in result.issues_by_index.get(index, [])}


class StudentIdRuleTest(unittest.TestCase):
    def test_valid_row_has_no_issue(self):
        result = validate([make_record(1)])
        self.assertEqual(result.issues, [])

    def test_student_id_must_be_pure_digits(self):
        result = validate([make_record(1, student_id="20230101AB", email="20230101AB@smbu.edu.cn")])
        self.assertIn("E002", codes_of(result, 1))

    def test_full_width_digits_are_rejected(self):
        """全角数字 str.isdigit() 会放行，这里必须拦住。"""
        result = validate([make_record(1, student_id="２０２３０１０１０１", email="２０２３０１０１０１@smbu.edu.cn")])
        self.assertIn("E002", codes_of(result, 1))

    def test_blank_student_id(self):
        result = validate([make_record(1, student_id="   ")])
        self.assertIn("E001", codes_of(result, 1))

    def test_id_length_is_optional(self):
        """默认不校验位数，传了 --id-length 才校验。"""
        self.assertEqual(validate([make_record(1, student_id="1", email="1@smbu.edu.cn")]).issues, [])
        result = validate(
            [make_record(1, student_id="1", email="1@smbu.edu.cn")], COLUMNS, id_length=10
        )
        self.assertIn("E003", codes_of(result, 1))


class EmailRuleTest(unittest.TestCase):
    def test_domain_must_be_school(self):
        result = validate([make_record(1, email="2023010101@gmail.com")])
        self.assertIn("E005", codes_of(result, 1))

    def test_domain_is_case_insensitive(self):
        self.assertEqual(validate([make_record(1, email="2023010101@SMBU.EDU.CN")]).issues, [])

    def test_prefix_must_match_student_id(self):
        result = validate([make_record(1, email="2023010199@smbu.edu.cn")])
        self.assertIn("E006", codes_of(result, 1))

    def test_blank_email(self):
        result = validate([make_record(1, email="   ")])
        self.assertIn("E004", codes_of(result, 1))

    def test_surrounding_spaces_are_tolerated(self):
        """前后空格属于脏输入而非错误，strip 后应判为合法。"""
        self.assertEqual(
            validate([make_record(1, email="  2023010101@smbu.edu.cn ")]).issues, []
        )
        self.assertEqual(
            validate([make_record(1, student_id=" 2023010101 ")]).issues, []
        )


class DuplicateTest(unittest.TestCase):
    def test_same_student_id_twice(self):
        records = [make_record(1), make_record(2, name="李四")]
        result = validate(records)
        self.assertNotIn("E007", codes_of(result, 1))
        self.assertIn("E007", codes_of(result, 2))

    def test_exact_duplicate_flags_both_codes(self):
        records = [make_record(1), make_record(2)]
        result = validate(records)
        self.assertEqual(codes_of(result, 2), {"E007", "E008"})

    def test_id_duplicate_uses_first_occurrence_in_reason(self):
        records = [make_record(1), make_record(2), make_record(3)]
        result = validate(records)
        reasons = " ".join(issue.reason for issue in result.issues_by_index[3])
        self.assertIn("第 1 行", reasons)


class CleanDataTest(unittest.TestCase):
    def test_error_rows_dropped_warn_rows_kept(self):
        records = [
            make_record(1, student_id="2023010101", email="2023010101@smbu.edu.cn"),  # 干净
            make_record(2, student_id="2023010102", email="2023010102@smbu.edu.cn", name=""),  # W101 保留
            make_record(3, student_id="", email="2023010103@smbu.edu.cn"),            # E001 剔除
            make_record(4, student_id="2023010104", email="2023010104@smbu.edu.cn", first=""),  # W102 保留
            make_record(5, student_id="2023010105", email="bad@x.com"),               # E005 剔除
        ]
        result = validate(records)
        self.assertEqual(result.dropped_indexes, {3, 5})
        self.assertEqual([r.index for r in result.clean_records], [1, 2, 4])
        self.assertEqual(result.severity_of_index(2), "WARN")
        self.assertEqual(result.severity_of_index(3), "ERROR")

    def test_original_records_are_never_mutated(self):
        records = [make_record(1, student_id="abc")]
        before = dict(records[0].values)
        validate(records)
        self.assertEqual(records[0].values, before)


if __name__ == "__main__":
    unittest.main()
