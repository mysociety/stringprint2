"""
stringprint.compiler.CustomSCSS - dart-sass plus an autoprefixer pass.

Not compared byte for byte: sass output churns between releases, and the point
here is that the two subprocesses run and produce usable css.
"""

from __future__ import annotations

import shutil

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

    Output lands in static/COMPILED, which is gitignored - the same place a
    normal run puts it.
    """
    import static_precompiler.settings
    from static_precompiler.registry import get_compiler_by_path

    was_disabled = static_precompiler.settings.DISABLE_AUTO_COMPILE
    static_precompiler.settings.DISABLE_AUTO_COMPILE = False
    try:
        source = org.org_scss()
        compiler = get_compiler_by_path(source)
        compiler.compile(source)
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


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Known defect: the autoprefixer pass does not run in this image. "
        "postcss-cli and autoprefixer are installed globally but `postcss` "
        "itself is an unmet peer dependency, so `npx postcss --use "
        "autoprefixer` exits with ERR_MODULE_NOT_FOUND. CustomSCSS.compile_file "
        "captures the return code and never checks it, so the failure is "
        "silent and the published css is unprefixed - which matters because "
        "bootstrap relies on it. See docs/feature-inventory.md."
    ),
)
def test_autoprefixer_ran(compiled) -> None:
    """
    postcss/autoprefixer is a second subprocess after sass - a prefixed
    display:flex is the cheapest proof it happened.
    """
    css = open(compiled).read()
    assert "-ms-flexbox" in css or "-webkit-box" in css


def test_the_postcss_return_code_is_discarded(compiled) -> None:
    """
    Companion to the xfail above: this is why the breakage is invisible.
    """
    import inspect

    from stringprint.compiler import CustomSCSS

    source = inspect.getsource(CustomSCSS.compile_file)
    assert "return_code, out, errors = utils.run_command(post_process" in source
    tail = source.split("post_process")[-1]
    assert "raise" not in tail, "a failing postcss run would now be reported"


def test_svg_data_uris_survive_minification(compiled) -> None:
    from stringprint.compiler import svg_safe

    minified = svg_safe(open(compiled).read())
    assert "svg xmlns=" in minified
