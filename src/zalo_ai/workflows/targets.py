from playwright.sync_api import sync_playwright

from zalo_ai.targets.json_store import add_selected_targets, ensure_targets_file
from zalo_ai.targets.zalo_discovery import discover_conversations
from .browser import ProgressCallback, notify, open_zalo


def discover_target_conversations(
    on_status: ProgressCallback | None = None,
) -> list[dict[str, str]]:
    """Open Zalo and discover conversations for the target refresh screen."""
    with sync_playwright() as playwright:
        context, page = _open_zalo(on_status, playwright)

        try:
            notify(on_status, "Discovering conversations.")
            return discover_conversations(page)
        finally:
            context.close()


def save_discovered_targets(
    conversations: list[dict[str, str]],
) -> int:
    """Save selected discovered conversations to the target store."""
    ensure_targets_file()
    return add_selected_targets(conversations)
