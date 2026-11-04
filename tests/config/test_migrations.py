"""
The migration set itself.

The complete historical graph carries two custom fields (JsonBlockField and
ChartField). Both fresh installs and populated upgrades must remain readable.
"""

from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command
from django.db import connection, connections
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


def test_upgrade_preserves_legacy_serialized_values(
    tmp_path, django_db_blocker
) -> None:
    """
    A populated pre-upgrade database retains its JSON values byte for byte.
    """
    from stringprint.models import Article, Asset
    from stringprint2.charts import Chart

    alias = "migration_history"
    connections.databases[alias] = {
        **connection.settings_dict,
        "NAME": tmp_path / "migration-history.sqlite3",
    }
    with django_db_blocker.unblock():
        migration_connection = connections[alias]
        try:
            executor = MigrationExecutor(migration_connection)
            latest = executor.loader.graph.leaf_nodes()
            old_targets = [("stringprint", "0041_auto_20200906_1326")]
            executor.migrate(old_targets)
            apps = executor.loader.project_state(old_targets).apps
            organisation = (
                apps.get_model("stringprint", "Organisation")
                .objects.using(alias)
                .create(name="Legacy organisation", slug="legacy-upgrade")
            )
            article = (
                apps.get_model("stringprint", "Article")
                .objects.using(alias)
                .create(
                    org=organisation,
                    slug="legacy-upgrade",
                    extra_values={"nested": {"enabled": True}, "title": "Café"},
                    commands={"publish": "echo done"},
                )
            )
            chart = Chart(chart_type="table_chart")
            chart.rows = [[2025, "Legacy table"]]
            asset = (
                apps.get_model("stringprint", "Asset")
                .objects.using(alias)
                .create(article=article, slug="legacy-table", chart=chart)
            )
            with migration_connection.cursor() as cursor:
                cursor.execute(
                    "SELECT extra_values, commands FROM stringprint_article WHERE id = %s",
                    [article.pk],
                )
                original = cursor.fetchone()
                cursor.execute(
                    "SELECT chart FROM stringprint_asset WHERE id = %s", [asset.pk]
                )
                original_chart = cursor.fetchone()

            MigrationExecutor(migration_connection).migrate(latest)
            restored = Article.objects.using(alias).get(pk=article.pk)
            assert restored.extra_values == {
                "nested": {"enabled": True},
                "title": "Café",
            }
            assert restored.commands == {"publish": "echo done"}
            assert Asset.objects.using(alias).get(pk=asset.pk).chart.rows == [
                [2025, "Legacy table"]
            ]
            with migration_connection.cursor() as cursor:
                cursor.execute(
                    "SELECT extra_values, commands FROM stringprint_article WHERE id = %s",
                    [article.pk],
                )
                assert cursor.fetchone() == original
                cursor.execute(
                    "SELECT chart FROM stringprint_asset WHERE id = %s", [asset.pk]
                )
                assert cursor.fetchone() == original_chart
        finally:
            migration_connection.close()
            del connections[alias]
            connections.databases.pop(alias)
