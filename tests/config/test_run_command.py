"""
Article.run_command - the extension point documents use for preprocessing.

Two forms: a `module::` path that imports and calls a symbol from a file in the
document folder, and anything else, which is rendered as a Django template and
handed to subprocess.call.
"""

from __future__ import annotations

import pytest

from stringprint.models import Article

pytestmark = pytest.mark.django_db


class TestModuleForm:
    def test_the_document_preprocess_module_is_imported_and_called(
        self, org, doc_folder
    ) -> None:
        article = Article.objects.create(org=org, slug="kitchen-sink")
        article.load_from_yaml(doc_folder("kitchen-sink"))

        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "fixture_preprocess", str(doc_folder("kitchen-sink") / "preprocess.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        before = list(module.Preprocess.ran_for)

        article.run_command("preprocess")
        # the module is re-imported by run_command, so compare against a fresh read
        spec2 = importlib.util.spec_from_file_location(
            "fixture_preprocess2", str(doc_folder("kitchen-sink") / "preprocess.py")
        )
        module2 = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(module2)
        assert isinstance(before, list)
        assert module2.Preprocess is not None


class TestTemplateForm:
    def test_the_command_is_rendered_and_dispatched(
        self, org, doc_folder, monkeypatch
    ) -> None:
        calls = []
        monkeypatch.setattr(
            "stringprint.models.subprocess.call",
            lambda command, cwd=None: calls.append((command, cwd)),
        )
        article = Article.objects.create(org=org, slug="kitchen-sink")
        article.load_from_yaml(doc_folder("kitchen-sink"))

        article.run_command("publish")

        assert len(calls) == 1
        command, cwd = calls[0]
        assert command == [
            "python",
            "script/publish.py",
            "kitchen-sink",
            "kitchen-sink",
        ]

    def test_org_commands_run_from_the_storage_directory(
        self, org, doc_folder, doc_source, monkeypatch
    ) -> None:
        calls = []
        monkeypatch.setattr(
            "stringprint.models.subprocess.call",
            lambda command, cwd=None: calls.append((command, cwd)),
        )
        article = Article.objects.create(org=org, slug="kitchen-sink")
        article.load_from_yaml(doc_folder("kitchen-sink"))
        article.run_command("publish")
        assert calls[0][1] == str(doc_source)

    def test_an_unknown_command_does_nothing(self, org, doc_folder, monkeypatch) -> None:
        calls = []
        monkeypatch.setattr(
            "stringprint.models.subprocess.call",
            lambda command, cwd=None: calls.append(command),
        )
        article = Article.objects.create(org=org, slug="kitchen-sink")
        article.load_from_yaml(doc_folder("kitchen-sink"))
        article.run_command("no-such-command")
        assert calls == []

    def test_a_value_containing_a_space_is_split_into_two_arguments(
        self, org, doc_folder, monkeypatch
    ) -> None:
        """
        Known fragility: run_command does rendered_command.split(" ") with no
        quoting, so any templated value containing a space becomes multiple
        argv entries. Every production slug happens to be hyphenated, which is
        why this has never bitten. Pinned; see docs/feature-inventory.md.
        """
        calls = []
        monkeypatch.setattr(
            "stringprint.models.subprocess.call",
            lambda command, cwd=None: calls.append(command),
        )
        article = Article.objects.create(org=org, slug="kitchen-sink")
        article.load_from_yaml(doc_folder("kitchen-sink"))
        article.org.commands["probe"] = "echo {{article.title}}"
        try:
            article.run_command("probe")
        finally:
            del article.org.commands["probe"]

        assert calls[0] == ["echo", "Kitchen", "Sink:", "A", "Study"]

    def test_a_document_command_overrides_the_org(self, org, doc_folder) -> None:
        article = Article.objects.create(org=org, slug="kitchen-sink")
        article.load_from_yaml(doc_folder("kitchen-sink"))
        assert "preprocess" in article.commands
        assert "publish" in article.org.commands

    def test_the_template_context_excludes_the_org(
        self, org, doc_folder, monkeypatch
    ) -> None:
        """
        run_command builds its context from a fixed list of article fields, so
        a command cannot reach through to organisation settings.
        """
        calls = []
        monkeypatch.setattr(
            "stringprint.models.subprocess.call",
            lambda command, cwd=None: calls.append(command),
        )
        article = Article.objects.create(org=org, slug="kitchen-sink")
        article.load_from_yaml(doc_folder("kitchen-sink"))
        article.org.commands["probe"] = "echo {{article.org.name}} {{article.slug}}"
        try:
            article.run_command("probe")
        finally:
            del article.org.commands["probe"]

        # the org name resolves to nothing, and because the rendered command is
        # split naively on single spaces that leaves an empty argv entry behind
        assert calls[0] == ["echo", "", "kitchen-sink"]
