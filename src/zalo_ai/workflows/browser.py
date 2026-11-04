import logging
from pathlib import Path
from typing import Callable

from playwright.sync_api import (
    BrowserContext,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
)

from zalo_ai.targets.zalo_discovery import CONVERSATION_SELECTOR


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BROWSER_PROFILE = PROJECT_ROOT / "data" / "browser_profile"
ProgressCallback = Callable[[str], None]


def notify(callback: ProgressCallback | None, message: str) -> None:
    """Send progress to the caller or the application logger."""
    if callback is not None:
        callback(message)
    else:
        logging.getLogger(__name__).info(message)


def launch_zalo_context(
    playwright: Playwright,
    headless: bool,
) -> tuple[BrowserContext, Page]:
    """Launch Zalo with the project's persistent browser profile."""
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(BROWSER_PROFILE),
        headless=headless,
    )
    try:
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://chat.zalo.me/")
    except Exception:
        context.close()
        raise
    return context, page


def open_zalo(
    on_status: ProgressCallback | None,
    playwright: Playwright,
) -> tuple[BrowserContext, Page]:
    """Use the saved session headlessly and show a browser for sign-in."""
    notify(on_status, "Checking the saved Zalo session in the background.")
    context, page = launch_zalo_context(playwright, headless=True)

    try:
        page.locator(CONVERSATION_SELECTOR).first.wait_for(
            state="visible",
            timeout=15000,
        )
    except PlaywrightTimeoutError:
        context.close()
        notify(
            on_status,
            "Zalo needs attention. Opening a browser so you can sign in.",
        )
        context, page = launch_zalo_context(playwright, headless=False)

        try:
            page.locator(CONVERSATION_SELECTOR).first.wait_for(
                state="visible",
                timeout=300000,
            )
        except Exception:
            context.close()
            raise

        context.close()
        notify(
            on_status,
            "Sign-in is ready. Closing the browser and continuing "
            "in the background.",
        )
        context, page = launch_zalo_context(playwright, headless=True)

        try:
            page.locator(CONVERSATION_SELECTOR).first.wait_for(
                state="visible",
                timeout=60000,
            )
        except Exception:
            context.close()
            raise

    notify(on_status, "Zalo is ready; continuing without a browser window.")
    return context, page
