from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from utils import (
    CATEGORY_LABELS,
    categoria_label,
    estado_badge,
    estado_label,
    fecha,
    fecha_hora,
    is_safe_redirect_target,
    formato_numero,
    today_local,
)
import domain


class TestCategoriaLabel:
    @pytest.mark.parametrize(
        "key, label",
        [
            ("documents", "Documentos"),
            ("electronics", "Electrónica"),
            ("keys", "Llaves"),
            ("clothing", "Ropa y accesorios"),
            ("bags", "Mochilas y útiles"),
            ("other", "Otros"),
        ],
    )
    def test_known_keys(self, key, label):
        assert categoria_label(key) == label

    def test_mapping_has_all_keys(self):
        assert list(CATEGORY_LABELS) == [
            "documents",
            "electronics",
            "keys",
            "clothing",
            "bags",
            "other",
        ]

    def test_mapping_is_the_domain_mapping(self):
        assert CATEGORY_LABELS is domain.CATEGORY_LABELS

    @pytest.mark.parametrize("legacy", ["general", "office", "consumable"])
    def test_legacy_keys_fall_back_to_raw(self, legacy):
        assert categoria_label(legacy) == legacy

    def test_unknown_value_falls_back_to_raw(self):
        assert categoria_label("Herramientas") == "Herramientas"

    @pytest.mark.parametrize("empty", [None, ""])
    def test_empty_value(self, empty):
        assert categoria_label(empty) == "Sin categoría"


class TestEstado:
    @pytest.mark.parametrize(
        "key, label",
        [("lost", "Perdido"), ("found", "Encontrado"), ("returned", "Entregado")],
    )
    def test_estado_label_known_keys(self, key, label):
        assert estado_label(key) == label

    def test_estado_label_unknown_falls_back_to_raw(self):
        assert estado_label("archived") == "archived"

    @pytest.mark.parametrize("empty", [None, ""])
    def test_estado_label_empty(self, empty):
        assert estado_label(empty) == "Sin estado"

    @pytest.mark.parametrize(
        "key, suffix",
        [("lost", "warning"), ("found", "info"), ("returned", "success")],
    )
    def test_estado_badge_known_keys(self, key, suffix):
        assert estado_badge(key) == f"badge-{suffix}"

    @pytest.mark.parametrize("value", [None, "", "archived"])
    def test_estado_badge_unknown_is_neutral(self, value):
        assert estado_badge(value) == "badge-neutral"

    def test_filters_are_registered_and_render(self, app):
        assert "estado_label" in app.jinja_env.filters
        assert "estado_badge" in app.jinja_env.filters
        with app.test_request_context("/"):
            template = app.jinja_env.from_string(
                "{{ 'found'|estado_label }}|{{ 'found'|estado_badge }}"
            )
            assert template.render() == "Encontrado|badge-info"

    def test_info_badge_style_exists(self):
        css = (Path(__file__).resolve().parent.parent / "static" / "css" / "app.css").read_text(
            encoding="utf-8"
        )
        for status in domain.STATUS_BADGE.values():
            assert f".badge-{status}" in css


class TestFormatoNumero:
    def test_thousands(self):
        assert formato_numero(1234567) == "1.234.567"

    def test_none_and_invalid(self):
        assert formato_numero(None) == "0"
        assert formato_numero("x") == "0"


class TestFechas:
    def test_fecha_spanish_month(self):
        assert fecha(datetime(2026, 1, 15, 14, 30)) == "15 de enero de 2026"

    def test_fecha_all_months(self):
        names = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
            "agosto", "septiembre", "octubre", "noviembre", "diciembre",
        ]
        for index, name in enumerate(names, start=1):
            assert fecha(datetime(2026, index, 1)) == f"1 de {name} de 2026"

    def test_fecha_none(self):
        assert fecha(None) == "—"

    def test_fecha_hora_utc(self):
        assert fecha_hora(datetime(2026, 1, 15, 14, 30)) == "15/01/2026 14:30"

    def test_fecha_hora_none(self):
        assert fecha_hora(None) == "—"

    def test_fecha_hora_invalid_zone_falls_back_to_utc(self, app):
        app.config["DISPLAY_TIMEZONE"] = "Not/AZone"
        with app.test_request_context():
            assert fecha_hora(datetime(2026, 1, 15, 14, 30)) == "15/01/2026 14:30"


class TestTodayLocal:
    def test_returns_a_date_in_the_display_timezone(self, app):
        from datetime import date, timedelta

        with app.test_request_context():
            result = today_local()

        assert type(result) is date
        assert abs((result - datetime.now(timezone.utc).date()).days) <= 1

    def test_follows_the_utc_clock_by_default(self, app, monkeypatch):
        import utils

        class FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 5, 17, 23, 59, tzinfo=tz)

        monkeypatch.setattr(utils, "datetime", FrozenDatetime)
        with app.test_request_context():
            assert today_local() == date(2026, 5, 17)

    def test_works_outside_an_app_context(self):
        assert isinstance(today_local(), date)


class TestIsSafeRedirectTarget:
    @pytest.mark.parametrize(
        "target",
        ["/", "/ok", "/items/1?page=2", "/auth/login"],
    )
    def test_accepts_relative_paths(self, target):
        assert is_safe_redirect_target(target) is True

    @pytest.mark.parametrize(
        "target",
        [
            None,
            "",
            "//evil.com",
            "///evil.com",
            "https://x",
            "http://evil.com/path",
            "\\evil",
            "/\\evil.com",
            "javascript:alert(1)",
            "ok",
            "evil.com",
        ],
    )
    def test_rejects_unsafe_targets(self, target):
        assert is_safe_redirect_target(target) is False
