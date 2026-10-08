"""List filters: free-text search, status, category, month, counts, pagination and /search."""

import re
from datetime import date

import pytest

from models import User


def _text(response):
    return response.get_data(as_text=True)


def _main(html):
    return html.split("<main", 1)[1].split("</main>", 1)[0]


def _body(browser, **params):
    return _main(_text(browser.get("/", query_string=params)))


def _names(body):
    """Names of the cards rendered, in order."""
    return re.findall(r'class="object-card__link"[^>]*>\s*([^<]+?)\s*<', body)


@pytest.fixture
def maria(browser_for):
    return browser_for("maria")


@pytest.fixture
def maria_user(maria):
    return User.query.filter_by(username="maria").first()


@pytest.fixture
def carlos_user(maria, make_user):
    return make_user("carlos", "password123")


# --- free text -----------------------------------------------------------------


def test_text_search_matches_name_description_and_location(maria, maria_user, make_item):
    make_item(maria_user, name="Calculadora", description="científica", location="Aula 4")
    make_item(maria_user, name="Termo", description="metálico con calcomanía", location="Laboratorio")
    make_item(maria_user, name="Gorra", description="roja", location="Calle de la Calculadora")
    make_item(maria_user, name="Paraguas", description="negro", location="Cafetería")

    assert set(_names(_body(maria, q="calc"))) == {"Calculadora", "Termo", "Gorra"}
    assert _names(_body(maria, q="laboratorio")) == ["Termo"]
    assert _names(_body(maria, q="negro")) == ["Paraguas"]


def test_text_search_is_partial_and_case_insensitive(maria, maria_user, make_item):
    make_item(maria_user, name="Tornillo Hexagonal")
    make_item(maria_user, name="Martillo")

    for q in ("tornillo", "TORNILLO", "nillo", "Hexa", "gonal"):
        assert _names(_body(maria, q=q)) == ["Tornillo Hexagonal"], q


def test_text_search_folds_case_of_accented_letters_but_not_accents(maria, maria_user, make_item):
    make_item(maria_user, name="Árbol de Navidad")
    make_item(maria_user, name="CAÑERÍA de cobre")

    assert _names(_body(maria, q="árbol")) == ["Árbol de Navidad"]
    assert _names(_body(maria, q="ÁRBOL")) == ["Árbol de Navidad"]
    assert _names(_body(maria, q="cañería")) == ["CAÑERÍA de cobre"]
    assert _names(_body(maria, q="arbol")) == []


@pytest.mark.parametrize("q", ["", "   ", "\t"])
def test_blank_query_lists_everything(maria, maria_user, make_item, q):
    make_item(maria_user, name="Uno")
    make_item(maria_user, name="Dos")

    assert len(_names(_body(maria, q=q))) == 2


def test_search_keeps_the_stripped_query_in_the_input(maria, maria_user, make_item):
    make_item(maria_user, name="Tornillo")

    body = _body(maria, q="  tornillo  ")

    assert re.search(r'<input[^>]*name="q"[^>]*value="tornillo"|<input[^>]*value="tornillo"[^>]*name="q"', body)


@pytest.mark.parametrize(
    "q, expected, excluded",
    [
        ("%", ["100% algodón"], ["Cable_A", "CableXA", "Tela"]),
        ("100%", ["100% algodón"], ["Tela"]),
        ("_", ["Cable_A"], ["100% algodón", "CableXA", "Tela"]),
        ("Cable_A", ["Cable_A"], ["CableXA"]),
        ("\\", ["Ruta C:\\datos"], ["Cable_A", "100% algodón"]),
    ],
)
def test_wildcards_in_the_query_are_literal_characters(maria, maria_user, make_item, q, expected, excluded):
    for name in ("100% algodón", "Cable_A", "CableXA", "Tela", "Ruta C:\\datos"):
        make_item(maria_user, name=name)

    names = _names(_body(maria, q=q))

    for name in expected:
        assert name.replace("&", "&amp;") in names, (q, name)
    for name in excluded:
        assert name not in names, (q, name)


def test_percent_alone_does_not_list_everything(maria, maria_user, make_item):
    make_item(maria_user, name="Uno")
    make_item(maria_user, name="Dos")

    body = _body(maria, q="%")

    assert "No se encontraron objetos con los filtros aplicados." in body


def test_query_is_escaped_wherever_it_is_rendered(maria):
    body = _body(maria, q="<script>alert(1)</script>")

    assert "<script>alert(1)</script>" not in body
    assert "&lt;script&gt;" in body


def test_search_covers_the_reports_of_every_user(maria, maria_user, carlos_user, make_item):
    make_item(maria_user, name="Tornillo de maria")
    make_item(carlos_user, name="Tornillo de carlos")

    assert set(_names(_body(maria, q="tornillo"))) == {"Tornillo de maria", "Tornillo de carlos"}


# --- status, category, month -----------------------------------------------------


def test_status_filter_keeps_only_that_status_and_ignores_unknown_values(maria, maria_user, make_item):
    make_item(maria_user, name="Perdido uno", status="lost")
    make_item(maria_user, name="Hallado uno", status="found")
    make_item(maria_user, name="Entregado uno", status="returned")

    assert _names(_body(maria, estado="lost")) == ["Perdido uno"]
    assert _names(_body(maria, estado="found")) == ["Hallado uno"]
    assert _names(_body(maria, estado="returned")) == ["Entregado uno"]
    assert len(_names(_body(maria, estado="archived"))) == 3
    assert len(_names(_body(maria, estado=""))) == 3


def test_category_filter_accepts_keys_and_stored_legacy_values_and_ignores_others(
    maria, maria_user, make_item
):
    make_item(maria_user, name="Llavero", category="keys")
    make_item(maria_user, name="Cargador", category="electronics")
    make_item(maria_user, name="Martillo", category="Herramientas")
    make_item(maria_user, name="Sin categoría", category=None)

    assert _names(_body(maria, categoria="keys")) == ["Llavero"]
    assert _names(_body(maria, categoria="Herramientas")) == ["Martillo"]
    assert len(_names(_body(maria, categoria="inexistente"))) == 4


def test_category_select_lists_new_categories_and_stored_legacy_values(maria, maria_user, make_item):
    make_item(maria_user, name="Martillo", category="Herramientas")
    make_item(maria_user, name="Cable", category="general")

    body = _body(maria)
    select = re.search(r'<select[^>]*name="categoria".*?</select>', body, re.DOTALL).group(0)

    assert "Todas las categorías" in select
    for label in ("Documentos", "Electrónica", "Llaves", "Ropa y accesorios", "Mochilas y útiles", "Otros"):
        assert label in select, label
    assert 'value="Herramientas"' in select
    assert 'value="general"' in select


def test_category_select_marks_the_selected_value(maria, maria_user, make_item):
    make_item(maria_user, name="Llavero", category="keys")

    body = _body(maria, categoria="keys")

    assert re.search(r'<option[^>]*value="keys"[^>]*selected|<option[^>]*selected[^>]*value="keys"', body)


def test_month_filter_uses_the_event_date_with_exclusive_upper_bound(maria, maria_user, make_item):
    make_item(maria_user, name="Fin de noviembre", event_date=date(2026, 11, 30))
    make_item(maria_user, name="Inicio de diciembre", event_date=date(2026, 12, 1))
    make_item(maria_user, name="Fin de diciembre", event_date=date(2026, 12, 31))
    make_item(maria_user, name="Inicio de enero", event_date=date(2027, 1, 1))
    make_item(maria_user, name="Sin fecha", event_date=None)

    assert set(_names(_body(maria, mes="2026-12"))) == {"Inicio de diciembre", "Fin de diciembre"}
    assert _names(_body(maria, mes="2027-01")) == ["Inicio de enero"]


@pytest.mark.parametrize("mes", ["2026-13", "2026-00", "abril", "2026-1", "0000-01", "2026-04-01", ""])
def test_invalid_month_is_ignored(maria, maria_user, make_item, mes):
    make_item(maria_user, name="Uno", event_date=date(2026, 3, 1))
    make_item(maria_user, name="Dos", event_date=date(2026, 4, 1))

    assert len(_names(_body(maria, mes=mes))) == 2


def test_filters_combine(maria, maria_user, make_item):
    make_item(maria_user, name="Llaves rojas", category="keys", status="lost", event_date=date(2026, 3, 2))
    make_item(maria_user, name="Llaves azules", category="keys", status="found", event_date=date(2026, 3, 3))
    make_item(maria_user, name="Llaves verdes", category="keys", status="lost", event_date=date(2026, 4, 3))
    make_item(maria_user, name="Cartera roja", category="bags", status="lost", event_date=date(2026, 3, 2))

    assert _names(_body(maria, q="llaves", estado="lost", categoria="keys", mes="2026-03")) == ["Llaves rojas"]


# --- chips and counts -------------------------------------------------------------


def _chip_counts(body):
    chips = re.findall(r'<a[^>]*class="chip[^"]*"[^>]*>(.*?)</a>', body, re.DOTALL)
    result = {}
    for chip in chips:
        text = re.sub(r"<[^>]+>", " ", chip)
        match = re.match(r"\s*([A-Za-zñé]+)\s+(\d+)\s*$", text)
        assert match, text
        result[match.group(1)] = int(match.group(2))
    return result


def test_status_chips_show_counts_for_the_other_filters(maria, maria_user, make_item):
    make_item(maria_user, name="Llaves A", category="keys", status="lost", event_date=date(2026, 3, 2))
    make_item(maria_user, name="Llaves B", category="keys", status="lost", event_date=date(2026, 3, 9))
    make_item(maria_user, name="Llaves C", category="keys", status="found", event_date=date(2026, 3, 9))
    make_item(maria_user, name="Llaves D", category="keys", status="returned", event_date=date(2026, 4, 1))
    make_item(maria_user, name="Gorra", category="clothing", status="found", event_date=date(2026, 3, 9))

    assert _chip_counts(_body(maria)) == {"Todos": 5, "Perdidos": 2, "Encontrados": 2, "Entregados": 1}
    assert _chip_counts(_body(maria, categoria="keys")) == {"Todos": 4, "Perdidos": 2, "Encontrados": 1, "Entregados": 1}
    assert _chip_counts(_body(maria, categoria="keys", mes="2026-03")) == {"Todos": 3, "Perdidos": 2, "Encontrados": 1, "Entregados": 0}
    # The active status does not change the counts: they describe the other filters only.
    assert _chip_counts(_body(maria, categoria="keys", mes="2026-03", estado="found")) == {"Todos": 3, "Perdidos": 2, "Encontrados": 1, "Entregados": 0}
    assert _chip_counts(_body(maria, q="llaves a")) == {"Todos": 1, "Perdidos": 1, "Encontrados": 0, "Entregados": 0}


def test_active_chip_is_highlighted_with_aria_current(maria, maria_user, make_item):
    make_item(maria_user, name="Uno", status="found")

    body = _body(maria, estado="found")

    active = re.findall(r'<a[^>]*class="chip is-active"[^>]*>', body)
    assert len(active) == 1
    assert 'aria-current="true"' in active[0]
    assert "estado=found" in active[0]
    all_chip = re.search(r'<a[^>]*class="chip"[^>]*>\s*Todos', body)
    assert all_chip is not None and "aria-current" not in all_chip.group(0)


def test_todos_chip_is_active_without_status_filter(maria, maria_user, make_item):
    make_item(maria_user, name="Uno")

    body = _body(maria)

    assert re.search(r'<a[^>]*class="chip is-active"[^>]*>\s*Todos', body)


def test_chip_links_keep_the_other_filters(maria, maria_user, make_item):
    make_item(maria_user, name="Uno", category="keys", event_date=date(2026, 3, 1))

    body = _body(maria, q="uno", categoria="keys", mes="2026-03")
    chip = re.search(r'<a[^>]*class="chip"[^>]*href="([^"]+)"[^>]*>\s*Perdidos', body).group(1)

    for part in ("q=uno", "categoria=keys", "mes=2026-03", "estado=lost"):
        assert part in chip, part


def test_status_chip_lists_the_reports_of_every_user(maria, maria_user, carlos_user, make_item):
    make_item(maria_user, name="De maria", status="found")
    make_item(carlos_user, name="De carlos", status="found")

    assert set(_names(_body(maria, estado="found"))) == {"De maria", "De carlos"}


# --- states -------------------------------------------------------------------------


def test_no_results_state_offers_to_clear_the_filters(maria, maria_user, make_item):
    make_item(maria_user, name="Tornillo")

    body = _body(maria, q="zzz")

    assert "No se encontraron objetos con los filtros aplicados." in body
    assert "Aún no hay reportes registrados." not in body
    assert re.search(r'<a[^>]*href="/"[^>]*>\s*Limpiar filtros', body)
    assert 'class="gallery' not in body
    assert 'class="filter-bar' in body


def test_filter_bar_values_are_kept(maria, maria_user, make_item):
    make_item(maria_user, name="Uno", event_date=date(2026, 3, 1))

    body = _body(maria, q="uno", mes="2026-03")

    assert re.search(r'<input[^>]*name="mes"[^>]*value="2026-03"|<input[^>]*value="2026-03"[^>]*name="mes"', body)


def test_applying_the_filter_form_keeps_the_active_status(maria, maria_user, make_item):
    make_item(maria_user, name="Uno", status="found")

    body = _body(maria, estado="found")

    assert re.search(r'<input[^>]*type="hidden"[^>]*name="estado"[^>]*value="found"|<input[^>]*name="estado"[^>]*type="hidden"[^>]*value="found"', body)


def test_subtitle_counts_filtered_results(maria, maria_user, make_item):
    for number in range(3):
        make_item(maria_user, name=f"Cable {number}")
    make_item(maria_user, name="Otro")

    assert "3 reportes" in _body(maria, q="cable")
    assert "1 reporte" in _body(maria, q="otro")


# --- pagination ---------------------------------------------------------------------


def test_pagination_links_keep_every_filter(maria, maria_user, make_item):
    for number in range(13):
        make_item(maria_user, name=f"Llaves {number:02d}", category="keys", status="found", event_date=date(2026, 3, 1))
    make_item(maria_user, name="Gorra", category="clothing")

    first = _body(maria, q="llaves", estado="found", categoria="keys", mes="2026-03")
    second = _body(maria, q="llaves", estado="found", categoria="keys", mes="2026-03", page=2)

    link = re.search(r'<a[^>]*href="([^"]+)"[^>]*rel="next"', first).group(1)
    for part in ("page=2", "q=llaves", "estado=found", "categoria=keys", "mes=2026-03"):
        assert part in link, part
    assert "13 resultados" in first
    assert len(_names(first)) == 12 and len(_names(second)) == 1
    assert "Página 2 de 2" in second
    assert "Gorra" not in first + second
    prev = re.search(r'<a[^>]*href="([^"]+)"[^>]*rel="prev"', second).group(1)
    assert "q=llaves" in prev and "mes=2026-03" in prev


def test_pagination_links_encode_special_characters_in_the_query(maria, maria_user, make_item):
    for number in range(13):
        make_item(maria_user, name=f"50% {number}")

    assert "q=50%25" in _body(maria, q="50%")


def test_page_beyond_the_last_redirects_to_the_last_page_keeping_filters(maria, maria_user, make_item):
    for number in range(13):
        make_item(maria_user, name=f"Tuerca {number}", status="found")

    response = maria.get("/", query_string={"q": "tuerca", "estado": "found", "page": 9})

    assert response.status_code == 302
    location = response.headers["Location"]
    assert "page=2" in location and "q=tuerca" in location and "estado=found" in location


def test_invalid_page_numbers_fall_back_to_the_first_page(maria, maria_user, make_item):
    make_item(maria_user, name="Tuerca")

    for page in ("abc", "0", "-2"):
        response = maria.get("/", query_string={"q": "tuerca", "page": page})
        assert response.status_code == 200
        assert "Tuerca" in _text(response)


# --- /search redirect ---------------------------------------------------------------


def test_search_route_redirects_to_the_list_preserving_the_query_string(maria):
    response = maria.get("/search?q=llaves&estado=found&mes=2026-03")

    assert response.status_code in (301, 302, 308)
    location = response.headers["Location"]
    assert location.split("?", 1)[0].endswith("/")
    assert not location.split("?", 1)[0].endswith("/search")
    for part in ("q=llaves", "estado=found", "mes=2026-03"):
        assert part in location


def test_search_route_without_a_query_redirects_to_the_plain_list(maria):
    response = maria.get("/search")

    assert response.status_code in (301, 302, 308)
    assert response.headers["Location"].endswith("/")


def test_search_route_followed_shows_the_filtered_list(maria, maria_user, make_item):
    make_item(maria_user, name="Calculadora")
    make_item(maria_user, name="Paraguas")

    response = maria.get("/search?q=calc", follow_redirects=True)

    assert response.request.path == "/"
    assert _names(_main(_text(response))) == ["Calculadora"]


def test_search_template_is_gone():
    import os

    from config import BASE_DIR

    assert not os.path.exists(os.path.join(BASE_DIR, "templates", "search.html"))
    assert not os.path.exists(os.path.join(BASE_DIR, "templates", "_items_table.html"))
    assert os.path.exists(os.path.join(BASE_DIR, "templates", "_items_grid.html"))
