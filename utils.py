"""Display helpers: Spanish formatting filters, safe redirects and template context."""

import math
import os
from datetime import datetime, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

from flask import current_app, has_app_context, url_for

# CATEGORY_LABELS is re-exported: domain.py is the single source of truth.
from domain import CATEGORY_LABELS, STATUS_BADGE, STATUS_LABELS

MONTH_NAMES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)

EMPTY_DATE = "—"
DEFAULT_AVATAR_NAMES = (None, "", "default.png")


def categoria_label(value):
    """Return the Spanish label for a stored category key (raw value if unknown)."""
    if value is None or str(value).strip() == "":
        return "Sin categoría"
    return CATEGORY_LABELS.get(value, value)


def estado_label(value):
    """Return the Spanish label for a stored status key (raw value if unknown)."""
    if value is None or str(value).strip() == "":
        return "Sin estado"
    return STATUS_LABELS.get(value, value)


def estado_badge(value):
    """Return the badge CSS class for a status key (neutral if unknown)."""
    suffix = STATUS_BADGE.get(value, "neutral")
    return f"badge-{suffix}"


def _to_float(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(number) or math.isinf(number):
        return 0.0
    return number


def _spanish_separators(formatted):
    # Python renders 1,999.00; swap separators without relying on locale.
    return formatted.replace(",", "\0").replace(".", ",").replace("\0", ".")


def formato_numero(value):
    """Format a count with Spanish thousands separators."""
    number = int(round(_to_float(value)))
    return _spanish_separators(format(number, ","))


def fecha(value):
    """Format a date as '15 de enero de 2026'."""
    if value is None:
        return EMPTY_DATE
    return f"{value.day} de {MONTH_NAMES[value.month - 1]} de {value.year}"


@lru_cache(maxsize=None)
def _load_zone(name):
    if name != "UTC":
        try:
            return ZoneInfo(name)
        except Exception:
            # Unknown zone or missing tz database (e.g. Windows without tzdata).
            pass
    return timezone.utc


def _display_zone():
    name = "UTC"
    if has_app_context():
        name = current_app.config.get("DISPLAY_TIMEZONE") or "UTC"
    return _load_zone(name)


def fecha_hora(value):
    """Format a naive UTC datetime as '15/01/2026 14:30' in DISPLAY_TIMEZONE."""
    if value is None:
        return EMPTY_DATE
    aware = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    return aware.astimezone(_display_zone()).strftime("%d/%m/%Y %H:%M")


def today_local():
    """Return today's date in DISPLAY_TIMEZONE (the DB and the server clock use UTC)."""
    return datetime.now(timezone.utc).astimezone(_display_zone()).date()


def is_safe_redirect_target(target):
    """Accept only same-site relative paths such as '/items/1?page=2'."""
    if not target or not isinstance(target, str):
        return False
    if not target.startswith("/") or target.startswith("//"):
        return False
    if "\\" in target or any(ord(char) < 32 for char in target):
        return False
    return True


def avatar_url(user):
    """Return the avatar URL of a user, or the default SVG when no file exists."""
    filename = getattr(user, "avatar", None)
    default_url = url_for("static", filename="img/avatar-default.svg")
    if filename in DEFAULT_AVATAR_NAMES:
        return default_url
    if os.path.basename(filename) != filename:
        return default_url
    folder = current_app.config["AVATAR_UPLOAD_FOLDER"]
    if os.path.isfile(os.path.join(folder, filename)):
        return url_for("static", filename=f"avatars/{filename}")
    return default_url


def register_template_helpers(app):
    """Register Jinja filters and the shared template context."""
    app.add_template_filter(categoria_label, "categoria_label")
    app.add_template_filter(formato_numero, "formato_numero")
    app.add_template_filter(estado_label, "estado_label")
    app.add_template_filter(estado_badge, "estado_badge")
    app.add_template_filter(fecha, "fecha")
    app.add_template_filter(fecha_hora, "fecha_hora")

    @app.context_processor
    def inject_globals():
        return {
            "current_year": datetime.now(timezone.utc).year,
            "avatar_url": avatar_url,
        }
