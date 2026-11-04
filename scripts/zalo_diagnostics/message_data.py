"""Text cleanup, date inference, and diagnostic message keys."""

from datetime import datetime, timedelta
import re
import unicodedata

from .config import MISSING, VN_TZ


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

