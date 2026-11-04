"""Playwright DOM inspection and message extraction helpers."""

from playwright.sync_api import Page

from .config import SELECTORS
from .message_data import clean_text


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
