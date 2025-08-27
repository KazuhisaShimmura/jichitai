
import re
from datetime import datetime, date
from typing import Optional

ERA = {
    '令和': 2018,  # year offset: Gregorian = base + n (R1=2019 -> base 2018)
    '平成': 1988,
    '昭和': 1925,
}

def normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def _jp_era_to_year(era: str, y: int) -> int:
    base = ERA.get(era)
    if base is None:
        return y
    return base + y

def parse_jp_date(text: str) -> Optional[date]:
    """
    Accepts: '令和6年4月1日', '令和6年04月01日', '2025年4月1日', '2025/4/1', '2025-04-01'
    Returns a date or None.
    """
    if not text:
        return None
    text = text.strip()

    # ISO-like
    m = re.search(r"(\d{4})[-/年.](\d{1,2})[-/月.](\d{1,2})日?", text)
    if m:
        y, mo, d = map(int, m.groups())
        try:
            return date(y, mo, d)
        except ValueError:
            return None

    # Japanese era
    m = re.search(r"(令和|平成|昭和)\s*(\d{1,2}|元)年\s*(\d{1,2})月\s*(\d{1,2})日?", text)
    if m:
        era, yy_str, mo, dd = m.groups()
        yy = 1 if yy_str == '元' else int(yy_str)
        y = _jp_era_to_year(era, yy)
        try:
            return date(y, int(mo), int(dd))
        except ValueError:
            return None
    return None

DATE_RANGE_KEYWORDS = [
    "募集期間", "申請期間", "受付期間", "応募期間", "申込期間",
    "公募期間", "実施期間", "申請受付", "受付開始", "申請開始"
]

def parse_date_range(text: str):
    """
    Returns (start_iso, end_iso) if found, else (None, None).
    Handles '2025年4月1日～2025年5月31日', '～2025年5月31日まで'.
    """
    if not text: return (None, None)

    keyword_pattern = "|".join(DATE_RANGE_KEYWORDS)
    date_pattern_text = r"((?:令和|平成|昭和)?\s*(?:\d{1,4}|元)年\s*\d{1,2}月\s*\d{1,2}日?)"

    # パターン1: 「キーワード 日付1 から 日付2 まで」
    m = re.search(
        rf"({keyword_pattern})\s*[:：]?\s*(?P<s>{date_pattern_text})\s*[～〜\-から]\s*(?P<e>{date_pattern_text})", text
    )
    if m:
        s = parse_jp_date(m.group("s"))
        e = parse_jp_date(m.group("e"))
        return (s.isoformat() if s else None, e.isoformat() if e else None)

    # パターン2: 「キーワード 日付 から」
    m = re.search(rf"({keyword_pattern})\s*[:：]?\s*(?P<s>{date_pattern_text})\s*(?:から|より|開始)", text)
    if m:
        s = parse_jp_date(m.group("s"))
        return (s.isoformat() if s else None, None)

    # パターン3: 「キーワード ～ 日付 まで」
    m = re.search(rf"({keyword_pattern})?\s*[:：]?\s*[～〜]\s*(?P<e>{date_pattern_text})\s*(?:まで|締切|必着)", text)
    if m:
        e = parse_jp_date(m.group("e"))
        return (None, e.isoformat() if e else None)

    # 既存のキーワードなしパターンも残す
    m = re.search(r"(?P<s>" + date_pattern_text + r")\s*[～~\-から〜]\s*(?P<e>" + date_pattern_text + r")", text)
    if m:
        s, e = parse_jp_date(m.group('s')), parse_jp_date(m.group('e'))
        return (s.isoformat() if s else None, e.isoformat() if e else None)
    m = re.search(r"(?P<e>" + date_pattern_text + r")\s*まで", text)
    if m:
        e = parse_jp_date(m.group('e'))
        return (None, e.isoformat() if e else None)
    return (None, None)

def extract_money(text: str) -> Optional[str]:
    if not text: return None
    m = re.search(r"(最大)?\s*([0-9,\.]+)\s*(円|万円|億円)", text)
    if m:
        return "".join([x for x in m.groups() if x])
    return None

def extract_rate(text: str) -> Optional[str]:
    if not text: return None
    # 1/2, 2/3, 4分の3, 50%
    m = re.search(r"(\d+\/\d+|\d{1,3}\s*%|\d+分の\d+)", text)
    return m.group(0) if m else None
