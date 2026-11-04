"""Khám phá DOM của Zalo Web để chuẩn bị cho chức năng thu thập tin nhắn.

Script CHỈ ĐỌC: không gửi, không xóa, không sửa gì trên Zalo, không đọc cookie/token.
Việc duy nhất "tác động" tới trang là cuộn vùng tin nhắn lên đầu (có giới hạn số lần),
sau đó đưa vùng cuộn về vị trí hợp lý.

Chạy:  uv run python scripts/inspect_zalo_messages.py
       uv run python scripts/inspect_zalo_messages.py --raw   (in thêm HTML thô)
"""

import argparse

from playwright.sync_api import sync_playwright

from zalo_diagnostics.config import (
    BROWSER_PROFILE,
    MAX_SCROLL_ROUNDS,
    MISSING,
    PROJECT_ROOT,
    SCROLL_WAIT_MS,
    SELECTORS,
    VN_TZ,
)
from zalo_diagnostics.dom_inspection import (
    COLLECT_JS,
    DATE_HINTS_JS,
    FIND_SCROLLER_JS,
    METRICS_JS,
    SCROLLABLES_JS,
    collect_messages,
    inspect_date_hints,
    inspect_message_html,
    inspect_scroll_containers,
)
from zalo_diagnostics.message_data import (
    clean_text,
    date_for,
    epoch_ms_hypothesis,
    message_key,
    show,
    to_iso_date,
)
from zalo_diagnostics.reporting import (
    print_attribute_names,
    print_message_report,
    print_summary,
)
from zalo_diagnostics.scroll_experiments import (
    run_scroll_experiment,
    scroll_to_top_once,
    wheel_over,
)


def run_step(title: str, function, *args):
    """Chạy một bước; nếu lỗi thì báo và đi tiếp thay vì dừng cả script."""
    print(f"\n=== {title} ===")
    try:
        return function(*args)
    except Exception as error:  # noqa: BLE001
        print(f"[LỖI ở bước này] {type(error).__name__}: {error}")
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", action="store_true", help="in thêm HTML thô của vài tin nhắn")
    args = parser.parse_args()

    with sync_playwright() as playwright:
        # Giữ nguyên cách quản lý phiên hiện có: cùng thư mục profile với script mở trình duyệt.
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE),
            headless=False,
        )

        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://chat.zalo.me/")

            input("Hãy mở nhóm chat cần kiểm tra, đợi tin nhắn hiện ra, rồi nhấn Enter ở đây... ")

            print("\nPage title:", page.title())
            print("Current URL:", page.url)

            messages = run_step("Tin nhắn đang render trong DOM", collect_messages, page) or []
            if not messages:
                print("Không tìm thấy tin nhắn nào với selector hiện tại. Kiểm tra lại nhóm chat đã mở chưa.")
            else:
                print_message_report(messages)
                print()
                print_attribute_names(messages)

            run_step("Gợi ý về ngày tháng", inspect_date_hints, page)
            run_step("Vùng cuộn", inspect_scroll_containers, page)

            experiment = {"ran": False}
            if messages:
                experiment = run_step(
                    f"Thử nghiệm cuộn lên đầu (tối đa {MAX_SCROLL_ROUNDS} vòng)",
                    run_scroll_experiment, page, messages,
                ) or experiment

            if messages:
                run_step("Tổng kết", print_summary, messages, experiment)

            if args.raw:
                run_step("HTML thô", inspect_message_html, page)

            input("\nNhấn Enter để đóng trình duyệt... ")
        finally:
            context.close()

if __name__ == "__main__":
    main()
