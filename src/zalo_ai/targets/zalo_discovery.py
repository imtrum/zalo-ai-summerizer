from threading import Event

from playwright.sync_api import ElementHandle, Page, TimeoutError as PlaywrightTimeoutError

from zalo_ai.cancellation import check_cancellation


CONVERSATION_SELECTOR = ".msg-item"
CONVERSATION_NAME_SELECTOR = ".conv-item-title__name"
SCROLL_CONTAINER_SELECTOR = (
    ".ReactVirtualized__Grid__innerScrollContainer"
)


def discover_conversations(
    page: Page,
    max_unchanged_rounds: int = 3,
    cancel_event: Event | None = None,
) -> list[dict[str, str]]:
    """Discover conversations by scrolling to the top, then the bottom."""
    check_cancellation(cancel_event)
    page.locator(CONVERSATION_SELECTOR).first.wait_for(
        state="visible",
        timeout=15000,
    )
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
            """items => items.map(item => ({
                name: item.querySelector(
                    ".conv-item-title__name"
                )?.innerText.trim().replace(/\\u00a0/g, " ") || "",
                id: item.getAttribute("anim-data-id") || ""
            }))"""
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
        """container => {
            const viewport = container.getBoundingClientRect();

            return Array.from(
                document.querySelectorAll(".msg-item")
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
                .map(item => item.getAttribute("anim-data-id") || "")
                .filter(Boolean);
        }"""
    )


def open_visible_conversation(
    page: Page,
    target_id: str,
) -> bool:
    """Open a target only if its row is already visible in the list."""
    locator = page.locator(
        f'.msg-item[anim-data-id="{target_id}"]'
    )

    if not locator.count() or not locator.is_visible():
        return False

    locator.click()
    return True
