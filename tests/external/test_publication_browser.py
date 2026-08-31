"""Real-browser regressions for Bootstrap 5 publication display."""

from __future__ import annotations

from collections.abc import Iterator
import os
from pathlib import Path
from typing import NamedTuple

import pytest
from PIL import Image
from playwright.sync_api import Page, sync_playwright

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.external]


class PublicationBrowser(NamedTuple):
    """A browser page connected to the live publication preview server."""

    page: Page
    base_url: str
    failed_requests: list[str]


@pytest.fixture(scope="module")
def publication_browser(live_server, kitchen_sink) -> Iterator[PublicationBrowser]:
    """Serve processed fixtures and open them in managed headless Chromium."""
    import static_precompiler.settings

    previous = static_precompiler.settings.DISABLE_AUTO_COMPILE
    previous_async_setting = os.environ.get("DJANGO_ALLOW_ASYNC_UNSAFE")
    os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
    static_precompiler.settings.DISABLE_AUTO_COMPILE = False
    failed_requests: list[str] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox"],
            )
            page = browser.new_page()
            page.on(
                "requestfailed",
                lambda request: (
                    failed_requests.append(request.url)
                    if request.url.startswith(live_server.url)
                    else None
                ),
            )
            yield PublicationBrowser(
                page=page,
                base_url=f"{live_server.url}/preview/{kitchen_sink.slug}",
                failed_requests=failed_requests,
            )
            browser.close()
    finally:
        static_precompiler.settings.DISABLE_AUTO_COMPILE = previous
        if previous_async_setting is None:
            os.environ.pop("DJANGO_ALLOW_ASYNC_UNSAFE", None)
        else:
            os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = previous_async_setting


def check_desktop_navigation_dropdown_and_escape(
    publication_browser: PublicationBrowser,
) -> None:
    """Desktop menus open natively, expose state, and close with Escape."""
    page = publication_browser.page
    page.set_viewport_size({"width": 1280, "height": 900})
    response = page.goto(f"{publication_browser.base_url}/")

    assert response is not None and response.ok
    brand_box = page.locator("#brand").bounding_box()
    assert brand_box is not None
    assert brand_box["x"] == 16
    page.locator(".top-nav-item").evaluate_all(
        "links => links.forEach(link => { link.textContent += "
        "' deliberately long navigation heading'; })"
    )
    page.evaluate("window.dispatchEvent(new Event('resize'))")
    page.wait_for_timeout(100)
    assert page.locator("[data-item].hide-item").count() > 0
    visible_menu_items = page.locator("[data-item]:visible")
    home_link = page.locator("#home-link")
    if home_link.count():
        home_box = home_link.bounding_box()
        assert home_box is not None
        available_right = home_box["x"] - 30
    else:
        available_right = 1272
    for index in range(visible_menu_items.count()):
        box = visible_menu_items.nth(index).bounding_box()
        assert box is not None
        assert box["x"] + box["width"] <= available_right + 1

    response = page.goto(f"{publication_browser.base_url}/")
    assert response is not None and response.ok
    assert (
        page.locator("nav.large-menu").evaluate(
            "element => getComputedStyle(element).display"
        )
        == "flex"
    )
    assert (
        page.locator("#mobile-navbar-header").evaluate(
            "element => getComputedStyle(element).display"
        )
        == "none"
    )

    toggle = page.locator("[data-menu-toggle]").first
    menu = toggle.locator("xpath=..//div[contains(@class, 'dropdown-menu')]")
    toggle.click()
    assert toggle.get_attribute("aria-expanded") == "true"
    assert "show" in (menu.get_attribute("class") or "")
    toggle_box = toggle.bounding_box()
    dropdown_box = toggle.locator("xpath=..").bounding_box()
    menu_box = menu.bounding_box()
    assert toggle_box is not None
    assert dropdown_box is not None
    assert menu_box is not None
    assert menu_box["x"] < toggle_box["x"]
    assert (
        abs(
            (menu_box["x"] + menu_box["width"])
            - (dropdown_box["x"] + dropdown_box["width"])
        )
        < 1
    )

    page.keyboard.press("Escape")
    assert toggle.get_attribute("aria-expanded") == "false"
    assert "show" not in (menu.get_attribute("class") or "")
    assert not publication_browser.failed_requests


def check_mobile_navigation_opens_and_link_closes_it(
    publication_browser: PublicationBrowser,
) -> None:
    """The mobile menu is visible at its breakpoint and closes after navigation."""
    page = publication_browser.page
    page.set_viewport_size({"width": 390, "height": 844})
    response = page.goto(f"{publication_browser.base_url}/")

    assert response is not None and response.ok
    assert (
        page.locator("nav.large-menu").evaluate(
            "element => getComputedStyle(element).display"
        )
        == "none"
    )
    assert (
        page.locator("#mobile-navbar-header").evaluate(
            "element => getComputedStyle(element).display"
        )
        == "flex"
    )

    toggle = page.locator("#mobile-menu-toggle")
    menu = page.locator("#navbarSupportedContent")
    toggle.click()
    assert toggle.get_attribute("aria-expanded") == "true"
    assert "show" in (menu.get_attribute("class") or "")

    page.locator(".mobile-menu-list a[href='#index']").click()
    assert toggle.get_attribute("aria-expanded") == "false"
    assert "show" not in (menu.get_attribute("class") or "")


def check_search_controls_align_and_page_can_be_screenshotted(
    publication_browser: PublicationBrowser,
    tmp_path: Path,
) -> None:
    """Search renders as one input group and produces a real browser image."""
    page = publication_browser.page
    page.set_viewport_size({"width": 1280, "height": 900})
    response = page.goto(f"{publication_browser.base_url}/search")

    assert response is not None and response.ok
    input_box = page.locator("#publication-search-input").bounding_box()
    button_box = page.locator("#publication-search-form button").bounding_box()
    assert input_box is not None
    assert button_box is not None
    assert abs(input_box["y"] - button_box["y"]) < 1
    assert abs(input_box["height"] - button_box["height"]) < 1

    overflow = page.evaluate(
        """() => Array.from(document.querySelectorAll('*'))
          .map(element => ({
            tag: element.tagName,
            id: element.id,
            className: element.className,
            right: element.getBoundingClientRect().right
          }))
          .filter(item => item.right > document.documentElement.clientWidth + 1)
          .sort((left, right) => right.right - left.right)
          .slice(0, 10)"""
    )
    assert page.evaluate("document.documentElement.scrollWidth") == 1280, overflow

    screenshot = tmp_path / "publication-search.png"
    page.screenshot(path=str(screenshot), full_page=True)
    width, height = Image.open(screenshot).size
    assert width == 1280
    assert height >= 900


def test_publication_display_in_real_browser(
    publication_browser: PublicationBrowser,
    tmp_path: Path,
) -> None:
    """Exercise desktop, mobile, and search views before Django flushes fixtures."""
    check_desktop_navigation_dropdown_and_escape(publication_browser)
    check_mobile_navigation_opens_and_link_closes_it(publication_browser)
    check_search_controls_align_and_page_can_be_screenshotted(
        publication_browser,
        tmp_path,
    )
    assert not publication_browser.failed_requests
