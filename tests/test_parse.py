from datetime import date

import pytest

from nldate import parse

# Wednesday, November 12, 2025
TODAY = date(2025, 11, 12)


@pytest.mark.parametrize(
    ("s", "expected"),
    [
        # absolute dates
        ("December 1st, 2025", date(2025, 12, 1)),
        ("Dec 1 2025", date(2025, 12, 1)),
        ("1 December 2025", date(2025, 12, 1)),
        ("December 1, 2025", date(2025, 12, 1)),
        ("2025-12-01", date(2025, 12, 1)),
        ("12/1/2025", date(2025, 12, 1)),
        ("DECEMBER 1ST, 2025", date(2025, 12, 1)),
        ("  dec 1, 2025  ", date(2025, 12, 1)),
        ("December 22nd, 2025", date(2025, 12, 22)),
        ("March 3rd, 2026", date(2026, 3, 3)),
        ("February 29, 2024", date(2024, 2, 29)),
        ("December 25", date(2025, 12, 25)),
    ],
)
def test_absolute(s: str, expected: date) -> None:
    assert parse(s, today=TODAY) == expected


@pytest.mark.parametrize(
    ("s", "expected"),
    [
        ("today", date(2025, 11, 12)),
        ("tomorrow", date(2025, 11, 13)),
        ("yesterday", date(2025, 11, 11)),
        ("day after tomorrow", date(2025, 11, 14)),
        ("day before yesterday", date(2025, 11, 10)),
        ("Tomorrow", date(2025, 11, 13)),
    ],
)
def test_simple_relative(s: str, expected: date) -> None:
    assert parse(s, today=TODAY) == expected


@pytest.mark.parametrize(
    ("s", "expected"),
    [
        ("in 3 days", date(2025, 11, 15)),
        ("3 days from now", date(2025, 11, 15)),
        ("3 days ago", date(2025, 11, 9)),
        ("1 day ago", date(2025, 11, 11)),
        ("in 2 weeks", date(2025, 11, 26)),
        ("2 months ago", date(2025, 9, 12)),
        ("a week from today", date(2025, 11, 19)),
        ("in a week", date(2025, 11, 19)),
        ("1 year from now", date(2026, 11, 12)),
        ("three days ago", date(2025, 11, 9)),
    ],
)
def test_offsets(s: str, expected: date) -> None:
    assert parse(s, today=TODAY) == expected


@pytest.mark.parametrize(
    ("s", "expected"),
    [
        ("5 days before December 1st, 2025", date(2025, 11, 26)),
        ("1 year and 2 months after yesterday", date(2027, 1, 11)),
        ("two weeks from tomorrow", date(2025, 11, 27)),
        ("3 days before 2 weeks after tomorrow", date(2025, 11, 24)),
        ("2 weeks and 3 days after today", date(2025, 11, 29)),
    ],
)
def test_anchored(s: str, expected: date) -> None:
    assert parse(s, today=TODAY) == expected


@pytest.mark.parametrize(
    ("s", "expected"),
    [
        ("next Tuesday", date(2025, 11, 18)),
        ("next Tue", date(2025, 11, 18)),
        ("next Monday", date(2025, 11, 17)),
        ("last Friday", date(2025, 11, 7)),
        ("last Fri", date(2025, 11, 7)),
        ("last Monday", date(2025, 11, 10)),
        ("this Friday", date(2025, 11, 14)),
        # today is Wednesday: next/last skip today
        ("next Wednesday", date(2025, 11, 19)),
        ("last Wednesday", date(2025, 11, 5)),
    ],
)
def test_weekdays(s: str, expected: date) -> None:
    assert parse(s, today=TODAY) == expected


@pytest.mark.parametrize(
    ("s", "expected"),
    [
        ("next week", date(2025, 11, 19)),
        ("last week", date(2025, 11, 5)),
        ("next month", date(2025, 12, 12)),
        ("last month", date(2025, 10, 12)),
        ("next year", date(2026, 11, 12)),
        ("last year", date(2024, 11, 12)),
    ],
)
def test_next_last_units(s: str, expected: date) -> None:
    assert parse(s, today=TODAY) == expected


@pytest.mark.parametrize(
    ("s", "expected"),
    [
        ("1 month after January 31st, 2025", date(2025, 2, 28)),
        ("1 month after January 31, 2024", date(2024, 2, 29)),
        ("1 year after February 29, 2024", date(2025, 2, 28)),
        ("2 months after November 15", date(2026, 1, 15)),
        ("1 day after December 31, 2025", date(2026, 1, 1)),
        ("1 day before January 1, 2025", date(2024, 12, 31)),
    ],
)
def test_edge_cases(s: str, expected: date) -> None:
    assert parse(s, today=TODAY) == expected


@pytest.mark.parametrize(
    "s",
    [
        "",
        "   ",
        "banana",
        "February 30, 2025",
        "13/45/2025",
        "5 days before",
        "next",
        "3 days",
    ],
)
def test_invalid_raises(s: str) -> None:
    with pytest.raises(ValueError):
        parse(s, today=TODAY)


def test_default_today() -> None:
    assert parse("today") == date.today()
