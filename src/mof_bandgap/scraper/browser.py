import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Self

from browserforge.fingerprints import Screen  # pyright: ignore[reportMissingImports]
from camoufox.async_api import AsyncCamoufox  # pyright: ignore[reportMissingImports]
from playwright.async_api import Browser as PlaywrightBrowser  # pyright: ignore[reportMissingImports]
from playwright.async_api import Dialog, Locator, Page, Response  # pyright: ignore[reportMissingImports]

logger = logging.getLogger(__name__)


async def _handle_dialog(dialog: Dialog) -> None:
    logger.warning("[Browser] unexpected dialog type=%s message=%r", dialog.type, dialog.message)
    await dialog.accept()


class Browser:
    def __init__(self, page: Page, *, click_timeout_ms: int) -> None:
        self._page = page
        self._click_timeout_ms = click_timeout_ms

    @classmethod
    @asynccontextmanager
    async def open(
        cls,
        url: str,
        *,
        headless: bool,
        click_timeout_ms: int,
        page_load_timeout_ms: int,
    ) -> AsyncIterator[Self]:
        async with AsyncCamoufox(  # type: ignore[no-untyped-call]
            headless           = headless,
            screen             = Screen(max_width=1280, max_height=720),
            humanize           = True,
            block_webrtc       = True,
            locale             = ["en-US", "en"],
            firefox_user_prefs = {
                "javascript.use_us_english_locale": True,
                "network.trr.mode": 5,
            },
        ) as browser:
            assert isinstance(browser, PlaywrightBrowser)
            context = await browser.new_context(accept_downloads=False, no_viewport=True)
            page = await context.new_page()
            page.on("dialog", _handle_dialog)
            await page.goto(url)
            await page.wait_for_load_state("domcontentloaded", timeout=page_load_timeout_ms)
            await page.wait_for_load_state("load", timeout=page_load_timeout_ms)
            yield cls(page, click_timeout_ms=click_timeout_ms)

    async def select_count(self) -> int:
        return await self._page.locator("select").count()

    def select(self, index: int) -> Locator:
        return self._page.locator("select").nth(index)

    def button(self, name: re.Pattern[str]) -> Locator:
        return self._page.get_by_role("button", name=name)

    async def button_visible(self, name: re.Pattern[str]) -> bool:
        return await self.button(name).is_visible()

    async def has_ancestor_with_class(self, locator: Locator, class_name: str) -> bool:
        return bool(await locator.evaluate("(el, cls) => el.closest('.' + cls) !== null", class_name))

    async def click(self, locator: Locator) -> None:
        await locator.wait_for(state="visible", timeout=self._click_timeout_ms)
        await locator.scroll_into_view_if_needed(timeout=self._click_timeout_ms)
        await locator.click(trial=True, timeout=self._click_timeout_ms)
        await locator.click(timeout=self._click_timeout_ms)

    async def submit(self, button_name: re.Pattern[str], response_url: re.Pattern[str]) -> Response:
        async with self._page.expect_response(response_url) as response_info:
            await self.click(self.button(button_name))
        return await response_info.value
