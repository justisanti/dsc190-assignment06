"""Natural-language date parsing."""

import calendar
import re
from collections.abc import Callable
from datetime import date, timedelta

_MONTH_NAMES = [
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
]
MONTHS: dict[str, int] = {}
for _i, _name in enumerate(_MONTH_NAMES, start=1):
    MONTHS[_name] = _i
    MONTHS[_name[:3]] = _i
MONTHS["sept"] = 9

_WEEKDAY_NAMES = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]
WEEKDAYS: dict[str, int] = {}
for _i, _name in enumerate(_WEEKDAY_NAMES):
    WEEKDAYS[_name] = _i
    WEEKDAYS[_name[:3]] = _i
WEEKDAYS.update({"tues": 1, "weds": 2, "thur": 3, "thurs": 3})

_ONES = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}
_TENS = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}
_ORDINAL_WORDS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
    "eleventh": 11,
    "twelfth": 12,
    "thirteenth": 13,
    "fourteenth": 14,
    "fifteenth": 15,
    "sixteenth": 16,
    "seventeenth": 17,
    "eighteenth": 18,
    "nineteenth": 19,
    "twentieth": 20,
    "thirtieth": 30,
}

_UNITS = {
    "day": "day",
    "days": "day",
    "week": "week",
    "weeks": "week",
    "wk": "week",
    "wks": "week",
    "fortnight": "fortnight",
    "fortnights": "fortnight",
    "month": "month",
    "months": "month",
    "mo": "month",
    "mos": "month",
    "year": "year",
    "years": "year",
    "yr": "year",
    "yrs": "year",
}

_HOLIDAYS = {
    "christmas": (12, 25),
    "christmas day": (12, 25),
    "xmas": (12, 25),
    "christmas eve": (12, 24),
    "new years": (1, 1),
    "new years day": (1, 1),
    "new years eve": (12, 31),
    "valentines day": (2, 14),
    "halloween": (10, 31),
    "independence day": (7, 4),
}

_NEXT_MODS = {"next", "coming", "upcoming"}
_LAST_MODS = {"last", "previous", "past"}
_THIS_MODS = {"this"}
_CONNECTORS = {"before", "after", "from"}

_ISO_RE = re.compile(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$")
_NUM_RE = re.compile(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2}|\d{4})$")
_MD_RE = re.compile(r"^(\d{1,2})/(\d{1,2})$")

# (months, days)
Offset = tuple[int, int]


def parse(s: str, today: date | None = None) -> date:
    """Turn a natural-language date such as "next Tuesday" into a date.

    ``today`` is the reference point for relative expressions and defaults to
    the current date. Raises ValueError if the input is not recognized.
    """
    if today is None:
        today = date.today()
    tokens = _normalize(s)
    if not tokens:
        raise ValueError(f"Cannot parse date from {s!r}")
    try:
        return _parse_tokens(tokens, today)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"Cannot parse date from {s!r}") from exc


def _normalize(s: str) -> list[str]:
    s = s.lower().replace("\u2019", "").replace("'", "")
    s = s.replace(",", " ").replace(";", " ")
    s = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", s)
    s = re.sub(r"(?<=\d)(?=[a-z])", " ", s)
    s = re.sub(r"(?<=[a-z])-(?=[a-z])", " ", s)
    tokens = [t.rstrip(".") for t in s.split()]
    return [t for t in tokens if t and t not in {"the", "on"}]


def _add_months(d: date, months: int) -> date:
    total = d.year * 12 + (d.month - 1) + months
    year, month0 = divmod(total, 12)
    month = month0 + 1
    if not 1 <= year <= 9999:
        raise ValueError("year out of range")
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _shift(anchor: date, offset: Offset, sign: int) -> date:
    months, days = offset
    return _add_months(anchor, sign * months) + timedelta(days=sign * days)


def _unit_offset(unit: str, n: int) -> Offset:
    if unit == "day":
        return (0, n)
    if unit == "week":
        return (0, 7 * n)
    if unit == "fortnight":
        return (0, 14 * n)
    if unit == "month":
        return (n, 0)
    return (12 * n, 0)


def _words_to_int(tokens: list[str]) -> int | None:
    if not tokens:
        return None
    current = 0
    for tok in tokens:
        if tok in _ONES:
            current += _ONES[tok]
        elif tok in _TENS:
            current += _TENS[tok]
        elif tok == "hundred":
            current = max(current, 1) * 100
        else:
            return None
    return current


def _parse_quantity(tokens: list[str]) -> int | None:
    if not tokens:
        return 1
    t = list(tokens)
    if t[0] in {"a", "an"}:
        t = t[1:]
        if not t:
            return 1
    if t[-1] == "of":
        t = t[:-1]
    if t == ["couple"]:
        return 2
    if len(t) == 1 and t[0].isdigit():
        return int(t[0])
    return _words_to_int(t)


def _parse_offset(tokens: list[str]) -> Offset | None:
    """Parse e.g. ``1 year and 2 months`` into (months, days)."""
    months = 0
    days = 0
    pending: list[str] = []
    seen_unit = False
    for tok in tokens:
        if tok == "and":
            if pending:
                return None
        elif tok in _UNITS:
            qty = _parse_quantity(pending)
            if qty is None:
                return None
            pending = []
            m, d = _unit_offset(_UNITS[tok], qty)
            months += m
            days += d
            seen_unit = True
        else:
            pending.append(tok)
    if pending or not seen_unit:
        return None
    return months, days


def _parse_tokens(tokens: list[str], today: date) -> date:
    # "<offset> before/after/from <anything>", e.g. "5 days before tomorrow"
    for i, tok in enumerate(tokens):
        if tok not in _CONNECTORS or i == 0 or i + 1 >= len(tokens):
            continue
        offset = _parse_offset(tokens[:i])
        if offset is None:
            continue
        try:
            anchor = _parse_tokens(tokens[i + 1 :], today)
        except ValueError:
            continue
        return _shift(anchor, offset, -1 if tok == "before" else 1)

    # "in <offset>"
    if tokens[0] == "in":
        rest = tokens[1:]
        if rest and rest[-1] == "time":
            rest = rest[:-1]
        offset = _parse_offset(rest)
        if offset is not None:
            return _shift(today, offset, 1)

    # "<offset> ago" / "<offset> hence" / "<offset> later"
    if len(tokens) > 1 and tokens[-1] in {"ago", "hence", "later"}:
        offset = _parse_offset(tokens[:-1])
        if offset is not None:
            return _shift(today, offset, -1 if tokens[-1] == "ago" else 1)

    return _parse_term(tokens, today)


Handler = Callable[[list[str], date], date | None]


def _parse_term(tokens: list[str], today: date) -> date:
    handlers: tuple[Handler, ...] = (
        _simple_word,
        _next_last_unit,
        _weekday_expr,
        _boundary,
        _absolute,
        _holiday,
    )
    for handler in handlers:
        result = handler(tokens, today)
        if result is not None:
            return result
    raise ValueError("unrecognized date")


def _simple_word(tokens: list[str], today: date) -> date | None:
    if len(tokens) != 1:
        return None
    word = tokens[0]
    if word in {"today", "now", "tonight"}:
        return today
    if word in {"tomorrow", "tmrw", "tmr"}:
        return today + timedelta(days=1)
    if word == "yesterday":
        return today - timedelta(days=1)
    return None


def _sign_for_mod(mod: str) -> int | None:
    if mod in _NEXT_MODS:
        return 1
    if mod in _LAST_MODS:
        return -1
    if mod in _THIS_MODS:
        return 0
    return None


def _next_last_unit(tokens: list[str], today: date) -> date | None:
    if len(tokens) != 2 or tokens[1] not in _UNITS:
        return None
    sign = _sign_for_mod(tokens[0])
    if sign is None:
        return None
    return _shift(today, _unit_offset(_UNITS[tokens[1]], 1), sign)


def _weekday_expr(tokens: list[str], today: date) -> date | None:
    wd = today.weekday()
    if len(tokens) == 1 and tokens[0] in WEEKDAYS:
        return today + timedelta(days=(WEEKDAYS[tokens[0]] - wd) % 7)
    if len(tokens) == 2 and tokens[1] in WEEKDAYS:
        idx = WEEKDAYS[tokens[1]]
        sign = _sign_for_mod(tokens[0])
        if sign == 1:
            return today + timedelta(days=(idx - wd) % 7 or 7)
        if sign == -1:
            return today - timedelta(days=(wd - idx) % 7 or 7)
        if sign == 0:
            return today + timedelta(days=(idx - wd) % 7)
        return None
    # "tuesday next week", "friday of last week"
    rest = [t for t in tokens[1:] if t != "of"]
    if (
        tokens
        and tokens[0] in WEEKDAYS
        and len(rest) == 2
        and rest[1] == "week"
        and (sign := _sign_for_mod(rest[0])) is not None
    ):
        monday = today - timedelta(days=wd) + timedelta(weeks=sign)
        return monday + timedelta(days=WEEKDAYS[tokens[0]])
    return None


def _boundary(tokens: list[str], today: date) -> date | None:
    """Handle "end of the month", "first day of next year", etc."""
    if tokens[:2] in (["first", "day"], ["last", "day"]) and tokens[2:3] == ["of"]:
        is_end = tokens[0] == "last"
        rest = tokens[3:]
    elif tokens[:1] in (["start"], ["beginning"], ["begin"], ["end"]):
        if tokens[1:2] != ["of"]:
            return None
        is_end = tokens[0] == "end"
        rest = tokens[2:]
    else:
        return None

    if len(rest) == 1 and rest[0] in _UNITS:
        rest = ["this", rest[0]]
    if len(rest) == 2 and rest[1] in _UNITS:
        sign = _sign_for_mod(rest[0])
        if sign is None:
            return None
        unit = _UNITS[rest[1]]
        ref = _shift(today, _unit_offset(unit, 1), sign)
        if unit == "month":
            day = calendar.monthrange(ref.year, ref.month)[1] if is_end else 1
            return ref.replace(day=day)
        if unit == "year":
            return date(ref.year, 12, 31) if is_end else date(ref.year, 1, 1)
        if unit == "week":
            monday = ref - timedelta(days=ref.weekday())
            return monday + timedelta(days=6 if is_end else 0)
        return None
    # "end of december", "start of february 2024"
    if rest and rest[0] in MONTHS and len(rest) <= 2:
        year = today.year
        if len(rest) == 2:
            if not (rest[1].isdigit() and len(rest[1]) == 4):
                return None
            year = int(rest[1])
        month = MONTHS[rest[0]]
        day = calendar.monthrange(year, month)[1] if is_end else 1
        return date(year, month, day)
    return None


def _convert_ordinal_words(tokens: list[str]) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
        if tok in {"twenty", "thirty"} and 1 <= _ORDINAL_WORDS.get(nxt, 0) <= 9:
            out.append(str(_TENS[tok] + _ORDINAL_WORDS[nxt]))
            i += 2
            continue
        if tok in _ORDINAL_WORDS:
            out.append(str(_ORDINAL_WORDS[tok]))
        else:
            out.append(tok)
        i += 1
    return out


def _make_numeric_date(a: int, b: int, year: int) -> date:
    month, day = (b, a) if a > 12 else (a, b)
    return date(year, month, day)


def _absolute(tokens: list[str], today: date) -> date | None:
    # optional leading weekday: "Monday, December 1, 2025"
    if len(tokens) > 1 and tokens[0] in WEEKDAYS:
        tokens = tokens[1:]

    if len(tokens) == 1:
        tok = tokens[0]
        if m := _ISO_RE.match(tok):
            return date(int(m[1]), int(m[2]), int(m[3]))
        if m := _NUM_RE.match(tok):
            year = int(m[3])
            if len(m[3]) == 2:
                year += 2000 if year < 70 else 1900
            return _make_numeric_date(int(m[1]), int(m[2]), year)
        if m := _MD_RE.match(tok):
            return _make_numeric_date(int(m[1]), int(m[2]), today.year)
        return None

    toks = _convert_ordinal_words([t for t in tokens if t != "of"])
    month_tokens = [t for t in toks if t in MONTHS]
    if len(month_tokens) != 1:
        return None
    month = MONTHS[month_tokens[0]]
    found_day: int | None = None
    found_year: int | None = None
    for t in toks:
        if t in MONTHS:
            continue
        if not t.isdigit():
            return None
        if len(t) == 4 and found_year is None:
            found_year = int(t)
        elif len(t) <= 2 and found_day is None:
            found_day = int(t)
        else:
            return None
    if found_day is None:
        return None
    return date(found_year or today.year, month, found_day)


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (n - 1))


def _holiday(tokens: list[str], today: date) -> date | None:
    year = today.year
    if len(tokens) > 1 and tokens[-1].isdigit() and len(tokens[-1]) == 4:
        year = int(tokens[-1])
        tokens = tokens[:-1]
    name = " ".join(tokens)
    if name == "thanksgiving":
        return _nth_weekday(year, 11, 3, 4)
    if name in _HOLIDAYS:
        month, day = _HOLIDAYS[name]
        return date(year, month, day)
    return None
