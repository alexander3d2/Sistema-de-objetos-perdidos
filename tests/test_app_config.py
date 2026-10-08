import ast
import os

from app import create_app, debug_enabled
from config import BASE_DIR, Config
from extensions import csrf, db, login_manager


def _db_stat():
    path = os.path.join(BASE_DIR, "inventory.db")
    if not os.path.exists(path):
        return None
    stat = os.stat(path)
    return stat.st_size, stat.st_mtime_ns


def test_app_py_has_single_create_app_and_main_block():
    with open(os.path.join(BASE_DIR, "app.py"), encoding="utf-8") as handle:
        tree = ast.parse(handle.read())

    create_app_defs = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "create_app"
    ]
    main_blocks = [
        node
        for node in tree.body
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and getattr(node.test.left, "id", None) == "__name__"
    ]
    assert len(create_app_defs) == 1
    assert len(main_blocks) == 1


def test_tests_use_in_memory_database(app):
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"
    assert db.engine.url.drivername == "sqlite"
    assert db.engine.url.database == ":memory:"
    assert app.config["WTF_CSRF_ENABLED"] is False
    assert app.config["TESTING"] is True


def test_real_database_file_is_untouched(client):
    before = _db_stat()
    client.get("/auth/login")
    client.get("/does-not-exist")
    assert _db_stat() == before


def test_create_app_with_test_config_does_not_create_db_file(tmp_path, monkeypatch):
    missing = tmp_path / "never-created.db"
    monkeypatch.setattr(Config, "DATABASE_PATH", str(missing))
    create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "test",
        }
    )
    assert not missing.exists()


def test_blueprints_registered(app):
    assert {"main", "auth", "dashboard", "profile"} <= set(app.blueprints)
    assert "api" not in app.blueprints
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/auth/login" in rules
    assert "/dashboard/" in rules
    assert any(rule.startswith("/profile") for rule in rules)


def test_config_defaults():
    assert not hasattr(Config, "CURRENCY_SYMBOL")
    assert not hasattr(Config, "LOW_STOCK_THRESHOLD")
    assert Config.MAX_CONTENT_LENGTH == 5 * 1024 * 1024
    assert Config.ITEMS_PER_PAGE == 12
    assert Config.DISPLAY_TIMEZONE == os.environ.get("DISPLAY_TIMEZONE", "UTC")
    assert os.path.isabs(Config.ITEM_UPLOAD_FOLDER)
    assert os.path.isabs(Config.AVATAR_UPLOAD_FOLDER)
    assert Config.ITEM_UPLOAD_FOLDER == os.path.join(BASE_DIR, "static", "uploads")
    assert Config.AVATAR_UPLOAD_FOLDER == os.path.join(BASE_DIR, "static", "avatars")


def test_debug_is_off_by_default(monkeypatch):
    monkeypatch.delenv("FLASK_DEBUG", raising=False)
    assert debug_enabled() is False


def test_debug_requires_explicit_flag(monkeypatch):
    monkeypatch.setenv("FLASK_DEBUG", "0")
    assert debug_enabled() is False
    monkeypatch.setenv("FLASK_DEBUG", "1")
    assert debug_enabled() is True


def test_csrf_extension_is_initialised(app):
    assert "csrf" in app.extensions
    assert csrf is not None


def test_login_message_is_spanish():
    assert login_manager.login_message == "Inicie sesión para acceder a esta página."
    assert login_manager.login_message_category == "warning"
    assert login_manager.login_view == "auth.login"


def test_unknown_url_renders_404_page(client):
    response = client.get("/this-url-does-not-exist")
    assert response.status_code == 404
    assert "Página no encontrada".encode() in response.data
    assert b'<html lang="es"' in response.data


def test_app_py_has_no_inline_error_page_fallback():
    with open(os.path.join(BASE_DIR, "app.py"), encoding="utf-8") as handle:
        source = handle.read()
    assert "_FALLBACK_ERROR_PAGES" not in source
    assert "TemplateNotFound" not in source


def test_server_error_renders_500_page_and_rolls_back(app, monkeypatch):
    @app.route("/boom")
    def boom():
        raise RuntimeError("boom")

    calls = []
    monkeypatch.setattr(db.session, "rollback", lambda: calls.append("rollback"))
    app.config["PROPAGATE_EXCEPTIONS"] = False
    client = app.test_client()
    response = client.get("/boom")
    assert response.status_code == 500
    assert "Error del servidor".encode() in response.data
    assert calls == ["rollback"]


def test_template_helpers_exposed_in_context(app):
    with app.test_request_context("/"):
        app.update_template_context(context := {})
        assert "currency_symbol" not in context
        assert "low_stock_threshold" not in context
        assert isinstance(context["current_year"], int)
        assert callable(context["avatar_url"])


def test_jinja_filters_registered(app):
    assert "moneda" not in app.jinja_env.filters
    assert "numero" not in app.jinja_env.filters
    for name in ("categoria_label", "formato_numero", "fecha", "fecha_hora"):
        assert name in app.jinja_env.filters


def test_avatar_url_falls_back_to_default_svg(app):
    with app.test_request_context("/"):
        context = {}
        app.update_template_context(context)

        class Anonymous:
            avatar = None

        class Missing:
            avatar = "no-such-file.png"

        class Default:
            avatar = "default.png"

        for user in (None, Anonymous(), Missing(), Default()):
            assert context["avatar_url"](user).endswith("img/avatar-default.svg")


def test_avatar_url_uses_existing_file(app, tmp_path):
    app.config["AVATAR_UPLOAD_FOLDER"] = str(tmp_path)
    (tmp_path / "1_123.png").write_bytes(b"png")

    class Owner:
        avatar = "1_123.png"

    with app.test_request_context("/"):
        context = {}
        app.update_template_context(context)
        assert context["avatar_url"](Owner()).endswith("avatars/1_123.png")


def test_pytz_global_is_not_exposed_to_templates(app):
    assert "pytz" not in app.jinja_env.globals
