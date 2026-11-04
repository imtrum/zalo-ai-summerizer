"""Bounded experiments for inspecting Zalo message-list scrolling."""

from playwright.sync_api import Page

from .config import MAX_SCROLL_ROUNDS, SCROLL_WAIT_MS, SELECTORS
from .dom_inspection import (
    FIND_SCROLLER_JS,
    METRICS_JS,
    collect_messages,
)
from .message_data import date_for, message_key


def scroll_to_top_once(page: Page, handle) -> str:
    """Cuộn vùng tin nhắn lên đầu. Nếu chưa thấy gì thay đổi, caller sẽ thử thêm lăn chuột."""
    handle.evaluate("el => { el.scrollTop = 0; }")
    return "scrollTop=0"

def wheel_over(page: Page, handle) -> None:
    """Lăn chuột lên trên vùng tin nhắn (mô phỏng người dùng) - dự phòng nếu scrollTop không đủ."""
    box = handle.bounding_box()
    if box:
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.mouse.wheel(0, -800)

def run_scroll_experiment(page: Page, baseline: list[dict]) -> dict:
    """Mỗi vòng: cuộn lên ĐẦU vùng, chờ, xem có tin cũ hơn được tải thêm không.

    Vòng nào cũng không đổi gì (kể cả sau khi thử lăn chuột) thì dừng.
    """
    result = {"ran": False, "loaded_older": None, "all_keys": set(), "reseen": 0,
              "wheel_needed": None, "oldest": None}

    handle = page.evaluate_handle(FIND_SCROLLER_JS, SELECTORS["frame"]).as_element()
    if handle is None:
        print("Không tìm thấy tổ tiên cuộn được của tin nhắn -> bỏ qua thử nghiệm cuộn.")
        return result

    result["ran"] = True
    original = handle.evaluate(METRICS_JS)
    print(f"Vùng cuộn thực tế (tổ tiên cuộn được gần nhất của tin nhắn): {original}")

    baseline_keys = {message_key(m) for m in baseline}
    seen_keys = set(baseline_keys)
    reseen: set = set()
    grew_overall = False
    last_snapshot = baseline

    try:
        for round_no in range(1, MAX_SCROLL_ROUNDS + 1):
            before = handle.evaluate(METRICS_JS)
            scroll_to_top_once(page, handle)
            page.wait_for_timeout(SCROLL_WAIT_MS)
            after = handle.evaluate(METRICS_JS)
            snapshot = collect_messages(page)
            new_keys = {message_key(m) for m in snapshot} - seen_keys
            used_wheel = False

            if after["scrollHeight"] <= before["scrollHeight"] and not new_keys:
                # scrollTop = 0 có thể không kích hoạt tải thêm: thử lăn chuột một lần.
                wheel_over(page, handle)
                page.wait_for_timeout(SCROLL_WAIT_MS)
                used_wheel = True
                after = handle.evaluate(METRICS_JS)
                snapshot = collect_messages(page)
                new_keys = {message_key(m) for m in snapshot} - seen_keys
                if new_keys or after["scrollHeight"] > before["scrollHeight"]:
                    result["wheel_needed"] = True

            keys = {message_key(m) for m in snapshot}
            reseen |= keys & baseline_keys
            seen_keys |= keys
            last_snapshot = snapshot
            grew = after["scrollHeight"] > before["scrollHeight"] or bool(new_keys)
            grew_overall = grew_overall or grew

            print(f"  vòng {round_no}: scrollTop {before['scrollTop']}->{after['scrollTop']} | "
                  f"scrollHeight {before['scrollHeight']}->{after['scrollHeight']} | "
                  f"DOM={len(snapshot)} | tin mới={len(new_keys)} | "
                  f"thấy lại tin ban đầu={len(keys & baseline_keys)}"
                  + (" | (đã thử lăn chuột)" if used_wheel else ""))

            if not grew:
                print("  -> không có gì mới sau khi cuộn lên đầu (kể cả lăn chuột): dừng.")
                break
    except Exception as error:  # noqa: BLE001 - script khám phá, in lỗi rồi tiếp tục
        print(f"  Lỗi khi cuộn: {error}")
    finally:
        try:
            # Nếu đã tải thêm tin cũ thì vị trí cũ vô nghĩa -> đưa xuống cuối (tin mới nhất).
            target = "el.scrollHeight" if grew_overall else str(original["scrollTop"])
            handle.evaluate(f"el => {{ el.scrollTop = {target}; }}")
            print("Đã đưa vùng cuộn về " + ("cuối (tin mới nhất)." if grew_overall else "vị trí ban đầu."))
        except Exception as error:  # noqa: BLE001
            print(f"Không trả được vị trí cuộn ({error}); hãy tự cuộn xuống cuối.")

    result["loaded_older"] = grew_overall
    result["all_keys"] = seen_keys
    result["reseen"] = len(reseen)
    if last_snapshot:
        oldest = last_snapshot[0]
        result["oldest"] = (date_for(oldest)[0], oldest["time_text"], oldest["sender"])
    return result


# --------------------------------------------------------------------------
# 6. Tổng kết
# --------------------------------------------------------------------------
