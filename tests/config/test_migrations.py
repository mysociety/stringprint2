"""
The migration set itself.

41 stringprint migrations plus 5 for frontend, carrying two custom fields
(JsonBlockField and ChartField). Breakage under a new Django would otherwise
surface as a collection error rather than a named failure.
"""

from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_every_migration_is_applied() -> None:
    out = StringIO()
    call_command("showmigrations", "--plan", stdout=out)
    plan = out.getvalue()
    assert "[ ]" not in plan, "unapplied migrations:\n{0}".format(plan)


@pytest.mark.django_db
def test_the_custom_fields_survive_a_round_trip(load_doc) -> None:
    """
    JsonBlockField and ChartField are the two non-standard columns, and both
    are hand-rolled serialisers rather than Django's own JSONField.
    """
    from stringprint.models import Article, Asset

    article = Article.objects.get(pk=load_doc("kitchen-sink").pk)
    assert isinstance(article.extra_values, dict)
    assert article.extra_values["repo_slug"] == "kitchen-sink"

    asset = Asset.objects.get(article=article, slug="table-one")
    assert asset.chart.chart_type == "table_chart"
    assert len(asset.chart.columns) == 4


@pytest.mark.django_db
def test_the_schema_matches_the_models() -> None:
    """No model change has been left without a migration."""
    out = StringIO()
    call_command("makemigrations", "--check", "--dry-run", stdout=out, verbosity=1)
