
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError


CONVERSATION_SELECTOR = ".msg-item"
CONVERSATION_NAME_SELECTOR = ".conv-item-title__name"
SCROLL_CONTAINER_SELECTOR = (
    ".ReactVirtualized__Grid__innerScrollContainer"
)



def discover_conversations(
    page: Page,
    max_unchanged_rounds: int = 3,
) -> list[dict[str, str]]:
    """Discover conversations by scrolling to the top, then the bottom."""
    page.locator(CONVERSATION_SELECTOR).first.wait_for(
        state="visible",
        timeout=15000,
    )

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

            new_top = scroll_container.evaluate(
                "(element) => element.scrollTop"
            )
            if new_top == position["top"]:
                unchanged_rounds += 1
            else:
                unchanged_rounds = 0

        # Capture the final visible rows at the bottom.
        collect_visible()

    finally:
        if scroll_container is not None:
            scroll_container.dispose()
        scroll_handle.dispose()

    return list(conversations.values())






def find_conversation(
    page: Page,
    target_id: str,
) -> bool:
    """Find a conversation by ID while scrolling the chat list."""
    conversations = discover_conversations(page)

    return any(
        conversation["id"] == target_id
        for conversation in conversations
    )


def open_conversation(
    page: Page,
    target_id: str,
    max_scrolls: int = 30,
) -> bool:
    """Scroll the conversation list until the target row is rendered."""
    locator = page.locator(
        f'.msg-item[anim-data-id="{target_id}"]'
    )

    if locator.count() and locator.is_visible():
        locator.click()
        return True

    container = page.locator(
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

    scroll_container = container.as_element()
    if scroll_container is None:
        container.dispose()
        return False

    try:
        # Start at the top so targets above the current position are checked.
        scroll_container.evaluate(
            "(element) => { element.scrollTop = 0; }"
        )

        for _ in range(max_scrolls):
            if locator.count() and locator.is_visible():
                locator.click()
                return True

            old_top = scroll_container.evaluate(
                "(element) => element.scrollTop"
            )
            scroll_container.evaluate(
                """element => {
                    element.scrollTop += Math.max(
                        300, element.clientHeight * 0.8
                    );
                }"""
            )
            page.wait_for_timeout(500)

            new_top = scroll_container.evaluate(
                "(element) => element.scrollTop"
            )

            if new_top == old_top:
                break

        # Check the final visible rows.
        if locator.count() and locator.is_visible():
            locator.click()
            return True

        return False

    finally:
        scroll_container.dispose()
        container.dispose()

