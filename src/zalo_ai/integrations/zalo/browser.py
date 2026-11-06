import logging
from threading import Event
from time import monotonic
from typing import Callable

from playwright.sync_api import (
    BrowserContext,
    Locator,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
)

from zalo_ai.common.cancellation import check_cancellation
from zalo_ai.integrations.zalo.selectors import CONVERSATION_SELECTOR
from zalo_ai.paths import BROWSER_PROFILE, PROJECT_ROOT

ProgressCallback = Callable[[str], None]


def notify(callback: ProgressCallback | None, message: str) -> None:
    """Send progress to the caller or the application logger."""
    if callback is not None:
        callback(message)
    else:
        logging.getLogger(__name__).info(message)


def wait_for_locator(
    locator: Locator,
    timeout_ms: int,
    cancel_event: Event | None = None,
) -> None:
    """Wait in short intervals so a running workflow can be cancelled."""
    if cancel_event is None:
        locator.wait_for(state="visible", timeout=timeout_ms)
        return

    deadline = monotonic() + timeout_ms / 1000

    while True:
        check_cancellation(cancel_event)
        remaining_ms = int((deadline - monotonic()) * 1000)
        if remaining_ms <= 0:
            raise PlaywrightTimeoutError(
                f"Timed out after {timeout_ms} ms waiting for locator."
            )

        try:
            locator.wait_for(
                state="visible",
                timeout=min(750, remaining_ms),
            )
            return
        except PlaywrightTimeoutError:
            if monotonic() >= deadline:
                raise


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
    cancel_event: Event | None = None,
) -> tuple[BrowserContext, Page]:
    """Use the saved session headlessly and show a browser for sign-in."""
    check_cancellation(cancel_event)
    notify(on_status, "Checking the saved Zalo session in the background.")
    context, page = launch_zalo_context(playwright, headless=True)

    try:
        wait_for_locator(
            page.locator(CONVERSATION_SELECTOR).first,
            timeout_ms=15000,
            cancel_event=cancel_event,
        )
    except PlaywrightTimeoutError:
        context.close()
        check_cancellation(cancel_event)
        notify(
            on_status,
            "Zalo needs attention. Opening a browser so you can sign in.",
        )
        context, page = launch_zalo_context(playwright, headless=False)

        try:
            wait_for_locator(
                page.locator(CONVERSATION_SELECTOR).first,
                timeout_ms=300000,
                cancel_event=cancel_event,
            )
        except BaseException:
            context.close()
            raise

        context.close()
        check_cancellation(cancel_event)
        notify(
            on_status,
            "Sign-in is ready. Closing the browser and continuing "
            "in the background.",
        )
        context, page = launch_zalo_context(playwright, headless=True)

        try:
            wait_for_locator(
                page.locator(CONVERSATION_SELECTOR).first,
                timeout_ms=60000,
                cancel_event=cancel_event,
            )
        except BaseException:
            context.close()
            raise
    except BaseException:
        context.close()
        raise

    check_cancellation(cancel_event)
    notify(on_status, "Zalo is ready; continuing without a browser window.")
    return context, page
