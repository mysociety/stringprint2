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
    def test_a_long_paginator_returns_a_window(self, num_pages: int) -> None:
        result = page(1, num_pages, []).reasonable_range()
        assert result
        assert all(isinstance(value, int) for value in result)
        assert result == sorted(result)
        assert result[-1] == num_pages, "the last page is always reachable"

    def test_the_window_is_centred_on_the_current_page(self) -> None:
        assert page(50, 100, []).reasonable_range() == [
            1, 46, 47, 48, 49, 50, 51, 52, 53, 100
        ]

    def test_the_first_page_is_linked_once_out_of_range(self) -> None:
        assert page(1, 20, []).reasonable_range() == [1, 2, 3, 4, 20]

    def test_near_the_end_the_last_page_is_not_duplicated(self) -> None:
        result = page(18, 20, []).reasonable_range()
        assert result == [1, 14, 15, 16, 17, 18, 19]
        assert len(result) == len(set(result))
