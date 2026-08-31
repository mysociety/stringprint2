"""
stringprint.compiler.CustomSCSS - dart-sass plus an autoprefixer pass.

Not compared byte for byte: sass output churns between releases, and the point
here is that the two subprocesses run and produce usable css.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.external,
    pytest.mark.needs_sass,
    pytest.mark.skipif(
        shutil.which("sass") is None or shutil.which("npx") is None,
        reason="needs sass and npx on PATH",
    ),
]


@pytest.fixture
def compiled(org):
    """
    Compile the org stylesheet through the app's own compiler registration.

    Output lands in COMPILED under the session's own STATIC_ROOT (see
    stringprint_test_env), not the real stringprint2/static/ tree.
    """
    import static_precompiler.settings
    from static_precompiler.registry import get_compiler_by_path

    was_disabled = static_precompiler.settings.DISABLE_AUTO_COMPILE
    static_precompiler.settings.DISABLE_AUTO_COMPILE = False
    try:
        source = org.org_scss()
        compiler = get_compiler_by_path(source)
        # compile_file rather than compile: the latter skips when the output is
        # newer than the entry point, and does not notice a changed partial
        compiler.compile_file(source)
        yield compiler.get_full_output_path(source)
    finally:
        static_precompiler.settings.DISABLE_AUTO_COMPILE = was_disabled


def test_the_org_stylesheet_compiles(compiled) -> None:
    import os

    assert os.path.exists(compiled)


def test_variables_are_resolved(compiled) -> None:
    css = open(compiled).read()
    assert "#cc0033" in css, "the brand colour from _org_variables"


def test_nested_rules_are_flattened(compiled) -> None:
    css = open(compiled).read()
    assert ".org-marker .nested-rule" in css


def test_autoprefixer_ran(compiled) -> None:
    """
    postcss/autoprefixer is a second subprocess after sass. flex needs no
    prefix under the default browserslist, so the fixture uses user-select,
    which still does.
    """
    css = open(compiled).read()
    assert "-webkit-user-select" in css


def test_no_inline_sourcemap_is_appended(compiled) -> None:
    """
    postcss is run with --no-map; without it, it appends a base64 copy of the
    whole stylesheet to every compiled file.
    """
    assert "sourceMappingURL" not in open(compiled).read()


def test_a_failing_postcss_run_is_reported(monkeypatch, org) -> None:
    """
    The return code used to be captured and discarded, so a missing postcss
    or autoprefixer produced unprefixed css silently.
    """
    import static_precompiler.exceptions
    import static_precompiler.settings
    from static_precompiler.registry import get_compiler_by_path
    from static_precompiler import utils

    real_run_command = utils.run_command

    def failing(args, *rest, **kwargs):
        if args and args[0] == "npx":
            return 1, "", "boom"
        return real_run_command(args, *rest, **kwargs)

    monkeypatch.setattr("stringprint.compiler.utils.run_command", failing)
    monkeypatch.setattr(static_precompiler.settings, "DISABLE_AUTO_COMPILE", False)

    source = org.org_scss()
    compiler = get_compiler_by_path(source)
    with pytest.raises(
        static_precompiler.exceptions.StaticCompilationError, match="autoprefixer"
    ):
        compiler.compile_file(source)


def test_svg_data_uris_survive_minification(compiled) -> None:
    from stringprint.compiler import svg_safe

    minified = svg_safe(open(compiled).read())
    assert "svg xmlns=" in minified


def test_default_publication_stylesheet_bootstrap_5_baseline(tmp_path) -> None:
    """Bootstrap 5 publication CSS retains a selective component and size budget."""
    from django.conf import settings
    from static_precompiler import utils

    source = Path(settings.PROJECT_PATH, "web", "scss", "main.scss")
    output = tmp_path / "publication.css"
    status, _, errors = utils.run_command(
        [
            "/usr/bin/sass",
            "--no-source-map",
            "--load-path",
            str(Path(settings.PROJECT_PATH, "vendor", "bootstrap", "scss")),
            "--load-path",
            str(Path(settings.PROJECT_PATH, "web", "scss")),
            str(source),
            str(output),
        ]
    )

    assert status == 0, errors
    css = output.read_text()
    assert 80_000 <= len(css.encode()) <= 90_000
    for selector in [
        ".navbar-expand-md",
        ".dropdown-menu-end",
        ".input-group",
        ".table-striped",
        ".me-auto",
        ".ms-auto",
        ".fixed-top",
    ]:
        assert selector in css
    assert ".modal" not in css
    assert ".carousel" not in css


@pytest.mark.parametrize(
    ("variables", "expected"),
    [
        (
            """
$page-background-color: #102030;
$content-background-color: #203040;
$content-text-color: #304050;
$navbar-accent-color: #405060;
$table-head-bg: #506070;
@import "stringprint/main";
""",
            ["#102030", "#203040", "#304050", "#405060", "#506070"],
        ),
        (
            """
$stringprint-page-background: #112233;
$stringprint-content-background: #223344;
$stringprint-content-color: #334455;
$stringprint-navbar-background: #445566;
$stringprint-table-heading-background: #556677;
@import "stringprint/main";
""",
            ["#112233", "#223344", "#334455", "#445566", "#556677"],
        ),
    ],
    ids=("legacy", "stringprint-api"),
)
def test_publication_theme_variable_apis_compile(
    tmp_path,
    variables: str,
    expected: list[str],
) -> None:
    """Existing aliases and the stable Stringprint API both affect output."""
    from django.conf import settings
    from static_precompiler import utils

    source = tmp_path / "theme.scss"
    output = tmp_path / "theme.css"
    source.write_text(variables)
    status, _, errors = utils.run_command(
        [
            "/usr/bin/sass",
            "--quiet",
            "--no-source-map",
            "--load-path",
            str(Path(settings.PROJECT_PATH, "vendor", "bootstrap", "scss")),
            "--load-path",
            str(Path(settings.PROJECT_PATH, "web", "scss")),
            str(source),
            str(output),
        ]
    )

    assert status == 0, errors
    css = output.read_text().lower()
    for colour in expected:
        assert colour in css
