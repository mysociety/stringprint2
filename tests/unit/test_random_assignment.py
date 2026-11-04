"""
RandomAssignment drives Graf.position_key, and so feeds combo_key.

Deliberately no assertions on a literal random sequence: CPython's PRNG is not
a contract across versions, and every fixture document uses seed -1.
"""

from __future__ import annotations

from stringprint2.stringprint.tools.deepink import RandomAssignment


class TestSequentialSeed:
    def test_minus_one_counts_up_from_one(self) -> None:
        assignment = RandomAssignment(-1)
        assert [assignment.get() for _ in range(5)] == [1, 2, 3, 4, 5]

    def test_two_instances_agree(self) -> None:
        assert [RandomAssignment(-1).get() for _ in range(3)] == [1, 1, 1]


class TestRandomSeed:
    def test_values_are_unique(self) -> None:
        assignment = RandomAssignment(13)
        values = [assignment.get() for _ in range(200)]
        assert len(set(values)) == len(values)

    def test_values_are_offset_by_the_seed(self) -> None:
        assignment = RandomAssignment(13)
        values = [assignment.get() for _ in range(50)]
        assert all(13 < value <= RandomAssignment.max + 13 for value in values)

    def test_same_seed_gives_the_same_sequence(self) -> None:
        first = [RandomAssignment(13).get() for _ in range(3)]
        second = [RandomAssignment(13).get() for _ in range(3)]
        assert first == second

    def test_different_seeds_diverge(self) -> None:
        first = [RandomAssignment(13).get() for _ in range(5)]
        second = [RandomAssignment(99).get() for _ in range(5)]
        assert first != second
