
import json
import re
from datetime import date, datetime, time, timedelta

from zalo_ai.config.timezone import VN_TZ
from zalo_ai.integrations.zalo.selectors import (
    FRAME_SELECTOR,
    SENDER_SELECTOR,
    TEXT_SELECTOR,
    TIME_SELECTOR,
)


COLLECT_JS = (
    """() => {
    const frames = [...document.querySelectorAll(
        __FRAME_SELECTOR__
    )];

    const clean = (value) =>
        (value || '').replace(/\\u00a0/g, ' ').replace(/\\s+/g, ' ').trim();

    const separators = [...document.querySelectorAll('*')]
        .filter(el =>
            el.children.length === 0 &&
            !el.closest(__FRAME_SELECTOR__) &&
            /^(T[2-7]\\s+\\d{1,2}\\/\\d{1,2}\\/\\d{4}|CN\\s+\\d{1,2}\\/\\d{1,2}\\/\\d{4}|Hôm nay|Hôm qua|\\d{1,2}\\/\\d{1,2}\\/\\d{4})$/i
                .test(clean(el.textContent))
        );

    return frames.map((frame, index) => {
        let row = frame;

        for (let i = 0; i < 8; i++) {
            const parent = row.parentElement;
            if (!parent ||
                parent.querySelectorAll(
                    __FRAME_SELECTOR__
                ).length !== 1) break;
            row = parent;
        }

        const sender = row.querySelector(__SENDER_SELECTOR__);
        const timeElement = row.querySelector(
            __TIME_SELECTOR__
        );

        const fullTimeElement = [...row.querySelectorAll('*')].find(el =>
            el.children.length === 0 &&
            /^\\d{1,2}:\\d{2}\\s+(\\d{1,2}\\/\\d{1,2}\\/\\d{4}|Hôm nay|Hôm qua)$/i
                .test(clean(el.textContent))
        );

        let previousDate = null;
        for (const separator of separators) {
            if (separator.compareDocumentPosition(frame) &
                Node.DOCUMENT_POSITION_FOLLOWING) {
                previousDate = separator;
            }
        }

        const ids = [];
        for (let el = frame; el; el = el.parentElement) {
            if (el.id) ids.push(el.id);
            if (el === row) break;
        }

        return {
            index,
            message_id: ids.find(id => id.startsWith('message-frame'))
                || ids[0] || null,
            sender: sender ? clean(sender.innerText) : null,
            content: [...frame.querySelectorAll(
                __TEXT_SELECTOR__
            )].map(el => clean(el.innerText)).filter(Boolean).join('\\n'),
            time_text: timeElement ? clean(timeElement.innerText) : null,
            full_time_text: fullTimeElement
                ? clean(fullTimeElement.textContent) : null,
            date_separator: previousDate ? clean(previousDate.textContent) : null
        };
    });
}""".replace("__FRAME_SELECTOR__", json.dumps(FRAME_SELECTOR))
    .replace("__TEXT_SELECTOR__", json.dumps(TEXT_SELECTOR))
    .replace("__SENDER_SELECTOR__", json.dumps(SENDER_SELECTOR))
    .replace("__TIME_SELECTOR__", json.dumps(TIME_SELECTOR))
)


def clean_text(value: str | None) -> str | None:
    if not value:
        return None
    return value.strip() or None


def parse_date(value: str | None) -> date | None:
    if not value:
        return None

    match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", value)
    if match:
        day, month, year = map(int, match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None

    lowered = value.lower()
    today = datetime.now(VN_TZ).date()

    if "hôm nay" in lowered:
        return today
    if "hôm qua" in lowered:
        return today - timedelta(days=1)

    return None


def parse_timestamp(record: dict) -> datetime | None:
    """Return a timestamp only when both date and time are identifiable."""

    full_text = record.get("full_time_text") or ""
    full_match = re.search(r"(\d{1,2}):(\d{2})\s+(.*)", full_text)

    if full_match:
        hour, minute = map(int, full_match.groups()[:2])
        message_date = parse_date(full_match.group(3))
    else:
        time_text = record.get("time_text") or ""
        time_match = re.search(r"\b(\d{1,2}):(\d{2})\b", time_text)

        if not time_match:
            return None

        hour, minute = map(int, time_match.groups())
        message_date = parse_date(record.get("date_separator"))

    if message_date is None:
        return None

    try:
        return datetime.combine(
            message_date,
            time(hour, minute),
            tzinfo=VN_TZ,
        )
    except ValueError:
        return None
