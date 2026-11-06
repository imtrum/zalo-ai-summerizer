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
    CONVERSATION_NAME_SELECTOR,
    CONVERSATION_SCROLL_CONTAINER_SELECTOR as SCROLL_CONTAINER_SELECTOR,
    CONVERSATION_SELECTORS,
    CONVERSATION_SELECTOR,
)


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
    check_cancellation(cancel_event)
    if cancel_event is None:
        page.locator(CONVERSATION_SELECTOR).first.wait_for(
            state="visible",
            timeout=15000,
        )
    else:
        _wait_for_conversation_list(page, cancel_event)
    check_cancellation(cancel_event)

    scroll_handle = page.locator(
        SCROLL_CONTAINER_SELECTOR
    ).evaluate_handle(
        """element => {
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
    )

    scroll_container = scroll_handle.as_element()
    conversations: dict[str, dict[str, str]] = {}

    def collect_visible() -> None:
        check_cancellation(cancel_event)
        visible = page.locator(
            CONVERSATION_SELECTOR
        ).evaluate_all(
            """(items, selectors) => items.map(item => ({
                name: item.querySelector(
                    selectors.name_selector
                )?.innerText.trim().replace(/\\u00a0/g, " ") || "",
                id: item.getAttribute(selectors.id_attribute) || ""
            }))""",
            CONVERSATION_SELECTORS
        )

        for item in visible:
            check_cancellation(cancel_event)
            name = item["name"]
            target_id = item["id"]
            if name and target_id:
                conversations[target_id] = {
                    "id": target_id,
                    "name": name,
                }

    try:
        if scroll_container is None:
            collect_visible()
            return list(conversations.values())

        # Phase 1: Scroll upward until reaching the top.
        unchanged_rounds = 0
        while unchanged_rounds < max_unchanged_rounds:
            check_cancellation(cancel_event)
            collect_visible()

            current_top = scroll_container.evaluate(
                "(element) => element.scrollTop"
            )
            if current_top <= 0:
                break

            scroll_container.evaluate(
                """element => {
                    element.scrollTop -= Math.max(
                        300, element.clientHeight * 0.8
                    );
                }"""
            )
            page.wait_for_timeout(800)
            check_cancellation(cancel_event)

            new_top = scroll_container.evaluate(
                "(element) => element.scrollTop"
            )
            if new_top == current_top:
                unchanged_rounds += 1
            else:
                unchanged_rounds = 0

        # Phase 2: Scroll downward until reaching the bottom.
        unchanged_rounds = 0
        while unchanged_rounds < max_unchanged_rounds:
            check_cancellation(cancel_event)
            collect_visible()

            position = scroll_container.evaluate(
                """element => ({
                    top: element.scrollTop,
                    max: element.scrollHeight - element.clientHeight
                })"""
            )
            if position["top"] >= position["max"]:
                break

            scroll_container.evaluate(
                """element => {
                    element.scrollTop += Math.max(
                        300, element.clientHeight * 0.8
                    );
                }"""
            )
            page.wait_for_timeout(800)
            check_cancellation(cancel_event)

            new_top = scroll_container.evaluate(
                "(element) => element.scrollTop"
            )
            if new_top == position["top"]:
                unchanged_rounds += 1
            else:
                unchanged_rounds = 0

        # Capture the final visible rows at the bottom.
        check_cancellation(cancel_event)
        collect_visible()

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
