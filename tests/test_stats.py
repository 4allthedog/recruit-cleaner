"""需求 3 的统计逻辑测试。"""

from __future__ import annotations

import unittest

from recruit_clean.stats import (
    FILL_BOTH,
    FILL_NONE,
    FILL_SINGLE,
    UNFILLED_LABEL,
    build_stats,
)

from .test_validator import make_record


class FirstChoiceStatsTest(unittest.TestCase):
    def test_group_by_first_choice(self):
        records = [
            make_record(1, student_id="1", email="1@smbu.edu.cn", first="技术部"),
            make_record(2, student_id="2", email="2@smbu.edu.cn", first="技术部"),
            make_record(3, student_id="3", email="3@smbu.edu.cn", first="宣传部"),
        ]
        stats = build_stats(records)
        self.assertEqual(stats.first_choice, [("技术部", 2), ("宣传部", 1)])
        self.assertEqual(stats.total, 3)

    def test_ties_are_broken_by_name_for_stable_output(self):
        records = [
            make_record(1, student_id="1", email="1@smbu.edu.cn", first="策划部"),
            make_record(2, student_id="2", email="2@smbu.edu.cn", first="技术部"),
        ]
        stats = build_stats(records)
        self.assertEqual([name for name, _ in stats.first_choice], ["技术部", "策划部"])

    def test_unfilled_first_choice_is_grouped(self):
        records = [make_record(1, first="")]
        stats = build_stats(records)
        self.assertEqual(stats.first_choice, [(UNFILLED_LABEL, 1)])

    def test_surrounding_spaces_do_not_create_a_new_group(self):
        records = [
            make_record(1, first="技术部"),
            make_record(2, student_id="2", email="2@smbu.edu.cn", first=" 技术部 "),
        ]
        stats = build_stats(records)
        self.assertEqual(stats.first_choice, [("技术部", 2)])


class FillStatsTest(unittest.TestCase):
    def test_both_single_and_none(self):
        records = [
            make_record(1, student_id="1", email="1@smbu.edu.cn", first="技术部", second="策划部"),
            make_record(2, student_id="2", email="2@smbu.edu.cn", first="技术部"),
            make_record(3, student_id="3", email="3@smbu.edu.cn", first="", second=""),
        ]
        stats = build_stats(records)
        self.assertEqual(stats.fill[FILL_BOTH], 1)
        self.assertEqual(stats.fill[FILL_SINGLE], 1)
        self.assertEqual(stats.fill[FILL_NONE], 1)

    def test_second_choice_only_counts_as_single(self):
        """第一志愿空、第二志愿填了，也算"只填了一个"。"""
        records = [make_record(1, first="", second="宣传部")]
        stats = build_stats(records)
        self.assertEqual(stats.fill[FILL_SINGLE], 1)
        self.assertEqual(stats.fill[FILL_BOTH], 0)

    def test_fill_counts_sum_to_total(self):
        records = [
            make_record(1, student_id="1", email="1@smbu.edu.cn", first="技术部", second="策划部"),
            make_record(2, student_id="2", email="2@smbu.edu.cn", first="技术部"),
            make_record(3, student_id="3", email="3@smbu.edu.cn", first="宣传部", second="秘书处"),
        ]
        stats = build_stats(records)
        self.assertEqual(sum(stats.fill.values()), stats.total)


if __name__ == "__main__":
    unittest.main()
