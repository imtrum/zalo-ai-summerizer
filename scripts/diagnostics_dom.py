"""Inspect conversation rows and their scroll container in Zalo Web."""

from playwright.sync_api import sync_playwright

from zalo_ai.integrations.zalo.selectors import (
    CONVERSATION_SCROLL_CONTAINER_SELECTOR,
    CONVERSATION_SELECTOR,
    CONVERSATION_SELECTORS,
)
from zalo_ai.paths import BROWSER_PROFILE


def inspect_chat_list() -> None:
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE), headless=False
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://chat.zalo.me/")
            input("Wait for Zalo to load and your conversations to appear, then press Enter here...")
            scroll_info = page.locator(
                CONVERSATION_SCROLL_CONTAINER_SELECTOR
            ).evaluate("""element => {
                const ancestors = [];
                for (let current = element; current && current !== document.body;
                     current = current.parentElement) {
                    ancestors.push({tag: current.tagName,
                        className: String(current.className),
                        scrollTop: current.scrollTop,
                        clientHeight: current.clientHeight,
                        scrollHeight: current.scrollHeight,
                        canScroll: current.scrollHeight > current.clientHeight});
                }
                return ancestors;
            }""")
            print("\nConversation-list ancestors:")
            for item in scroll_info:
                print(item)
            handle = page.locator(CONVERSATION_SCROLL_CONTAINER_SELECTOR).evaluate_handle(
                """element => {
                    for (let current = element; current && current !== document.body;
                         current = current.parentElement) {
                        const style = getComputedStyle(current);
                        if (current.scrollHeight > current.clientHeight &&
                            ["auto", "scroll", "overlay"].includes(style.overflowY))
                            return current;
                    }
                    return null;
                }"""
            )
            container = handle.as_element()
            if container is None:
                print("\nNo scrollable ancestor was found. Collecting currently visible conversations only.")
            else:
                print("\nFound a scrollable conversation container.")
            names: set[str] = set()
            conversations: list[dict] = []
            unchanged = 0
            previous = -1
            while unchanged < 3:
                visible = page.locator(CONVERSATION_SELECTOR).evaluate_all(
                    """(items, selectors) => items.map(item => {
                        const name = item.querySelector(selectors.name_selector);
                        return {name: name ? name.innerText.trim().replace(/\\u00a0/g, " ") : null,
                            element_id: item.id || null,
                            data_id: item.getAttribute(selectors.data_id_attribute),
                            anim_data_id: item.getAttribute(selectors.id_attribute)};
                    })""", CONVERSATION_SELECTORS
                )
                for item in visible:
                    if item["name"] and item["name"] not in names:
                        names.add(item["name"])
                        conversations.append(item)
                if container is None:
                    break
                top = container.evaluate("element => element.scrollTop")
                container.evaluate("element => { element.scrollTop += Math.max(300, element.clientHeight * 0.8); }")
                page.wait_for_timeout(800)
                new_top = container.evaluate("element => element.scrollTop")
                unchanged = unchanged + 1 if new_top == top or new_top == previous else 0
                previous = new_top
            print(f"\nDiscovered {len(conversations)} conversations:")
            for index, item in enumerate(conversations, start=1):
                print(f"{index}. name={item['name']!r}, element_id={item['element_id']!r}, data_id={item['data_id']!r}, anim_data_id={item['anim_data_id']!r}")
        finally:
            context.close()
