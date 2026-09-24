"""UI, responsive-design and accessibility checks for IPTT.

Two layers:

* Static checks (always run) inspect the shipped templates and stylesheets for
  the shared layout contract: viewport meta, main landmark, skip link, shared
  theme/script include, the CloudTeam footer, responsive breakpoints, reduced
  motion, focus styles and a WCAG-AA colour palette.
* Live checks (run when the app answers) log in and verify every page actually
  serves the same shell and footer.

Read-only: makes no schema or data changes. Exit code 1 on any failure.

Run inside the app container after startup:

    docker-compose -p iptt-lab -f compose.postgres.yaml exec app python scripts/check_ui.py

Optional environment overrides:
    IPTT_BASE_URL   default http://127.0.0.1:8080
    IPTT_USERNAME   default admin
    IPTT_PASSWORD   default SEED_ADMIN_PASSWORD or admin123
    IPTT_OFFLINE=1  skip the live checks
"""

import http.cookiejar
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = os.getenv("IPTT_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
USERNAME = os.getenv("IPTT_USERNAME", "admin")
PASSWORD = os.getenv("IPTT_PASSWORD", os.getenv("SEED_ADMIN_PASSWORD", "admin123"))

PAGES = [
    "/login",
    "/home",
    "/programmes",
    "/projects/1",
    "/dashboard",
    "/circle-dashboard",
    "/users",
    "/profile",
    "/audit-logs",
    "/programme/1/executive-dashboard",
    "/project/1/executive-dashboard",
    "/project/1/execution",
    "/project/1/forecast-dashboard",
    "/project/1/scopes",
    "/tasks/1",
    "/scope/1/execution",
    "/project/1/circle/AP",
]

# Colour literals that used to fail WCAG AA on their own surfaces. Keeping them
# out of the code is what stops the regressions we just fixed from coming back.
BANNED_LITERALS = [
    (r"color:\s*(?:red|green|orange|gray|grey)\b", "CSS colour keyword as text colour"),
    (r"color:\s*#0078d4\b", "#0078d4 text (3.4:1 on the app background)"),
    (r"color:\s*#94a3b8\b", "#94a3b8 text (2.6:1 on white)"),
    (r"color:\s*#718096\b", "#718096 text (3.0:1 on the app background)"),
    (r"color:\s*#6b7280\b", "#6b7280 text (3.7:1 on the app background)"),
    (r"color:\s*#777\b", "#777 text (3.4:1 on white)"),
    (r"color:\s*#888\b", "#888 text (3.0:1 on white)"),
    (r"color:\s*#855f00\b", "#855f00 text (4.2:1 on white)"),
    (r"background(?:-color)?:\s*#16a34a\b", "#16a34a surface with white text (3.3:1)"),
    (r"background(?:-color)?:\s*#28a745\b", "#28a745 surface with white text (3.1:1)"),
    (r"background(?:-color)?:\s*#ff9800\b", "#ff9800 surface with white text (2.2:1)"),
    (r"background(?:-color)?:\s*#059669\b", "#059669 surface with white text (3.8:1)"),
    (r"background(?:-color)?:\s*#319795\b", "#319795 surface with white text (3.5:1)"),
    (r"background(?:-color)?:\s*#e0e0e0\b", "#e0e0e0 surface with white text (1.3:1)"),
]

REQUIRED_TOKENS = [
    "--iptt-ink",
    "--iptt-muted",
    "--iptt-link",
    "--iptt-line",
    "--iptt-blue",
    "--iptt-shadow",
    "--iptt-success",
    "--iptt-warning",
    "--iptt-danger",
]

REQUIRED_CSS = [
    ("@media (max-width: 1000px)", "tablet breakpoint"),
    ("@media (max-width: 640px)", "phone breakpoint"),
    ("@media (prefers-reduced-motion: reduce)", "reduced-motion support"),
    ("@media print", "print styles"),
    (":focus-visible", "visible keyboard focus"),
    (".iptt-footer", "shared footer styling"),
    ("#iptt-main", "main landmark styling"),
    (".iptt-menu-toggle", "mobile navigation toggle"),
]

MAX_STATIC_ASSET_KB = 400

failures: list[str] = []
checks = 0


def check(condition: bool, message: str) -> None:
    global checks
    checks += 1
    if not condition:
        failures.append(message)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def relative_luminance(hex_colour: str) -> float:
    value = hex_colour.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    channels = [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def blend(foreground: str, background: str, alpha: float) -> str:
    """Composite a colour over a background at the given opacity."""
    fg = [int(foreground.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    bg = [int(background.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    mixed = [round(fg[i] * alpha + bg[i] * (1 - alpha)) for i in range(3)]
    return "#%02x%02x%02x" % tuple(mixed)


def contrast(foreground: str, background: str) -> float:
    a, b = relative_luminance(foreground), relative_luminance(background)
    high, low = max(a, b), min(a, b)
    return (high + 0.05) / (low + 0.05)


# --------------------------------------------------------------------------
# Static checks
# --------------------------------------------------------------------------
def static_checks() -> None:
    html_files = sorted((ROOT / "templates").glob("*.html"))
    partials = sorted((ROOT / "templates" / "partials").glob("*.html"))
    css_files = sorted((ROOT / "static").glob("*.css"))
    js_files = sorted((ROOT / "static").glob("*.js"))
    sources = html_files + partials + css_files + js_files

    # 1. Palette + responsive declarations in the shared stylesheet.
    theme = read(ROOT / "static" / "theme.css")
    for token in REQUIRED_TOKENS:
        check(token in theme, f"static/theme.css is missing the {token} design token")
    for needle, label in REQUIRED_CSS:
        check(needle in theme, f"static/theme.css is missing {label} ({needle})")

    # 2. No low-contrast colour literals anywhere in the shipped UI.
    for path in sources:
        text = read(path)
        for pattern, label in BANNED_LITERALS:
            found = re.search(pattern, text)
            if found:
                failures.append(
                    f"{path.relative_to(ROOT)} uses {label} ({found.group(0)!r})"
                )
    # 3. Declared palette pairs must clear WCAG AA (4.5:1).
    pairs = [
        ("--iptt-ink", "#ffffff"), ("--iptt-muted", "#ffffff"),
        ("--iptt-link", "#ffffff"), ("--iptt-link", "#f2f5f9"),
        ("--iptt-success", "#ffffff"), ("--iptt-warning", "#ffffff"),
        ("--iptt-danger", "#ffffff"),
    ]
    for token, background in pairs:
        match = re.search(re.escape(token) + r":\s*(#[0-9a-fA-F]{3,8})", theme)
        check(match is not None, f"static/theme.css does not define {token}")
        if match:
            ratio = contrast(match.group(1), background)
            check(
                ratio >= 4.5,
                f"{token} ({match.group(1)}) is only {ratio:.2f}:1 on {background}, needs 4.5:1",
            )

    # 3b. Gradient banners that carry white text must be dark enough along the
    #     whole gradient. Automated contrast tools skip gradient backgrounds, so
    #     this is where the "light stop + white text" failure gets caught.
    gradient_pattern = re.compile(
        r"(background[^;\"']*linear-gradient\([^)]*\)[^;\"']*|linear-gradient\([^)]*\))"
        r"[^\"']*"
    )
    white_text = re.compile(r"color:\s*(?:#fff(?:fff)?|white)\b", re.I)
    for path in sources:
        text = read(path)
        for match in re.finditer(r"\.([a-z0-9-]+)\s*\{[^}]*linear-gradient\([^)]*\)[^}]*\}", text, re.I | re.S):
            block = match.group(0)
            if not white_text.search(block):
                continue
            for colour in re.findall(r"#[0-9a-fA-F]{6}\b", block):
                ratio = contrast(colour, "#ffffff")
                check(
                    ratio >= 4.5,
                    f"{path.relative_to(ROOT)}: white text sits on gradient stop {colour} "
                    f"({ratio:.2f}:1, needs 4.5:1)",
                )
        for match in re.finditer(r'style="([^"]*linear-gradient\([^)]*\)[^"]*)"', text):
            block = match.group(1)
            if not white_text.search(block):
                continue
            for colour in re.findall(r"#[0-9a-fA-F]{6}\b", block):
                ratio = contrast(colour, "#ffffff")
                check(
                    ratio >= 4.5,
                    f"{path.relative_to(ROOT)}: white text sits on gradient stop {colour} "
                    f"({ratio:.2f}:1, needs 4.5:1)",
                )

    # 3c. Text placed on the dark login panel must use the light palette.
    login = read(ROOT / "templates" / "login.html")
    for light in ("#cbd5e1", "#7dd3fc", "#b9c9db"):
        check(light in login, f"templates/login.html lost its light panel text colour {light}")

    # 4. Every page that loads the theme also carries the shared shell contract.
    for path in html_files:
        text = read(path)
        if "theme.css" not in text:
            continue
        name = path.relative_to(ROOT)
        check("viewport" in text, f"{name} loads the theme without a viewport meta tag")
        check("ui.js" in text, f"{name} loads the theme without the shared ui.js enhancements")
        check("theme.css?v=" in text, f"{name} loads theme.css without a cache key")
        check('lang="en"' in text, f"{name} has no document language")
        has_shell = 'id="iptt-main"' in text or '{% extends "base.html" %}' in text
        check(has_shell, f"{name} has neither a main landmark nor the shared base template")
        has_footer = "partials/footer.html" in text or 'class="iptt-footer"' in text
        check(has_footer, f"{name} does not include the shared footer")

    # 4b. Every application page uses the shared navigation partial, and no page
    #     still carries its own copy of the menu markup (that is what let page
    #     styles paint invisible links on the shared bar).
    for path in html_files:
        text = read(path)
        name = path.relative_to(ROOT)
        # A web page = a template that renders the app shell (extends the base
        # template, or is a standalone HTML document that loads the theme).
        # base.html is the shell itself, PDF exports and fragments are not pages.
        is_page = '{% extends "base.html" %}' in text or ("<html" in text and "theme.css" in text)
        if not is_page or path.name == "base.html":
            continue
        if path.name == "login.html":
            check('class="top-nav' not in text, f"{name} should not render the shared navigation")
            continue
        check('include "partials/nav.html"' in text, f"{name} does not include the shared navigation partial")
        check('class="top-nav"' not in text, f"{name} still renders its own navigation markup")

    # 4c. No template re-styles the shared navigation bar.
    for path in sources:
        text = read(path)
        if path.suffix not in {".html", ".css"}:
            continue
        for selector in (r"\.top-nav\b", r"\.nav-links\b", r"\.app-title\b"):
            found = re.search(r"[^{}\n]*" + selector + r"[^{}\n]*\{", text)
            if found and path.name not in {"nav.html", "theme.css"}:
                failures.append(
                    f"{path.relative_to(ROOT)} defines its own navigation styling "
                    f"({found.group(0).strip()[:60]!r}); the shared theme owns that"
                )

    # 4d. The brand in the shared navigation always points at /home.
    nav_partial = read(ROOT / "templates" / "partials" / "nav.html")
    check('href="/home"' in nav_partial, "the shared navigation has no link back to /home")
    check('class="iptt-brand"' in nav_partial, "the shared navigation has no IPTT brand element")
    check('partials/nav.html' not in read(ROOT / "templates" / "base.html"),
          "base.html must not include the navigation as well as its child pages")

    # 5. The footer credit itself.
    footer = read(ROOT / "templates" / "partials" / "footer.html")
    check("Hosted with" in footer, "the footer is missing the 'Hosted with' credit")
    check("CloudTeam" in footer, "the footer is missing the CloudTeam credit")
    check("by <strong>CloudTeam</strong>" in footer or "by <strong>NPE CloudTeam</strong>" in footer,
          "the footer credit is not 'Hosted with ... CloudTeam'")
    check("iptt-heart" in footer, "the footer credit is missing the heart")
    check("role=\"img\"" in footer and 'aria-label="love"' in footer,
          "the footer heart needs role=img and aria-label=love for screen readers")
    check("made with" not in footer, "the footer still uses the old 'made with' wording")

    # 5b. Motion: the footer credit must fade in and beat on hover/focus, and
    #     every animation must be switched off for reduced-motion visitors.
    for keyframe in ("iptt-footer-fade", "iptt-heartbeat", "iptt-rise", "iptt-drop-in", "iptt-grow"):
        check(f"@keyframes {keyframe}" in theme, f"static/theme.css is missing the {keyframe} animation")
    check(".iptt-footer-credit:hover .iptt-heart" in theme or
          ".iptt-footer-credit:hover .iptt-heart," in theme,
          "the footer heart does not beat on hover")
    check("focus-within .iptt-heart" in theme, "the footer heart does not beat on keyboard focus")
    reduced = theme[theme.index("prefers-reduced-motion: reduce"):]
    check("animation: none !important" in reduced, "reduced motion does not disable animations")
    check(".iptt-js .iptt-reveal" in theme, "scroll-reveal styles are missing")
    print_block = theme[theme.index("@media print"):]
    check("iptt-reveal" in print_block, "print styles do not force revealed blocks visible")

    # 5c. The credit must stay readable while faded (AA on the page background).
    credit_match = re.search(r"\.iptt-footer-credit \{[^}]*opacity: ([\d.]+)", theme)
    check(credit_match is not None, "could not read the footer credit opacity")
    if credit_match:
        opacity = float(credit_match.group(1))
        blended = blend("#172b43", "#f2f5f9", opacity)
        ratio = contrast(blended, "#f2f5f9")
        check(ratio >= 4.5, f"the faded footer credit is only {ratio:.2f}:1, needs 4.5:1")

    # 5d. ui.js must not be able to leave content hidden.
    ui_js = read(ROOT / "static" / "ui.js")
    check("iptt-reveal-in" in ui_js, "ui.js does not reveal on-scroll blocks")
    check("setTimeout(() => revealables.forEach(reveal)" in ui_js,
          "ui.js has no safety net that reveals every block")

    # 6. Page weight: keep the login logo and other static art small.
    for asset in sorted((ROOT / "static").iterdir()):
        if asset.suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif"}:
            continue
        size_kb = asset.stat().st_size / 1024
        check(
            size_kb <= MAX_STATIC_ASSET_KB,
            f"static/{asset.name} is {size_kb:.0f} KB, over the {MAX_STATIC_ASSET_KB} KB budget",
        )


# --------------------------------------------------------------------------
# Live checks
# --------------------------------------------------------------------------
def build_opener() -> tuple[urllib.request.OpenerDirector, http.cookiejar.CookieJar]:
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar)), jar


def fetch(opener, path: str, data: dict | None = None):
    url = urllib.parse.urljoin(BASE_URL + "/", path.lstrip("/"))
    body = urllib.parse.urlencode(data).encode() if data else None
    return opener.open(urllib.request.Request(url, data=body), timeout=20)


def live_checks() -> bool:
    opener, cookies = build_opener()
    try:
        fetch(opener, "/login")
    except (urllib.error.URLError, OSError) as exc:
        print(f"SKIP: live checks - {BASE_URL} not reachable ({exc})")
        return False

    try:
        fetch(opener, "/login", {"username": USERNAME, "password": PASSWORD})
    except urllib.error.HTTPError as exc:
        failures.append(f"login failed with HTTP {exc.code}")
        return True

    for path in PAGES:
        try:
            response = fetch(opener, path)
            page = response.read().decode("utf-8", "replace")
            status = response.status
        except urllib.error.HTTPError as exc:
            failures.append(f"GET {path} returned HTTP {exc.code}")
            continue
        except (urllib.error.URLError, OSError) as exc:
            failures.append(f"GET {path} failed: {exc}")
            continue

        check(status == 200, f"GET {path} returned HTTP {status}")
        check(page.count('class="iptt-footer"') == 1, f"{path} must render exactly one footer")
        check("CloudTeam" in page, f"{path} footer is missing the CloudTeam credit")
        check("Hosted with" in page, f"{path} footer is missing the 'Hosted with' credit")
        if path != "/login":
            check(page.count('class="top-nav') == 1, f"{path} must render exactly one navigation bar")
            check('href="/home"' in page, f"{path} navigation has no link back to /home")
        check('id="iptt-main"' in page, f"{path} has no main landmark")
        check("theme.css" in page, f"{path} does not load the shared theme")
        check("ui.js" in page, f"{path} does not load the shared ui.js enhancements")

    # /projects used to answer 422 when the programme id was absent; it must
    # now forward the visitor instead. Redirects are checked without following.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    plain = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookies), NoRedirect
    )
    try:
        response = plain.open(BASE_URL + "/projects", timeout=20)
        check(False, f"GET /projects should redirect, returned HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        check(
            exc.code in (301, 302, 303, 307, 308),
            f"GET /projects returned HTTP {exc.code}; expected a redirect",
        )
    return True


def main() -> None:
    static_checks()
    live = live_checks()

    if failures:
        print(f"FAIL: {len(failures)} of {checks} UI checks failed")
        for item in failures:
            print(f"  - {item}")
        raise SystemExit(1)

    scope = "static + live" if live else "static"
    print(f"PASS: {checks} UI checks passed ({scope})")


if __name__ == "__main__":
    main()
