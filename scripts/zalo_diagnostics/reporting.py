"""Console reports for the Zalo message inspection utility."""

from .config import MISSING
from .message_data import (
    date_for,
    epoch_ms_hypothesis,
    message_key,
    show,
    to_iso_date,
)


def print_message_report(messages: list[dict], sample_size: int = 10) -> None:
    print(f"Số phần tử tin nhắn trong DOM: {len(messages)}")
    fields = ["message_id", "data_qid", "sender", "content", "time_text", "full_time_text", "date_separator"]
    for field in fields:
        have = sum(1 for m in messages if m[field])
        print(f"  {field:<15}: có {have}/{len(messages)}, thiếu {len(messages) - have}")

    print(f"\n--- {min(sample_size, len(messages))} tin nhắn đầu tiên trong DOM ---")
    for msg in messages[:sample_size]:
        content = msg["content"]
        preview = content if content is None or len(content) <= 70 else content[:70] + "…"
        date_value, date_source = date_for(msg)
        print(f"\n#{msg['index']}")
        print(f"  message_id     : {show(msg['message_id'])}")
        print(f"  data_qid       : {show(msg['data_qid'])}")
        print(f"  mọi ID quanh tin: {msg['raw_ids'] if msg['raw_ids'] else MISSING}")
        print(f"  sender         : {show(msg['sender'])}")
        print(f"  time_text      : {show(msg['time_text'])}")
        print(f"  giờ đầy đủ     : {show(msg['full_time_text'])}")
        print(f"  vạch ngày trên : {show(msg['date_separator'])}")
        print(f"  ngày suy ra    : {date_value or 'chưa xác định'}  [{date_source}]")
        print(f"  content        : {show(preview)}")
        print(f"  giả thuyết ID  : {epoch_ms_hypothesis(msg)}")

    print("\nGhi chú: sender thiếu có thể do Zalo gộp các tin liên tiếp của cùng một người;")
    print("content thiếu có thể là ảnh/sticker/file. Cả hai cần xác minh bằng mắt.")

def print_attribute_names(messages: list[dict]) -> None:
    """Liệt kê tên thuộc tính xuất hiện trên frame và các tổ tiên của nó."""
    seen: dict[str, int] = {}
    for msg in messages:
        for level in msg["dom_attrs"]:
            for name in level["attrs"]:
                seen[name] = seen.get(name, 0) + 1
    print("Các thuộc tính DOM (trừ class/style) xuất hiện quanh tin nhắn:")
    for name, count in sorted(seen.items(), key=lambda kv: -kv[1]):
        print(f"  {name:<28} {count} lần")


# --------------------------------------------------------------------------
# 3. Ngày tháng: tìm dấu hiệu ngoài giờ HH:MM
# --------------------------------------------------------------------------

def print_summary(baseline: list[dict], experiment: dict) -> None:
    total = len(baseline)
    keys = [message_key(m) for m in baseline]
    weak = sum(1 for k in keys if k[0] == "weak")
    duplicates = total - len(set(keys))
    dated = sum(1 for m in baseline if date_for(m)[0])
    from_full = sum(1 for m in baseline if to_iso_date(m["full_time_text"])[0])
    from_sep = sum(1 for m in baseline if to_iso_date(m["date_separator"])[0])

    print(f"Tin nhắn trong DOM lúc bắt đầu      : {total}")
    print(f"  - nhận diện bằng ID DOM             : {total - weak}")
    print(f"  - chỉ có khóa yếu (sender+giờ+nội dung): {weak}")
    print(f"  - trùng khóa trong cùng một lần quét: {duplicates}"
          + ("  (với khóa yếu, trùng chưa chắc là cùng một tin)" if weak else ""))
    for field in ("message_id", "data_qid", "sender", "content", "time_text"):
        print(f"  - thiếu {field:<10}: {sum(1 for m in baseline if not m[field])}")
    print(f"  - có ngày suy ra được               : {dated}/{total} "
          f"(từ giờ đầy đủ: {from_full}, từ vạch ngày: {from_sep})")

    mismatches = [m for m in baseline if "KHÔNG khớp" in epoch_ms_hypothesis(m)]
    matched = [m for m in baseline
               if "KHỚP" in epoch_ms_hypothesis(m) and m not in mismatches]
    print(f"  - giả thuyết ID=epoch-ms: có tin khớp {len(matched)}, có tin lệch {len(mismatches)}")

    if experiment["ran"]:
        print(f"Tổng số tin nhắn khác nhau sau khi cuộn: {len(experiment['all_keys'])}")
        print(f"Tin cũ được tải thêm khi cuộn lên đầu : {'CÓ' if experiment['loaded_older'] else 'KHÔNG thấy'}")
        if experiment["wheel_needed"] is not None:
            print("  (cần lăn chuột mới tải thêm; chỉ đặt scrollTop là chưa đủ)")
        print(f"Tin ban đầu nhận ra lại được sau khi cuộn: {experiment['reseen']}/{total}")
        if experiment["oldest"]:
            print(f"Tin cũ nhất đang trong DOM (ngày, giờ, người gửi): {experiment['oldest']}")
    else:
        print("Thử nghiệm cuộn: KHÔNG chạy được.")

    print("\nCHƯA XÁC MINH ĐƯỢC (script không tự kết luận):")
    print(" - Ngày suy ra từ 'vạch ngày' là suy luận theo vị trí; 'Hôm nay/Hôm qua' chỉ đúng nếu thu thập trong ngày.")
    print(" - ID/data-qid có phải timestamp: xem dòng 'giả thuyết ID' và số tin khớp/lệch ở trên.")
    print(" - Zalo có gỡ tin khỏi DOM khi cuộn xa không (so 'DOM=' giữa các vòng).")
    print(" - Hành vi ở nhóm khác, nhóm rất dài, hoặc kiểu tin nhắn khác (ảnh, file, trả lời, thu hồi).")


# --------------------------------------------------------------------------
# 7. HTML thô (tùy chọn)
# --------------------------------------------------------------------------
