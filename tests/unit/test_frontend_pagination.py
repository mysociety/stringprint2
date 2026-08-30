"""
GroupedPage - pure pagination helpers, no database.
"""

from __future__ import annotations

import pytest

from frontend.views import GroupedPage


class FakePaginator:
    def __init__(self, num_pages: int):
        self.num_pages = num_pages


def page(number: int, num_pages: int, items=None) -> GroupedPage:
    return GroupedPage(items or [], number, FakePaginator(num_pages))


class TestGroupedRelease:
    def test_items_come_out_in_pairs(self) -> None:
        result = list(page(1, 1, ["a", "b", "c", "d"]).grouped_release())
        assert result == [["a", "b"], ["c", "d"]]

    def test_an_odd_tail_is_yielded_alone(self) -> None:
        result = list(page(1, 1, ["a", "b", "c"]).grouped_release())
        assert result == [["a", "b"], ["c"]]

    def test_a_single_item_is_yielded(self) -> None:
        assert list(page(1, 1, ["a"]).grouped_release()) == [["a"]]

    def test_nothing_yields_nothing(self) -> None:
        assert list(page(1, 1, []).grouped_release()) == []


class TestReasonableRange:
    def test_a_short_paginator_lists_every_page(self) -> None:
        assert page(1, 5, []).reasonable_range() == [1, 2, 3, 4, 5]

    def test_the_boundary_below_the_full_range(self) -> None:
        assert page(1, 9, []).reasonable_range() == list(range(1, 10))

    @pytest.mark.parametrize("num_pages", [10, 11, 20, 100])
    def test_a_long_paginator_raises(self, num_pages: int) -> None:
        """
        Known defect: h_range is full_range / 2, which is a float under Python
        3, so lower and higher stay floats and range() rejects them. Every
        branch except the `max_pages < full_range` early return is therefore
        dead - this helper only ever works for short paginators.

        Pinned rather than fixed; see docs/feature-inventory.md.
        """
        with pytest.raises(TypeError, match="integer"):
            page(1, num_pages, []).reasonable_range()
