
from playwright.sync_api import ElementHandle, Page


FRAME_SELECTOR = '[data-component="message-content-view"]'

FIND_SCROLLER_JS = """(frameSel) => {
    const first = document.querySelector(frameSel);

    for (let el = first && first.parentElement; el; el = el.parentElement) {
        if (
            /(auto|scroll)/.test(getComputedStyle(el).overflowY) &&
            el.scrollHeight > el.clientHeight + 10
        ) {
            return el;
        }
    }

    return null;
}"""


class ZaloScrollHelper:
    """Find and scroll the message-history container in Zalo Web."""

    def __init__(self, page: Page) -> None:
        self.page = page

    def find_scroller(self) -> ElementHandle | None:
        """Return the message-history scrollable element, if found."""
        handle = self.page.evaluate_handle(
            FIND_SCROLLER_JS,
            FRAME_SELECTOR,
        )

        element = handle.as_element()
        if element is None:
            handle.dispose()

        return element

    def scroll_up(self, scroller: ElementHandle) -> None:
        """Scroll the message-history container to its top."""
        scroller.evaluate("(el) => { el.scrollTop = 0; }")

    def scroll_up_with_wheel(self, scroller: ElementHandle) -> None:
        """Use a mouse-wheel gesture over the message-history container."""
        box = scroller.bounding_box()
        if box is None:
            return

        self.page.mouse.move(
            box["x"] + box["width"] / 2,
            box["y"] + box["height"] / 2,
        )
        self.page.mouse.wheel(0, -800)
