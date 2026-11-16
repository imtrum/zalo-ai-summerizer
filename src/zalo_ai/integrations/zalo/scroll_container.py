"""Locate the scrollable ancestor of Zalo's conversation list."""

from playwright.sync_api import ElementHandle, JSHandle, Page

from .selectors import CONVERSATION_SCROLL_CONTAINER_SELECTOR


FIND_SCROLL_CONTAINER_JS = """element => {
    for (
        let current = element;
        current && current !== document.body;
        current = current.parentElement
    ) {
        const style = getComputedStyle(current);
        if (
            current.scrollHeight > current.clientHeight &&
            ["auto", "scroll", "overlay"].includes(style.overflowY)
        ) {
            return current;
        }
    }
    return null;
}"""


def find_scroll_container(page: Page) -> tuple[JSHandle, ElementHandle | None]:
    """Return the evaluation handle and its scrollable element, if found."""
    handle = page.locator(CONVERSATION_SCROLL_CONTAINER_SELECTOR).first.evaluate_handle(
        FIND_SCROLL_CONTAINER_JS
    )
    return handle, handle.as_element()
