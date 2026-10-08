# Feature: ui-espanol-formal

Branch: `feat/ui-espanol-formal` (from `main`)
Engram mirror topic: `odd/ui-espanol-formal/tasks` (project `inventory-management-flask`)
Delivery strategy: LOCAL ONLY. User decision ("vamos a tenerlo local nomas"): NO commits, NO push, NO PR, NO merge. The user declined the first commit attempt. All work stays as uncommitted changes in the working tree of the local branch. This document stays untracked/local. Task "Commit:" lines below are intentionally NOT executed; they are suggested messages for when the user decides to commit. Native review is not applicable (no candidate commit).
TDD runner: `.venv\Scripts\python.exe -m pytest -q` (only AFTER T1 isolates the DB, see constraints)

## Objective
Rebuild the whole user interface with a formal, consistent design, translate everything the user sees to Spanish, and fix what is broken in the UI layer. Authorized scope chosen by the user: "Interfaz + corregir lo roto".

## Problem (evidence from analysis, all verified by reading code)
- Inconsistent visual design: same action uses different colors (blue vs green submit), emojis in titles/flash, mixed card/input sizes, plain-text duplicated pagination, no empty state in the item list. Tailwind via unpinned Play CDN, no config; `static/css/style.css` is not linked (dead).
- English everywhere: `<html lang="en">`, 14 templates, `forms.py`, 24 `flash()` calls, 404/500, README.
- Broken: `/dashboard` (main) vs `/dashboard/` (blueprint) both render `dashboard.html` with different context vars; `view.html:69` delete is a GET link to a POST-only route (405); `static/avatars/default.png` missing; `base.html` JS null error for anonymous users; 404/500 never rendered (no errorhandler); `{% block title %}` never rendered; form errors never displayed; CSV import/export not linked from the UI; `current_year` never passed; low-stock threshold inconsistent (`dashboard.py:24` `<5`, `main.py:60` config default 5 with `<`, `view.html:45` `<=5`).
- Security/robustness in UI-layer routes: no `CSRFProtect`; logout via GET; open redirect on `next` (`auth.py:33-34`); profile edit / change password use raw `request.form` with no validation (`profile.py:74-75,112-127`); avatar upload without extension check/rename; `UPLOAD_FOLDER = "static/avatars"` relative; edit deletes old image before validating new one (`main.py:138-150`); no `MAX_CONTENT_LENGTH`.
- `app.py` has two concatenated `create_app` definitions and two `__main__` blocks; `tests/conftest.py` uses the real `inventory.db` and calls `drop_all()` (DESTROYS local data). A backup exists at `C:\Users\alexa\AppData\Local\Temp\opencode\inv-backup\inventory.db.bak`.

## Out of scope (do NOT touch)
- `api.py` (dead code, stays as is, stays unregistered).
- Data model columns and DB schema (no migrations). `models.py` may only get non-schema changes if strictly needed.
- Category stored keys (`general`, `electronics`, `office`, `consumable`, `other`) and CSV header names (`name, description, quantity, price, category`; export extra: `id, image_filename, created_at`): these are data contracts, keep them in English; only display labels are Spanish.
- Flash categories (`success`, `danger`, `warning`, `info`) are logic, not text: keep.
- `requirements.txt` has an unrelated uncommitted user change: NEVER stage or edit it.
- Do not untrack or delete `static/uploads/*` or `static/avatars/*`. Do not touch `inventory.db`, `.venv`.
- Do not push, open PRs, or merge.

## Design decisions (made by the orchestrator; do not ask again)
- Look: formal, sober, institutional. Palette: slate/neutral grays + ONE primary color (deep blue, `#1e3a8a`/blue-900 family) used for every primary action; red only for destructive actions; amber/green/red only as semantic status (low stock, success, error). No emojis anywhere in UI or flash messages. No colorful per-action buttons (no yellow Edit / green Add).
- Typography: keep Inter. Title case is NOT used in Spanish: sentence case ("Agregar artículo", not "Agregar Artículo").
- Tailwind: keep Play CDN but pin the version (`https://cdn.tailwindcss.com/3.4.17`) and declare an inline `tailwind.config` with the palette (named primary shades) in `base.html`. Pin Bootstrap Icons `1.11.3`, Chart.js `4.4.7`. Do not add npm/build tooling.
- Put shared component classes in a NEW linked `static/css/app.css` (buttons `.btn .btn-primary .btn-secondary .btn-danger`, `.card`, `.form-input`, `.form-label`, `.badge`, `.table`, etc.) and DELETE the dead `static/css/style.css`. Keep inline Tailwind utilities for layout.
- Reusable Jinja macros in `templates/_macros.html` (field renderer showing label + input + `errors`, pagination, flash list, page header, empty state, confirm-delete form). All form pages must render WTForms errors.
- Language: `<html lang="es">`. Terminology: Inventario, Artículo(s), Buscar, Panel (Dashboard), Agregar artículo, Editar artículo, Eliminar, Ver detalle, Perfil, Cambiar contraseña, Cerrar sesión, Iniciar sesión, Registrarse, Importar CSV, Exportar CSV, Stock bajo, Cantidad, Precio, Categoría, Descripción, Acciones. Neutral/professional Spanish, `usted`-free impersonal style (e.g. "Ingrese su usuario"), no regional slang.
- Category display labels: general=General, electronics=Electrónica, office=Oficina, consumable=Consumible, other=Otro. Implement as a single mapping (e.g. `CATEGORY_LABELS` in `forms.py` or `utils.py`) + a Jinja filter `categoria_label` that falls back to the raw value for unknown keys (CSV may import any text). Use it in index/view/search/dashboard.
- Currency: keep `$`, but read it from `config.py` `CURRENCY_SYMBOL = "$"` and expose via context processor (no hardcoded `$` in templates). Number format: Spanish style via a Jinja filter `moneda` (thousands `.`/space-free, decimals `,`: `1.999,00`) implemented without locale dependencies (string replace of Python format output).
- Dates: Jinja filter `fecha` produces Spanish month names with a manual month-name table (`15 de enero de 2026`, and `fecha_hora` with 24h `15/01/2026 14:30`). No `locale.setlocale`.
- Timezone: replace hardcoded `Asia/Karachi` with `DISPLAY_TIMEZONE` in `config.py` (default `"UTC"`), used by a `fecha_hora` filter (DB stores naive UTC). Remove `pytz` usage from templates.
- Low stock: single source of truth `LOW_STOCK_THRESHOLD = 5` in `config.py`, rule `quantity <= threshold` everywhere (index, view, dashboard, search), exposed via context processor.
- Context processor provides: `current_year`, `currency_symbol`, `low_stock_threshold`, `avatar_url(user)` helper (falls back to a NEW static asset `static/img/avatar-default.svg` when the file is missing/default).
- Dashboard: ONE route. Remove the duplicate: keep the `dashboard` blueprint (`dashboard.home`) at `/dashboard/` as the single implementation, make `/dashboard` redirect (308/301) to it, remove `main.dashboard` route. Context vars must match the template exactly (`total_items`, `total_value`, `low_stock`, `latest_items`). Chart: show something meaningful with the data available (e.g. value by category as bar chart with the primary-palette colors) computed server-side from the user's items; empty state when no items.
- Navbar: Inventario, Buscar, Panel, Importar/Exportar CSV (reachable from the UI), "Agregar artículo" as a primary button, user menu with Perfil, Cambiar contraseña, Cerrar sesión. Logout must be POST with CSRF (form button), route `methods=["POST"]`.
- Error pages `404.html` and `500.html` in Spanish, registered via `app.register_error_handler`. Page `<title>` must work: `base.html` declares `{% block title %}` and renders `{% block title %}{% endblock %} · Inventario`-style.
- Security fixes in scope: `CSRFProtect(app)` in `extensions.py`/`app.py` with `csrf_token()` in EVERY POST form (including delete, logout, avatar, profile edit, change password, CSV import); safe redirect for `next` (only relative same-host paths, use `urlparse`, reject `//` and absolute URLs); `MAX_CONTENT_LENGTH = 5 * 1024 * 1024`; upload folders resolved from `app.root_path`/`app.static_folder` (absolute), not relative; avatar upload validated by extension allow-list (png, jpg, jpeg, gif, webp) + renamed to `<user_id>_<timestamp>.<ext>` (no collisions between users) and old custom avatar removed if it was the user's own; profile edit and change password use WTForms (`EditProfileForm` without `phone`/`location`, `ChangePasswordForm`) with validators (username 3–64, email valid, bio ≤ 300, new password ≥ 6, confirm EqualTo, current password check); edit item: validate form AND new image BEFORE deleting old image; replace bare `except:`; default `debug` off (use `FLASK_DEBUG` env or `app.run(debug=os.environ.get("FLASK_DEBUG")=="1")`); `SECRET_KEY` from env `SECRET_KEY` with a clearly-marked dev fallback.
- Exactly ONE `create_app(test_config=None)` in `app.py` and ONE `__main__` block. Test config overrides `SQLALCHEMY_DATABASE_URI` to `sqlite:///:memory:` (or tmp file), `WTF_CSRF_ENABLED=False`, `TESTING=True`. `db.create_all()` must run for non-test config only when needed as today (keep the existing "create if DB file missing" behavior for dev; tests do their own create_all on the in-memory DB).
- Forms: ONE `AddItemForm` (restore full validation: `DataRequired`, `Length(max=120)` on name, description `Length(max=500)`, quantity `NumberRange(0, 100000)`, price `NumberRange(0, 1000000)`, category choices, image `FileAllowed`), `EditItemForm` inherits. All labels/messages Spanish. Remove manual "too large" checks in `main.py` that become redundant only if the form enforces them. Remove unused/duplicate form classes only if unused by any route after changes (keep `AvatarUploadForm` if used).
- Flash messages: Spanish, no emojis, e.g. "Artículo agregado correctamente.", "Usuario o contraseña incorrectos.".
- Flask-Login: `login_manager.login_message = "Inicie sesión para acceder a esta página."` (+ keep `login_message_category = "warning"`).
- Tests: rewrite in Spanish naming/comments? NO: test code, names and comments stay English (code artifact rule), but assertions check Spanish UI text. Tests must be meaningful (no vacuous passes): real login flow with CSRF disabled in test config, register, logout (POST), item CRUD, authorization (user B cannot view/edit/delete user A's item), search scoping, CSV export/import contract (English headers), dashboard single route + redirect, 404 page, open-redirect rejection, avatar validation, profile/password validation, low-stock rule, Spanish filters (`moneda`, `fecha`, `categoria_label`). Remove the roman-urdu comments.
- README: translate fully to Spanish, fix wrong `cd` folder name (`inventory-management-flask`), document env vars (`SECRET_KEY`, `FLASK_DEBUG`), CSV contract, running tests, remove "Made with ❤️ in Pakistan"-style lines only if factually the user's repo is a fork? NO: keep author/license credit as in the original (MIT, Rumaisa Islam) — only translate. Screenshots in `screenshots/` are outdated: leave files, add a note in the README that they show the previous interface.

## Constraints for every writer
- ~400 authored changed lines per task is a planning heuristic only, not a cap; do not split artificially nor minify.
- Never run `pytest` before T1 is committed-ready (conftest isolated). If you must run anything touching the app before that, make sure it cannot use `inventory.db`.
- Do NOT run `git add`, `git commit`, `git push`, `git stash`, `git checkout`, `git reset` or any git command that mutates state. Read-only git (`status`, `diff`, `log`) is fine. Never edit `requirements.txt`.
- Leave the working tree with your changes uncommitted; list the exact files you created/modified/deleted in your report.
- Code identifiers, comments, tests, config and docs-as-code in English; only user-visible text and README in Spanish.
- Persona/voice rules do not leak into artifacts.

## Tasks (each closes with a work-unit commit; route per task recorded below)
- [x] T1 (DONE, uncommitted by user decision) Backend foundation: single `create_app`, config (env, CURRENCY_SYMBOL, DISPLAY_TIMEZONE, LOW_STOCK_THRESHOLD, MAX_CONTENT_LENGTH, absolute upload dirs), CSRFProtect, error handlers (render 404/500 templates, minimal Spanish placeholders ok until T2), test config isolation, `conftest.py` with in-memory DB, context processor + Jinja filters (`moneda`, `fecha`, `fecha_hora`, `categoria_label`, `avatar_url`), Flask-Login Spanish message, safe-redirect helper, `static/img/avatar-default.svg`, tests for filters/helpers/config/isolation (RED first). Commit: `refactor(app): unify create_app and isolate test database`.
- [x] T2 (DONE, uncommitted) Design system + layout: `base.html` (lang es, pinned CDNs, tailwind config, navbar, flash, footer, blocks), `static/css/app.css`, delete `static/css/style.css`, `templates/_macros.html`, `404.html`, `500.html`, plus navbar logout form (POST). Commit: `feat(ui): add formal design system and Spanish base layout`.
- [x] T3 Auth + profile: completed locally without commit; authentication and profile translated, redesigned and validated; POST logout, safe redirects, hardened avatar uploads and Spanish CSRF handling.
- [ ] T4 Items: single `AddItemForm`/`EditItemForm`, `main.py` (list, add, edit, view, delete POST button everywhere, search, CSV import/export linked, edit-image bug, Spanish flashes, empty states, threshold), templates `index/add/edit/view/search/import_csv`, tests. Commit: `feat(items): rebuild inventory screens in Spanish`.
- [ ] T5 Dashboard: single route + redirect, Spanish template, category chart, empty state, tests. Commit: `feat(dashboard): unify dashboard route and rebuild in Spanish`.
- [ ] T6 Docs: README in Spanish, final repo-wide grep for leftover English UI strings and emojis, full test run, update this document. Commit: `docs: translate README and document configuration`.

## Acceptance criteria
- Zero user-visible English strings remain (grep of templates, `forms.py`, `flash(`, README) except proper nouns/data contracts listed in Out of scope.
- All pages render with one consistent design; every POST form carries a CSRF token; app runs via `flask run` and `python app.py`.
- `pytest` passes, never touches `inventory.db`, covers the scenarios in "Tests" above.
- No regression of item authorization (owner-only view/edit/delete).

## Progress / evidence
- T1 done (route: delegated direct, trigger 2+ non-trivial files). Evidence: parent re-ran `pytest -q` -> 66 passed; `inventory.db` unchanged (Length 20480, LastWriteTime 6/10/2026 23:50:54). Files: app.py, config.py, extensions.py, utils.py (new), static/img/avatar-default.svg (new), tests/conftest.py, tests/test_utils.py (new), tests/test_app_config.py (new), tests/test_auth.py.
- T1 deviations/notes for later tasks:
  - 404/500 handlers have an inline Spanish fallback (`_FALLBACK_ERROR_PAGES` in app.py) used when templates are missing; T2 adds real templates and must remove the fallback.
  - `zoneinfo` needs `tzdata` (not installed; requirements.txt untouchable): UTC uses `datetime.timezone.utc`; other zones silently fall back to UTC. Decision for the user at the end: add `tzdata` or keep UTC.
  - CSRFProtect is active: every POST form needs `csrf_token()` (T2 logout form, T3 profile/auth forms, T4 delete/import, etc.).
  - `profile.py` still uses relative `static/avatars` + own UPLOAD_FOLDER; `main.py` reads UPLOAD_FOLDER not in config -> T3/T4 switch to `AVATAR_UPLOAD_FOLDER` / `ITEM_UPLOAD_FOLDER`.
  - `auth.py` open redirect + GET logout pending T3 (`utils.is_safe_redirect_target` ready). `dashboard.py` threshold must use `<=` (T5). `pytz` Jinja global kept for legacy profile.html until T3 replaces it (then remove it from app.py).
  - Existing tests still assert English (`Dashboard`, `Login`, `Invalid username or password.`): translate when UI changes (T2/T3).

- T2 done (delegated direct). Evidence: parent re-ran `pytest -q` -> 126 passed; inventory.db unchanged; `static/css/style.css` deleted; `static/css/app.css` (427 lines) and `templates/_macros.html` (180 lines) created.
  - Component API for later tasks: CSS `.btn .btn-primary .btn-secondary .btn-danger .btn-ghost .btn-sm .card .card-header .card-body .form-label .form-input .form-input-error .form-error .form-help .form-check .badge(-neutral|-warning|-danger|-success) .table-wrap .table .cell-truncate .text-numeric .page-header .page-title .page-subtitle .pagination* .empty-state* .alert-*`. Macros (`{% from "_macros.html" import ... %}`): `field(f, help=None, **kwargs)`, `form_errors(form)`, `csrf_field()`, `page_header(title, subtitle=None)` (use with `{% call %}` for actions), `pagination(pag, endpoint, **params)`, `empty_state(title, text, action_url, action_label, icon)`, `delete_form(url, label, confirm, size)`, `stock_badge(quantity, threshold=None)` (reads config), `flash_messages()`. Base blocks: `title`, `head`, `content`, `scripts`.
  - Open: navbar logout POSTs to `auth.logout` (GET-only until T3); CSRFError returns bare English 400 (T3 handler); `pytz` global still in app.py until T3; legacy templates still English until T3-T5; no browser check of Play CDN output yet (do a visual check at the end).

## PIVOT (user decision, supersedes inventory semantics where they conflict)
The app is for managing LOST AND FOUND OBJECTS at a university, not a priced inventory. User decisions: (a) money/price/quantity make no sense and must go; (b) add a MONTHLY dashboard (how many objects were lost during the month) and an export based on the selected month; (c) improve the design without adding new libraries (no Tailwind build, no htmx/Alpine; only bump Chart.js to 4.5.1, pinned); (d) everyone logged in sees ALL reports, search and dashboard; only the creator can edit/delete a report; NO roles.
Web research (official docs, verified): Tailwind v4 is current but the CDN is dev-only (prod needs CLI/Vite+Node) -> not adopted; htmx/Alpine optional -> not adopted; Chart.js latest seen 4.5.1.
T4 (inventory items UI, 450 tests green) was completed before the pivot and is now the base to be converted.

### New domain (design decisions made by orchestrator)
- Product name in UI: "Objetos perdidos". Item = one report.
- Fields: `name` ("Objeto"), `description`, `category`, `location` ("Lugar", required, <=120), `event_date` (date, "Fecha del suceso", required, not in the future, default today), `status`, `contact` ("Contacto", optional, <=120, email or phone free text), `image_filename`, `created_at`, `user_id` (reporter).
- Status keys (English, stored) and labels: `lost` Perdido, `found` Encontrado, `returned` Entregado. Default `lost`.
- Category keys and labels: `documents` Documentos, `electronics` Electrónica, `keys` Llaves, `clothing` Ropa y accesorios, `bags` Mochilas y útiles, `other` Otros. Legacy keys (`general`, `office`, `consumable`) fall back to the raw value in `categoria_label` unless migrated: migration maps `electronics`->`electronics`, everything else -> `other`.
- `quantity` and `price` leave the model, forms, CSV, templates, dashboard, config (`CURRENCY_SYMBOL`, `LOW_STOCK_THRESHOLD`), filters (`moneda`, `numero`), macros (`stock_badge`). Legacy DB columns are NOT dropped from `inventory.db` (non-destructive); they stay unused. The migration must be idempotent and additive.
- Dashboard: month selector `?mes=YYYY-MM` (default current month in `DISPLAY_TIMEZONE`), KPIs by `event_date` in the month: Reportados, Perdidos (status lost), Encontrados (found), Entregados (returned), plus delivery rate; charts (Chart.js 4.5.1 pinned): per-day bar, by-category bar, top locations horizontal bar; table of the month's reports; button "Exportar mes" -> CSV of that month `objetos_YYYY-MM.csv`.
- CSV data contract (English headers): `id,name,description,category,location,event_date,status,contact,image_filename,reported_by,created_at`. Import keeps working with required `name`, `location`, `event_date` (YYYY-MM-DD), optional `description,category,status,contact`.
- Design polish (no new libs): gallery of cards with photo for the list, filter bar (status chips, category, month), status badges with distinct semantic colors (lost amber, found blue, returned green), one-click "Marcar como entregado" for the owner, formal copy.

### Pivot tasks (sequential; none committed)
- [ ] P1 Additive domain layer: new columns + status/category constants + idempotent legacy-schema upgrade (tested against a temp legacy DB), config/helpers; keep quantity/price temporarily so the suite stays green.
- [ ] P2 Items UI/routes/forms/CSV for lost objects (visibility all, owner-only edit/delete, gallery, filters, mark returned); remove quantity/price everywhere.
- [ ] P3 Monthly dashboard + monthly export; remove duplicated dashboard route (original T5).
- [x] P3 (DONE, uncommitted) Monthly dashboard + monthly export; removed duplicated dashboard route and priced-inventory UI/model exposure. Evidence: dashboard tests 96 passed; full suite reported 701 passed; parent spot check 96 passed; inventory.db unchanged (20480 bytes, 7/10/2026 01:31:54).
- [x] P4 (DONE, uncommitted) Final polish: terminology sweep, README in Spanish, isolated visual smoke checks, and full test run. Browser inspection was unavailable. Evidence: 701 passed in 248.76s; inventory.db unchanged (20480 bytes, 7/10/2026 01:31:54); focused P4 tests 135 passed.

### U1 — Branding UCSS and subtle motion (delegated direct)

- **Scope:** local-only visual enhancement for the existing Spanish interface: use an authentic UCSS logo served locally, align shared CSS/Tailwind/chart colors with colors observed on official UCSS pages, and add restrained CSS-only entrance/hover/flash motion.
- **Constraints:** preserve behavior and Spanish copy; no backend, dependency, database, upload, or requirements changes; no commits, push, PR, or merge; respect keyboard focus and disable motion under `prefers-reduced-motion`.
- **Checks:** add deterministic branding tests for local logo URL/alt, valid image bytes, theme/chart consistency, reduced-motion rules, and existing layout behavior. Browser visual inspection is attempted only if an explicit browser tab is available; otherwise record it as unavailable.
- **Official evidence:** primary source `https://www.ucss.edu.pe/`; official logo asset `https://www.ucss.edu.pe/templates/gk_gamenews/images/logo.png`; observed source colors include `#00a2c5` in official inline CSS and `#39a1c4` in the official navigation border CSS. These are documented as colors observed on the official website, not as verified brand-guide values.
- **Files:** `static/img/ucss-logo.png`, `static/css/app.css`, `templates/base.html`, `templates/login.html`, `templates/register.html`, `templates/dashboard.html`, `tests/test_branding.py`, `README.md`, and this feature document.
- **Progress:** tracking entry created before source edits. Implemented local logo, observed palette, shared theme/chart alignment, and restrained motion. A separate RED run was not captured before implementation because the delegated workspace already contained the baseline and the source edit had to begin after U1 tracking; GREEN checks: 163 passed (`tests/test_branding.py`, `tests/test_layout.py`, `tests/test_dashboard.py`); full suite: 705 passed. `git diff --check` reported no whitespace errors. Logo verification: 12,426-byte PNG, signature `89 50 4e 47 0d 0a 1a 0a`, dimensions `277x88`; local image preview rendered successfully. Browser visual inspection of the running app was unavailable because no visible browser tab could be provided; do not treat the test-client checks as visual evidence. `inventory.db` remained 20,480 bytes with unchanged timestamp `7/10/2026 19:36:36`. No commit is planned under the local-only policy.

### U2 — Split login/register screens (delegated direct)

- **Scope:** local-only redesign of the anonymous screens `login.html` and `register.html` as a full-screen split layout: UCSS logo large on the left half (light area with decorative CSS spheres), dark UCSS-navy card vertically centered on the right half (date badge, product name, welcome heading, underlined inputs, password show/hide toggle, gradient submit). Stacked on viewports narrower than 900px.
- **Constraints:** UI only. No backend/Python, dependency, database, upload or requirements changes; no git mutations. Existing input names/ids, CSRF hidden field, `login_action` handling and flash messages preserved; no "forgot password" link (feature does not exist). Authenticated pages keep their exact markup: `base.html` only gains overridable blocks (`body_class`, `header`, `flash`, `main_class`, `footer`) whose defaults are the previous markup. Motion respects `prefers-reduced-motion`.
- **Checks (to mark only when observed):**
  - [x] RED run for the new/updated tests captured before templates/CSS change: 18 failed, 119 passed (new `auth-*` markup/CSS tests, `app.css?v=3`, base layout blocks).
  - [x] `tests/test_auth.py tests/test_branding.py tests/test_layout.py` green: 137 passed (after fixing two of my own tests that used the CSRF-disabled client to look for the token).
  - [x] Full suite green: 728 passed in 258.02s (isolated in-memory DB confirmed in `tests/conftest.py`).
  - [x] `git diff --check` exit 0 (only pre-existing LF/CRLF warnings); `inventory.db` still 20,480 bytes, last write 22:02:53, which predates this task (same timestamp as an untracked `static/uploads/1_20261008030253311466.webp` created by the running dev server, not by tests).
  - [ ] Visual inspection: NOT done. No desktop browser was connected (`browser.disconnected`), and `file://` URLs are not allowed. Layout, spacing, the date badge, sphere rendering and responsive behavior at 360px/900px are verified only by markup/CSS tests, not by eye.
- **Files:** `templates/base.html` (new overridable blocks `body_class`, `header`, `flash`, `main_class`, `footer`; defaults are the previous markup; `app.css?v=3`), `templates/login.html`, `templates/register.html`, `templates/_macros.html` (`field(..., password_toggle=true)`, `auth_spheres`, `auth_brand`, `auth_card_top`, `auth_scripts`), `static/css/app.css` (auth section at the end + reduced-motion list), `tests/test_branding.py`, `tests/test_auth.py`, `tests/test_layout.py`, this document.
- **Progress:** implemented and verified as listed. Tests that legitimately depended on the old anonymous header now read it from the 404 page (`test_layout.py` anonymous links, `test_branding.py` header/menu contrast); a new test pins the exact default chrome of authenticated pages. The running dev server caches templates, so it may keep serving the old login until it is restarted.

## Route declaration
- T3 verification: 239 passed, 224 warnings after fixing a false English substring assertion (`Cancel` matched `Cancelar`). Real database unchanged: 20480 bytes, last modified 6/10/2026 23:50:54. Remaining warnings include datetime.utcnow deprecations. T4 items and T5 dashboard remain pending.
Each task: delegated direct (one bounded writer per task; trigger: 2+ non-trivial files each). Parent does structural readback, one spot-check command per task, git state, and review assessment.

## Next step
Launch T1 writer.
