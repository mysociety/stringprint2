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
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


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


@pytest.mark.django_db(transaction=True)
def test_upgrade_preserves_legacy_serialized_values() -> None:
    """
    A populated pre-upgrade database retains its JSON values byte for byte.
    """
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    old_targets = [("stringprint", "0041_auto_20200906_1326")]
    try:
        executor.migrate(old_targets)
        apps = executor.loader.project_state(old_targets).apps
        organisation = apps.get_model("stringprint", "Organisation").objects.create(
            name="Legacy organisation", slug="legacy-upgrade"
        )
        article = apps.get_model("stringprint", "Article").objects.create(
            org=organisation,
            slug="legacy-upgrade",
            extra_values={"nested": {"enabled": True}, "title": "Café"},
            commands={"publish": "echo done"},
        )
        article_id = article.pk
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT extra_values, commands FROM stringprint_article WHERE id = %s",
                [article_id],
            )
            original = cursor.fetchone()

        executor = MigrationExecutor(connection)
        executor.migrate(latest)
        from stringprint.models import Article

        restored = Article.objects.get(pk=article_id)
        assert restored.extra_values == {"nested": {"enabled": True}, "title": "Café"}
        assert restored.commands == {"publish": "echo done"}
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT extra_values, commands FROM stringprint_article WHERE id = %s",
                [article_id],
            )
            assert cursor.fetchone() == original
    finally:
        MigrationExecutor(connection).migrate(latest)
