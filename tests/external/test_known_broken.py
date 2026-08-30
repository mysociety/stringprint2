"""
Code paths that are already broken on the current stack.

Every test here is a strict xfail, so each one flips to a failure the moment
someone repairs the underlying code - which is exactly the signal wanted
during the Python 3.14 / Django 5.2 upgrade. Nothing here is fixed as part of
building the suite; the catalogue lives in docs/feature-inventory.md.
"""

from __future__ import annotations

import inspect

import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.external]


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Article.authenticate references an Access model that no longer "
        "exists anywhere in the codebase."
    ),
)
def test_article_authenticate_references_a_missing_model(load_doc) -> None:
    from django.contrib.auth.models import User

    article = load_doc("kitchen-sink")
    user = User(username="someone", is_staff=False)
    article.authenticate(user, None)


def test_asset_get_chart_image_is_broken_on_python_three() -> None:
    """
    Two independent breakages, checked by reading the source rather than by
    running it - it needs geckodriver, which is not installed.

    str has had no .decode since Python 2, and find_element_by_id was removed
    in Selenium 4, so this cannot work on any modern stack.
    """
    from stringprint.models import Asset

    source = inspect.getsource(Asset.get_chart_image)
    assert 'contents.decode("base64")' in source
    assert "find_element_by_id" in source


def test_the_legacy_google_charts_module_is_unreferenced() -> None:
    """
    stringprint/tools/charts.py is superseded by the charts package. Nothing
    imports it, so it is dead weight that still has to survive the upgrade.
    """
    import subprocess

    from django.conf import settings

    result = subprocess.run(
        ["grep", "-rn", "--include=*.py", "from .charts import\\|tools.charts",
         settings.PROJECT_PATH],
        stdout=subprocess.PIPE,
    )
    assert result.stdout.decode() == ""


def test_footnote_convert_is_a_dead_script() -> None:
    """
    Its whole body sits under `if __name__ == "__main__"` with hardcoded
    Windows paths.
    """
    from stringprint.tools import footnote_convert

    public = [name for name in vars(footnote_convert) if not name.startswith("__")]
    assert not [name for name in public if callable(vars(footnote_convert)[name])]
