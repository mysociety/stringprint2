"""
Tests for native authenticated-interface form widgets.
"""

from __future__ import annotations

from stringprint2.frontend.forms import ArticlePublishForm


def test_publish_date_uses_native_date_input() -> None:
    """
    Publishing no longer requires the jQuery UI datepicker.
    """

    form = ArticlePublishForm()

    assert form.fields["publish_date"].widget.input_type == "date"
