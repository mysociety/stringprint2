"""
Organisation.load_from_yaml and the path properties derived from settings.ORGS.
"""

from __future__ import annotations

import pytest

from stringprint2.stringprint.models import Organisation

pytestmark = pytest.mark.django_db


class TestLoadFromYaml:
    def test_known_keys_land_on_model_fields(self, org: Organisation) -> None:
        assert org.name == "Test Org"
        assert org.twitter == "testorg"
        assert org.ga_code == "G-TESTTESTTEST"
        assert org.publish_root == "https://example.invalid/html/"
        assert org.icon == "images/test_icon.png"

    def test_booleans_survive_the_round_trip(self, org: Organisation) -> None:
        assert org.ga_cookies is False
        assert org.include_favicon is False

    def test_json_blob_fields_are_loaded(self, org: Organisation) -> None:
        assert org.commands["publish"].startswith("python script/publish.py")
        assert set(org.default_values) == {"repo_entry", "bottom_iframe"}

    def test_orglinks_are_not_stored_as_a_field(self, org: Organisation) -> None:
        assert "orglinks" not in org.extra_values

    def test_reloading_is_idempotent(self, org: Organisation) -> None:
        org.load_from_yaml()
        assert org.org_links.count() == 2


class TestOrgLinks:
    def test_links_are_created(self, org: Organisation) -> None:
        assert org.org_links.count() == 2

    def test_links_are_ordered_by_their_order_key(self, org: Organisation) -> None:
        # the yaml deliberately lists Second Link first
        names = [link.name for link in org.org_links_ordered()]
        assert names == ["First Link", "Second Link"]

    def test_link_targets_are_kept(self, org: Organisation) -> None:
        link = org.org_links_ordered()[0]
        assert link.link == "https://example.invalid/first"
        assert link.order == 0


class TestExtraValuesPruning:
    def test_keys_absent_from_the_yaml_are_dropped(self, doc_source) -> None:
        organisation = Organisation.objects.create(slug="default")
        organisation.extra_values = {"stale_key": "stale value"}
        organisation.load_from_yaml()
        assert "stale_key" not in organisation.extra_values

    def test_unknown_keys_in_the_yaml_are_kept(self, doc_source) -> None:
        """
        Anything that is not a model field goes to extra_values, and
        Organisation.__init__ splats extra_values onto the instance.
        """
        organisation = Organisation.objects.create(slug="default")
        organisation.load_from_yaml()
        reloaded = Organisation.objects.get(pk=organisation.pk)
        assert isinstance(reloaded.extra_values, dict)


class TestPathProperties:
    def test_storage_dir_comes_from_settings(self, org, doc_source) -> None:
        assert org.storage_dir == str(doc_source)

    def test_publish_dir_defaults_below_storage_dir(self, org, doc_source) -> None:
        assert org.publish_dir == str(doc_source / "_publish")

    def test_template_dir_is_found(self, org, doc_source) -> None:
        assert org.template_dir == str(doc_source / "_templates")

    def test_template_dir_is_none_when_absent(self, org, settings, tmp_path) -> None:
        settings.ORGS = {"default": {"storage_dir": str(tmp_path)}}
        assert org.template_dir is None

    def test_relative_icon_path_is_namespaced(self, org) -> None:
        assert org.relative_icon_path() == "orgs/default/images/test_icon.png"

    def test_org_scss_returns_a_static_relative_path(self, org) -> None:
        assert org.org_scss() == "orgs/default/scss/main.scss"

    def test_org_scss_screenshot_variant(self, org) -> None:
        assert org.org_scss_screenshot() == "orgs/default/scss/screenshot.scss"

    def test_org_scss_returns_none_when_missing(self, org) -> None:
        assert org.org_scss("does-not-exist.scss") is None


class TestGaCode:
    def test_the_org_code_wins(self, org) -> None:
        assert org.get_ga_code() == "G-TESTTESTTEST"

    def test_falls_back_to_the_site_setting(self, settings) -> None:
        settings.GA_CODE = "G-SITEWIDE"
        assert Organisation(slug="default", ga_code=None).get_ga_code() == "G-SITEWIDE"
