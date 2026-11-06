from threading import Event
from time import monotonic

from playwright.sync_api import (
    ElementHandle,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

from zalo_ai.cancellation import check_cancellation
from .selectors import (
    CONVERSATION_ID_ATTRIBUTE,
    CONVERSATION_SCROLL_CONTAINER_SELECTOR as SCROLL_CONTAINER_SELECTOR,
    CONVERSATION_SELECTORS,
    CONVERSATION_SELECTOR,
)

SCROLL_PAUSE_MS = 800

# Nearest scrollable ancestor of the given element (or null).
_FIND_SCROLLER_JS = """element => {
    for (
        let current = element;
        current && current !== document.body;
        current = current.parentElement
    ) {
        if (
            current.scrollHeight > current.clientHeight &&
            ["auto", "scroll", "overlay"].includes(
                getComputedStyle(current).overflowY
            )
        ) {
            return current;
        }
    }
    return null;
}"""

# Name and id of every conversation row currently in the DOM.
_COLLECT_JS = """(items, selectors) => items.map(item => ({
    name: item.querySelector(
        selectors.name_selector
    )?.innerText.trim().replace(/\\u00a0/g, " ") || "",
    id: item.getAttribute(selectors.id_attribute) || ""
}))"""

_SCROLL_STATE_JS = """element => ({
    top: element.scrollTop,
    max: element.scrollHeight - element.clientHeight
})"""

# Scroll one page (a negative direction scrolls up).
_SCROLL_STEP_JS = """(element, direction) => {
    element.scrollTop += direction * Math.max(
        300, element.clientHeight * 0.8
    );
}"""


def _wait_for_conversation_list(
    page: Page,
    cancel_event: Event | None,
    timeout_ms: int = 15000,
) -> None:
    """Wait in short intervals to make list discovery responsive to cancel."""
    locator = page.locator(CONVERSATION_SELECTOR).first
    deadline = monotonic() + timeout_ms / 1000

    while True:
        check_cancellation(cancel_event)
        remaining_ms = int((deadline - monotonic()) * 1000)
        if remaining_ms <= 0:
            raise PlaywrightTimeoutError(
                f"Timed out after {timeout_ms} ms waiting for conversations."
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


def discover_conversations(
    page: Page,
    max_unchanged_rounds: int = 3,
    cancel_event: Event | None = None,
) -> list[dict[str, str]]:
    """Discover conversations by scrolling to the top, then the bottom."""
    _wait_for_conversation_list(page, cancel_event)

    scroll_handle = page.locator(
        SCROLL_CONTAINER_SELECTOR
    ).evaluate_handle(_FIND_SCROLLER_JS)
    scroll_container = scroll_handle.as_element()
    conversations: dict[str, dict[str, str]] = {}

    def collect_visible() -> None:
        check_cancellation(cancel_event)
        visible = page.locator(CONVERSATION_SELECTOR).evaluate_all(
            _COLLECT_JS, CONVERSATION_SELECTORS
        )
        for item in visible:
            if item["name"] and item["id"]:
                conversations[item["id"]] = item

    def scroll_to_end(direction: int) -> None:
        """Scroll up (-1) or down (+1) until the end stops moving."""
        unchanged_rounds = 0
        while unchanged_rounds < max_unchanged_rounds:
            collect_visible()

            before = scroll_container.evaluate(_SCROLL_STATE_JS)
            at_end = (
                before["top"] <= 0
                if direction < 0
                else before["top"] >= before["max"]
            )
            if at_end:
                return

            scroll_container.evaluate(_SCROLL_STEP_JS, direction)
            page.wait_for_timeout(SCROLL_PAUSE_MS)
            check_cancellation(cancel_event)

            after = scroll_container.evaluate(_SCROLL_STATE_JS)
            unchanged_rounds = (
                unchanged_rounds + 1 if after["top"] == before["top"] else 0
            )

    try:
        if scroll_container is not None:
            scroll_to_end(-1)
            scroll_to_end(1)
        collect_visible()  # the rows left at the bottom (or the only rows)
    finally:
        if scroll_container is not None:
            scroll_container.dispose()
        scroll_handle.dispose()

    return list(conversations.values())


def get_visible_conversation_ids(
    scroll_container: ElementHandle,
) -> list[str]:
    """Return IDs of rows intersecting the conversation-list viewport."""
    return scroll_container.evaluate(
        """(container, selectors) => {
            const viewport = container.getBoundingClientRect();

            return Array.from(
                document.querySelectorAll(selectors.conversation_selector)
            )
                .filter(item => {
                    const row = item.getBoundingClientRect();
                    return (
                        row.bottom > viewport.top &&
                        row.top < viewport.bottom &&
                        row.right > viewport.left &&
                        row.left < viewport.right
                    );
                })
                .map(item => item.getAttribute(selectors.id_attribute) || "")
                .filter(Boolean);
        }""",
        {
            "conversation_selector": CONVERSATION_SELECTOR,
            "id_attribute": CONVERSATION_ID_ATTRIBUTE,
        },
    )


def open_visible_conversation(
    page: Page,
    target_id: str,
) -> bool:
    """Open a target only if its row is already visible in the list."""
    locator = page.locator(
        f'{CONVERSATION_SELECTOR}[{CONVERSATION_ID_ATTRIBUTE}="{target_id}"]'
    )

    if not locator.count() or not locator.is_visible():
        return False

    locator.click()
    return True