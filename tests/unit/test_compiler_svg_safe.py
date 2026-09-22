"""
svg_safe protects whitespace inside svg+xml data URIs from the css minifier.
"""

from __future__ import annotations

from stringprint.compiler import svg_safe


def test_static_placeholder_is_rewritten() -> None:
    assert "../.." in svg_safe("a{background:url(/%%static%%/x.png)}")


def test_minifies_ordinary_css() -> None:
    assert svg_safe("a {\n  color: red;\n}") == "a{color:red}"


def test_whitespace_inside_an_svg_data_uri_survives() -> None:
    css = (
        ".i{background-image:url(\"data:image/svg+xml;charset=utf8,"
        "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 8 8'%3E%3C/svg%3E\")}"
    )
    result = svg_safe(css)
    assert "svg xmlns=" in result
    assert "viewBox='0 0 8 8'" in result


def test_the_temporary_marker_never_survives() -> None:
    css = ".i{background:url(\"data:image/svg+xml,%3Csvg a b c%3E\")}"
    assert "!!TEMPSPACE!!" not in svg_safe(css)


def test_lines_without_svg_are_still_minified() -> None:
    css = ".a {\n  color: red;\n}\n.b{background:url(\"data:image/svg+xml,%3Csvg a b%3E\")}"
    result = svg_safe(css)
    assert ".a{color:red}" in result
    assert "svg a b" in result
