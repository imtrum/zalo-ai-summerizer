"""Khám phá DOM của Zalo Web để chuẩn bị cho chức năng thu thập tin nhắn.

Script CHỈ ĐỌC: không gửi, không xóa, không sửa gì trên Zalo, không đọc cookie/token.
Việc duy nhất "tác động" tới trang là cuộn vùng tin nhắn lên đầu (có giới hạn số lần),
sau đó đưa vùng cuộn về vị trí hợp lý.

Chạy:  uv run python scripts/inspect_zalo_messages.py
       uv run python scripts/inspect_zalo_messages.py --raw   (in thêm HTML thô)
"""

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import unicodedata

from playwright.sync_api import Page, sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BROWSER_PROFILE = PROJECT_ROOT / "data" / "browser_profile"

# Các selector dưới đây mới chỉ là PHÁT HIỆN BAN ĐẦU, script sẽ kiểm tra lại chúng.
SELECTORS = {
    "frame": '[data-component="message-content-view"]',
    "text": '[data-component="message-text-content"]',
    "sender": ".message-sender-name-content",
    "time": ".card-send-time__sendTime, .card-send-time",
}

MISSING = "<THIẾU>"
MAX_SCROLL_ROUNDS = 5       # giới hạn cứng, không cuộn vô hạn
SCROLL_WAIT_MS = 1500       # chờ Zalo tải thêm sau mỗi lần cuộn lên đầu
VN_TZ = timezone(timedelta(hours=7))


# --------------------------------------------------------------------------
# Tiện ích văn bản
# --------------------------------------------------------------------------

def clean_text(value: str | None) -> str | None:
    """Đổi \\xa0 thành khoảng trắng thường, gộp khoảng trắng thừa (giữ xuống dòng)."""
    if value is None:
        return None
    value = re.sub(r"[ \t ]+", " ", value)
    value = re.sub(r" *\n *", "\n", value).strip()
    return value or None


def to_iso_date(text: str | None) -> tuple[str | None, str]:
    """Đổi 'T4 07/10/2026' / '20:52 07/10/2026' / 'Hôm qua' thành YYYY-MM-DD.

    Trả về (ngày hoặc None, loại): 'tuyệt đối' nếu có dd/mm/yyyy, 'tương đối' nếu là
    Hôm nay/Hôm qua (tính theo ngày chạy script, chỉ đúng nếu thu thập ngay trong ngày).
    """
    if not text:
        return None, "không có"
    match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if match:
        day, month, year = (int(g) for g in match.groups())
        try:
            return f"{year:04d}-{month:02d}-{day:02d}", "tuyệt đối"
        except ValueError:
            return None, "không đọc được"
    today = datetime.now(VN_TZ).date()
    lowered = text.lower()
    if "hôm nay" in lowered:
        return today.isoformat(), "tương đối"
    if "hôm qua" in lowered:
        return (today - timedelta(days=1)).isoformat(), "tương đối"
    return None, "không đọc được"


# --------------------------------------------------------------------------
# 1. Thu thập tin nhắn đang render trong DOM
# --------------------------------------------------------------------------

# Đoạn JS dùng chung: tìm vùng cuộn gần nhất bao quanh tin nhắn đầu tiên.
FIND_SCROLLER_JS = """(frameSel) => {
    const first = document.querySelector(frameSel);
    for (let el = first && first.parentElement; el; el = el.parentElement) {
        if (/(auto|scroll)/.test(getComputedStyle(el).overflowY)
            && el.scrollHeight > el.clientHeight + 10) return el;
    }
    return null;
}"""

COLLECT_JS = """(sel) => {
    const frames = [...document.querySelectorAll(sel.frame)];
    const clean = (t) => (t || '').replace(/\\u00a0/g, ' ').replace(/\\s+/g, ' ').trim();

    // Vùng cuộn chứa tin nhắn (để chỉ tìm vạch ngày bên trong, không lẫn danh sách hội thoại).
    const findScroller = %FIND_SCROLLER%;
    const scroller = findScroller(sel.frame);
    const scope = scroller || document.body;

    // 'Vạch ngày' ứng viên: phần tử lá, nằm ngoài tin nhắn, text kiểu 'T4 07/10/2026', 'Hôm qua'.
    const sepRe = /^((T[2-7]|CN)\\s+\\d{1,2}\\/\\d{1,2}\\/\\d{4}|H[ôo]m (nay|qua)|\\d{1,2}\\/\\d{1,2}\\/\\d{4})$/i;
    const fullTimeRe = /^\\d{1,2}:\\d{2}\\s+(\\d{1,2}\\/\\d{1,2}\\/\\d{4}|H[ôo]m (nay|qua))$/i;
    const separators = [...scope.querySelectorAll('*')]
        .filter(el => el.children.length === 0 && !el.closest(sel.frame) && sepRe.test(clean(el.textContent)))
        .map(el => ({el, text: clean(el.textContent)}));

    const attrsOf = (el) => {
        const out = {};
        for (const a of el.attributes) {
            if (a.name === 'class' || a.name === 'style') continue;
            out[a.name] = a.value.slice(0, 120);
        }
        return out;
    };

    return frames.map((frame, index) => {
        // "Hàng" tin nhắn = tổ tiên cao nhất (tối đa 8 cấp) vẫn chỉ chứa đúng 1 frame này.
        let row = frame;
        for (let i = 0; i < 8; i++) {
            const p = row.parentElement;
            if (!p || p.querySelectorAll(sel.frame).length !== 1) break;
            row = p;
        }

        // Mọi phần tử từ frame -> hàng (gồm cả frame), kèm thuộc tính thô.
        const chain = [];
        for (let el = frame; el; el = el.parentElement) {
            chain.push({tag: el.tagName, attrs: attrsOf(el)});
            if (el === row) break;
        }
        // Mọi ID / data-qid trong chuỗi này (để thấy ID nào thuộc tầng nào).
        const rawIds = chain
            .filter(c => c.attrs.id || c.attrs['data-qid'])
            .map(c => ({tag: c.tag, id: c.attrs.id || null, data_qid: c.attrs['data-qid'] || null,
                        component: c.attrs['data-component'] || null}));

        // message_id: ưu tiên id bắt đầu bằng 'message-frame', rồi tới id của chính frame.
        const idItem = rawIds.find(r => r.id && /^message-frame/.test(r.id)) || rawIds.find(r => r.id);
        const qidItem = rawIds.find(r => r.data_qid);

        const senderEl = row.querySelector(sel.sender);
        const timeEl = row.querySelector(sel.time);
        const texts = [...frame.querySelectorAll(sel.text)].map(e => e.innerText.trim());

        // Giờ kèm ngày đầy đủ ('20:52 07/10/2026') nằm TRONG hàng của tin này, nếu có.
        const fullEl = [...row.querySelectorAll('*')]
            .find(e => e.children.length === 0 && fullTimeRe.test(clean(e.textContent)));

        // Vạch ngày gần nhất đứng TRƯỚC tin nhắn trong tài liệu.
        let prevSep = null;
        for (const s of separators) {
            if (s.el.compareDocumentPosition(frame) & Node.DOCUMENT_POSITION_FOLLOWING) prevSep = s;
        }

        return {
            index,
            message_id: idItem ? idItem.id : null,
            data_qid: qidItem ? qidItem.data_qid : null,
            raw_ids: rawIds,
            sender: senderEl ? senderEl.innerText.trim() : null,
            content: texts.length ? texts.join('\\n') : null,
            time_text: timeEl ? timeEl.innerText.trim() : null,
            time_attrs: timeEl ? {
                title: timeEl.getAttribute('title'),
                datetime: timeEl.getAttribute('datetime'),
                aria_label: timeEl.getAttribute('aria-label'),
            } : null,
            full_time_text: fullEl ? clean(fullEl.textContent) : null,
            date_separator: prevSep ? prevSep.text : null,
            dom_attrs: chain,
        };
    });
}""".replace("%FIND_SCROLLER%", FIND_SCROLLER_JS)


def collect_messages(page: Page) -> list[dict]:
    """Trả về danh sách tin nhắn đang có trong DOM, chỉ với trường thực sự tìm được."""
    messages = page.evaluate(COLLECT_JS, SELECTORS)
    for msg in messages:
        msg["sender"] = clean_text(msg["sender"])
        msg["content"] = clean_text(msg["content"])
        msg["time_text"] = clean_text(msg["time_text"])
        msg["full_time_text"] = clean_text(msg["full_time_text"])
        msg["date_separator"] = clean_text(msg["date_separator"])
    return messages


def message_key(msg: dict) -> tuple:
    """Khóa nhận diện cùng một tin nhắn.

    Ưu tiên ID của DOM. Nếu không có ID thì dùng bộ (người gửi, giờ, nội dung) và đánh
    dấu là khóa 'yếu' (weak): hai tin nhắn khác nhau vẫn có thể trùng khóa này.
    """
    if msg["message_id"]:
        return ("id", msg["message_id"])
    content = unicodedata.normalize("NFKC", msg["content"]) if msg["content"] else None
    return ("weak", msg["sender"], msg["time_text"], content)


# --------------------------------------------------------------------------
# 2. Báo cáo từng tin nhắn
# --------------------------------------------------------------------------

def show(value) -> str:
    return MISSING if value in (None, "") else repr(value)


def date_for(msg: dict) -> tuple[str | None, str]:
    """Ngày tốt nhất tìm được cho tin nhắn, kèm nguồn. Không bịa: không có thì None."""
    full, kind = to_iso_date(msg["full_time_text"])
    if full:
        return full, f"giờ đầy đủ trong hàng ({kind})"
    sep, kind = to_iso_date(msg["date_separator"])
    if sep:
        return sep, f"vạch ngày phía trên ({kind}) - suy luận theo vị trí"
    return None, "chưa xác định"


def epoch_ms_hypothesis(msg: dict) -> str:
    """GIẢ THUYẾT chưa kiểm chứng: dãy 13 số cuối của ID/qid là timestamp (mili-giây).

    Chỉ so khớp với giờ (và ngày nếu có) đã hiển thị, KHÔNG phải kết luận.
    """
    raw = msg["message_id"] or msg["data_qid"]
    if not raw:
        return "n/a (không có ID)"
    match = re.search(r"(\d{13})$", raw)
    if not match:
        return "n/a (không có dãy 13 chữ số ở cuối)"
    try:
        moment = datetime.fromtimestamp(int(match.group(1)) / 1000, VN_TZ)
    except (OverflowError, OSError, ValueError):
        return "n/a (không đổi được thành ngày)"
    text = f"nếu là epoch-ms (UTC+7) -> {moment:%Y-%m-%d %H:%M:%S}"
    checks = []
    if msg["time_text"]:
        checks.append("giờ " + ("KHỚP" if moment.strftime("%H:%M") == msg["time_text"] else "KHÔNG khớp"))
    shown_date, _ = date_for(msg)
    if shown_date:
        checks.append("ngày " + ("KHỚP" if moment.date().isoformat() == shown_date else "KHÔNG khớp"))
    return text + (" | " + ", ".join(checks) if checks else "")


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

DATE_HINTS_JS = """(frameSel) => {
    const pattern = /(h[ôo]m nay|h[ôo]m qua|\\b\\d{1,2}\\s*[\\/\\-.]\\s*\\d{1,2}(\\s*[\\/\\-.]\\s*\\d{2,4})?\\b)/i;
    const findScroller = %FIND_SCROLLER%;
    const scope = findScroller(frameSel) || document.body;
    return [...scope.querySelectorAll('*')]
        .filter(el => {
            const t = (el.textContent || '').trim();
            return t.length > 0 && t.length <= 40 && el.children.length === 0 && pattern.test(t);
        })
        .slice(0, 30)
        .map(el => ({
            text: el.textContent.replace(/\\u00a0/g, ' ').trim(),
            tag: el.tagName,
            className: String(el.className || '').slice(0, 100),
            insideMessageFrame: !!el.closest(frameSel),
        }));
}""".replace("%FIND_SCROLLER%", FIND_SCROLLER_JS)


def inspect_date_hints(page: Page) -> list[dict]:
    """Phần tử giống ngày, chỉ tìm TRONG vùng cuộn tin nhắn (không lẫn danh sách hội thoại)."""
    hints = page.evaluate(DATE_HINTS_JS, SELECTORS["frame"])
    print("Phần tử có text giống ngày trong vùng tin nhắn (ứng viên, CHƯA phải kết luận):")
    if not hints:
        print("  (không tìm thấy)")
    for item in hints:
        print(f"  {item}")
    return hints


# --------------------------------------------------------------------------
# 4. Vùng cuộn
# --------------------------------------------------------------------------

SCROLLABLES_JS = """(frameSel) => {
    const firstFrame = document.querySelector(frameSel);
    return [...document.querySelectorAll('*')]
        .filter(el => /(auto|scroll)/.test(getComputedStyle(el).overflowY)
                      && el.scrollHeight > el.clientHeight + 50)
        .map(el => ({
            tag: el.tagName,
            className: String(el.className || '').slice(0, 100),
            scrollHeight: el.scrollHeight,
            clientHeight: el.clientHeight,
            scrollTop: Math.round(el.scrollTop),
            containsMessages: !!firstFrame && el.contains(firstFrame),
            messageCount: el.querySelectorAll(frameSel).length,
        }))
        .slice(0, 20);
}"""

METRICS_JS = "el => ({scrollTop: Math.round(el.scrollTop), scrollHeight: el.scrollHeight, clientHeight: el.clientHeight})"


def inspect_scroll_containers(page: Page) -> None:
    items = page.evaluate(SCROLLABLES_JS, SELECTORS["frame"])
    print("Mọi phần tử cuộn được (overflow-y auto/scroll và scrollHeight > clientHeight):")
    if not items:
        print("  (không tìm thấy)")
    for item in items:
        flag = "  <-- chứa tin nhắn" if item["containsMessages"] else ""
        print(f"  {item}{flag}")


# --------------------------------------------------------------------------
# 5. Thử nghiệm cuộn có giới hạn
# --------------------------------------------------------------------------

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

def inspect_message_html(page: Page, sample_size: int = 2) -> None:
    frames = page.locator(SELECTORS["frame"])
    for i in range(min(frames.count(), sample_size)):
        print(f"\n--- Frame {i + 1} ---")
        print(frames.nth(i).evaluate("el => el.outerHTML.slice(0, 2500)"))
        print("\nParent HTML:")
        print(frames.nth(i).locator("xpath=..").evaluate("el => el.outerHTML.slice(0, 3500)"))


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

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