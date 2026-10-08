from datetime import date

import pytest

import domain


def test_status_labels_are_ordered_and_spanish():
    assert list(domain.STATUS_LABELS.items()) == [
        ("lost", "Perdido"),
        ("found", "Encontrado"),
        ("returned", "Entregado"),
    ]


def test_status_choices_follow_label_order():
    assert domain.STATUS_CHOICES == [
        ("lost", "Perdido"),
        ("found", "Encontrado"),
        ("returned", "Entregado"),
    ]
    assert domain.DEFAULT_STATUS == "lost"


def test_status_badge_covers_every_status():
    assert domain.STATUS_BADGE == {
        "lost": "warning",
        "found": "info",
        "returned": "success",
    }
    assert set(domain.STATUS_BADGE) == set(domain.STATUS_LABELS)


def test_category_labels_are_ordered_and_spanish():
    assert list(domain.CATEGORY_LABELS.items()) == [
        ("documents", "Documentos"),
        ("electronics", "Electrónica"),
        ("keys", "Llaves"),
        ("clothing", "Ropa y accesorios"),
        ("bags", "Mochilas y útiles"),
        ("other", "Otros"),
    ]


def test_legacy_category_map_only_keeps_electronics():
    assert domain.LEGACY_CATEGORY_MAP["electronics"] == "electronics"
    for legacy in ("general", "office", "consumable", "other"):
        assert domain.LEGACY_CATEGORY_MAP[legacy] == "other"


@pytest.mark.parametrize(
    ("stored", "expected"),
    [
        ("general", "other"),
        ("office", "other"),
        ("consumable", "other"),
        ("other", "other"),
        ("electronics", "electronics"),
        ("Electronics", "electronics"),
        ("  OFFICE ", "other"),
        ("Herramientas", "other"),
        ("documents", "documents"),
        ("keys", "keys"),
        ("clothing", "clothing"),
        ("bags", "bags"),
    ],
)
def test_normalize_legacy_category(stored, expected):
    assert domain.normalize_legacy_category(stored) == expected


@pytest.mark.parametrize("empty", [None, "", "   "])
def test_normalize_legacy_category_keeps_missing_values_missing(empty):
    assert domain.normalize_legacy_category(empty) is None


def test_month_bounds_regular_month():
    assert domain.month_bounds(2026, 5) == (date(2026, 5, 1), date(2026, 6, 1))


def test_month_bounds_february_in_leap_and_common_years():
    assert domain.month_bounds(2024, 2) == (date(2024, 2, 1), date(2024, 3, 1))
    assert domain.month_bounds(2026, 2) == (date(2026, 2, 1), date(2026, 3, 1))


def test_month_bounds_december_rolls_over_to_january():
    assert domain.month_bounds(2026, 12) == (date(2026, 12, 1), date(2027, 1, 1))


@pytest.mark.parametrize("month", [0, 13, -1])
def test_month_bounds_rejects_invalid_months(month):
    with pytest.raises(ValueError):
        domain.month_bounds(2026, month)


DEFAULT = (2026, 10)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026-05", (2026, 5)),
        ("2026-12", (2026, 12)),
        ("2024-02", (2024, 2)),
        ("  2026-05  ", (2026, 5)),
    ],
)
def test_parse_month_accepts_strict_year_month(raw, expected):
    assert domain.parse_month(raw, DEFAULT) == expected


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        "   ",
        "2026-13",
        "2026-00",
        "2026-1",
        "26-05",
        "2026/05",
        "2026-05-01",
        "2026-5a",
        "abcd-ef",
        "0000-05",
        "２０２６-０５",
        "2026-05\n2027-01",
    ],
)
def test_parse_month_returns_default_for_invalid_values(raw):
    assert domain.parse_month(raw, DEFAULT) is DEFAULT


def test_parse_month_returns_the_default_object_untouched():
    sentinel = object()
    assert domain.parse_month("nope", sentinel) is sentinel
