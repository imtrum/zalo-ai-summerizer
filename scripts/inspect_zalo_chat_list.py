
from pathlib import Path

from playwright.sync_api import sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BROWSER_PROFILE = PROJECT_ROOT / "data" / "browser_profile"


def main() -> None:
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE),
            headless=False,
        )

        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://chat.zalo.me/")

            input(
                "Wait for Zalo to load and your conversations to appear, "
                "then press Enter here..."
            )

            # Inspect the ancestors of the conversation list.
            scroll_info = page.locator(
                ".ReactVirtualized__Grid__innerScrollContainer"
            ).evaluate(
                """element => {
                    const ancestors = [];
                    let current = element;

                    while (current && current !== document.body) {
                        ancestors.push({
                            tag: current.tagName,
                            className: String(current.className),
                            scrollTop: current.scrollTop,
                            clientHeight: current.clientHeight,
                            scrollHeight: current.scrollHeight,
                            canScroll:
                                current.scrollHeight > current.clientHeight
                        });

                        current = current.parentElement;
                    }

                    return ancestors;
                }"""
            )

            print("\nConversation-list ancestors:")
            for item in scroll_info:
                print(item)

            # Find the nearest ancestor that can scroll vertically.
            scroll_container = page.locator(
                ".ReactVirtualized__Grid__innerScrollContainer"
            ).evaluate_handle(
                """element => {
                    let current = element;

                    while (current && current !== document.body) {
                        const style = getComputedStyle(current);
                        const hasScrollableContent =
                            current.scrollHeight > current.clientHeight;

                        const allowsVerticalScroll =
                            ["auto", "scroll", "overlay"].includes(
                                style.overflowY
                            );

                        if (hasScrollableContent && allowsVerticalScroll) {
                            return current;
                        }

                        current = current.parentElement;
                    }

                    return null;
                }"""
            )

            if scroll_container.as_element() is None:
                print(
                    "\nNo scrollable ancestor was found. "
                    "Collecting currently visible conversations only."
                )
                scroll_container = None
            else:
                print("\nFound a scrollable conversation container.")

            seen_names: set[str] = set()
            conversations: list[dict[str, str | None]] = []

            unchanged_rounds = 0
            previous_scroll_top = -1

            while unchanged_rounds < 3:
                # Collect currently rendered conversations and ID attributes.
                visible_conversations = page.locator(
                    ".msg-item"
                ).evaluate_all(
                    """items => items.map(item => {
                        const name = item.querySelector(
                            ".conv-item-title__name"
                        );

                        return {
                            name: name
                                ? name.innerText.trim().replace(/\\u00a0/g, " ")
                                : null,
                            element_id: item.id || null,
                            data_id: item.getAttribute("data-id"),
                            anim_data_id: item.getAttribute("anim-data-id"),
                        };
                    })"""
                )

                for conversation in visible_conversations:
                    name = conversation["name"]

                    if name and name not in seen_names:
                        seen_names.add(name)
                        conversations.append(conversation)

                if scroll_container is None:
                    break

                element = scroll_container.as_element()

                if element is None:
                    break

                # Scroll the actual conversation-list container.
                current_scroll_top = element.evaluate(
                    "(element) => element.scrollTop"
                )

                element.evaluate(
                    """element => {
                        element.scrollTop += Math.max(
                            300,
                            element.clientHeight * 0.8
                        );
                    }"""
                )

                page.wait_for_timeout(800)

                new_scroll_top = element.evaluate(
                    "(element) => element.scrollTop"
                )

                if (
                    new_scroll_top == current_scroll_top
                    or new_scroll_top == previous_scroll_top
                ):
                    unchanged_rounds += 1
                else:
                    unchanged_rounds = 0

                previous_scroll_top = new_scroll_top

            print(f"\nDiscovered {len(conversations)} conversations:")

            for index, conversation in enumerate(conversations, start=1):
                print(
                    f"{index}. "
                    f"name={conversation['name']!r}, "
                    f"element_id={conversation['element_id']!r}, "
                    f"data_id={conversation['data_id']!r}, "
                    f"anim_data_id={conversation['anim_data_id']!r}"
                )

        finally:
            context.close()


if __name__ == "__main__":
    main()
