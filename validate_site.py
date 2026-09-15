#!/usr/bin/env python3
"""Dependency-free structural, privacy, and identity checks for getfondary.com."""

from __future__ import annotations

from hashlib import sha256
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit
import re
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent
CANONICAL_ORIGIN = "https://getfondary.com"
PAGE_PATHS = {
    Path("index.html"): "/",
    Path("privacy.html"): "/privacy",
    Path("support/index.html"): "/support/",
    Path("terms/index.html"): "/terms/",
}
PAGE_MAILBOXES = {
    Path("index.html"): {"support@madebykal.com"},
    Path("privacy.html"): {
        "support@madebykal.com",
        "privacy@madebykal.com",
        "security@madebykal.com",
    },
    Path("support/index.html"): {"support@madebykal.com"},
    Path("terms/index.html"): {"support@madebykal.com"},
}
SUPPORT_EMAIL = "support@madebykal.com"
PRIVACY_EMAIL = "privacy@madebykal.com"
SECURITY_EMAIL = "security@madebykal.com"
APPROVED_PUBLIC_EMAILS = {SUPPORT_EMAIL, PRIVACY_EMAIL, SECURITY_EMAIL}
LEGAL_OPERATOR_NAME = "Kalpesh Patel"
CONTROLLER_DISCLOSURE = f"The data controller is {LEGAL_OPERATOR_NAME}."
EMAIL_PATTERN = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
FORBIDDEN_PUBLIC_IDENTITY = ("ashraya", "ashrayastudio", "copyright", "©")
FORBIDDEN_TRACKERS = (
    "google-analytics",
    "googletagmanager",
    "facebook.net",
    "segment.io",
    "mixpanel",
    "hotjar",
)
APPROVED_EXTERNAL_ANCHORS = {
    "https://www.apple.com/legal/internet-services/itunes/dev/stdeula/",
    "https://www.zoho.com/privacy.html",
    "https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement",
}
REQUIRED_PAGE_TEXT = {
    Path("index.html"): (
        "Your life,",
        "remembered.",
        "Preparing for the App Store",
        "Capture in the moment.",
        "Find it in your own words.",
        "Local by default",
        "Optional personal iCloud",
        "25 memories",
        "support@madebykal.com",
        "Please do not send private memories, health details, voice recordings, or exports.",
        "No public app availability is claimed.",
    ),
    Path("privacy.html"): (
        "Effective September 14, 2026.",
        "Memories are stored locally by default.",
        "Personal sync is off by default.",
        "private CloudKit database",
        "Voice audio is used transiently",
        "Fondary Watch app is capture-only",
        "no third-party analytics SDK",
        "Please do not send private memories, health details, voice recordings, or exports.",
        CONTROLLER_DISCLOSURE,
    ),
    Path("support/index.html"): (
        "A clear next step.",
        "Restore Purchases",
        "Can support recover my memories?",
        "Nothing is sent or attached automatically.",
        "Please do not send private memories, health details, voice recordings, or exports.",
    ),
    Path("terms/index.html"): (
        "Terms of Use",
        "Apple Standard End User License Agreement",
        "existing memories remain readable",
        "Please do not send private memory content.",
    ),
}
EXPECTED_ASSET_SHA256 = {
    Path("assets/fondary-icon.png"): "92b7f44a9acc4fbcc9135ac241deb4bc741bd8c29ade3de1d56e139068a04350",
    Path("assets/fondary-home.png"): "c7469c21fd9ca94f002f005a977adeda7ca0e359e2b9788b0b7d399f2df0f18c",
    Path("assets/fondary-capture.png"): "6b142fae9890e9afec91e2708643d4cc21d89fa7108a08a3333438299b6cc7a8",
    Path("assets/fondary-search.png"): "346e12344eddcb68c73c684294217999ddb54cdafce143ba16b065c293b3e457",
}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_depth = 0
        self.title = ""
        self.h1_count = 0
        self.main_count = 0
        self.description = ""
        self.canonical = ""
        self.internal_links: list[str] = []
        self.external_anchors: list[str] = []
        self.image_errors: list[str] = []
        self.script_count = 0
        self.form_count = 0
        self.embedded_count = 0
        self.resource_dependencies: list[str] = []
        self.attribute_values: list[str] = []
        self.rendered_text: list[str] = []
        self.ignored_depth = 0
        self.skip_link = False
        self.unsafe_markup = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        self.attribute_values.extend(value for value in values.values() if value)
        if len(values) != len(attrs) or any(name.startswith("on") for name in values):
            self.unsafe_markup = True
        if tag == "meta" and values.get("http-equiv"):
            self.unsafe_markup = True
        if any(name in values for name in ("srcdoc", "srcset", "ping", "action", "formaction")):
            self.unsafe_markup = True
        if tag in {"style", "script"}:
            self.ignored_depth += 1
        if tag == "title":
            self.title_depth += 1
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "main":
            self.main_count += 1
        elif tag == "script":
            self.script_count += 1
            if values.get("src"):
                self.resource_dependencies.append(values["src"] or "")
        elif tag == "form":
            self.form_count += 1
        elif tag in {"iframe", "object", "embed", "audio", "video"}:
            self.embedded_count += 1
            reference = values.get("src") or values.get("data") or ""
            if reference:
                self.resource_dependencies.append(reference)
        elif tag == "meta" and values.get("name") == "description":
            self.description = values.get("content") or ""
        elif tag == "link" and values.get("rel") == "canonical":
            self.canonical = values.get("href") or ""
        elif tag == "link":
            href = values.get("href") or ""
            if href:
                self.resource_dependencies.append(href)
                if href.startswith("/"):
                    self.internal_links.append(href)
        elif tag == "a":
            href = values.get("href") or ""
            if values.get("class") == "skip-link" and href == "#main":
                self.skip_link = True
            if href.startswith("/"):
                self.internal_links.append(href)
            elif urlsplit(href).scheme in {"http", "https"}:
                self.external_anchors.append(href)
        elif tag == "img":
            if "alt" not in values:
                self.image_errors.append(
                    f"image {values.get('src', '<missing src>')} has no alt attribute"
                )
            src = values.get("src") or ""
            if src:
                self.resource_dependencies.append(src)
                if src.startswith("/"):
                    self.internal_links.append(src)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self.title_depth:
            self.title_depth -= 1
        if tag in {"style", "script"} and self.ignored_depth:
            self.ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.title_depth:
            self.title += data
        if not self.ignored_depth:
            normalized = " ".join(data.split())
            if normalized:
                self.rendered_text.append(normalized)


def repository_html_paths() -> list[Path]:
    return sorted(
        path.relative_to(ROOT)
        for path in ROOT.rglob("*.html")
        if ".git" not in path.relative_to(ROOT).parts
    )


def local_target(reference: str) -> Path:
    path = urlsplit(reference).path
    if path == "/privacy":
        return ROOT / "privacy.html"
    candidate = ROOT / path.lstrip("/")
    if path.endswith("/"):
        candidate /= "index.html"
    return candidate


def page_parser(source: str) -> PageParser:
    parser = PageParser()
    parser.feed(source)
    return parser


def public_policy_errors(
    source: str,
    parser: PageParser,
    *,
    allow_controller_disclosure: bool = False,
) -> list[str]:
    errors: list[str] = []
    rendered_text = " ".join(parser.rendered_text)
    public_surface_text = " ".join(
        [parser.title, parser.description, *parser.rendered_text, *parser.attribute_values]
    )
    decoded_surface = unquote(unescape(public_surface_text)).lower()
    decoded_source = unquote(unescape(source)).lower()

    for marker in FORBIDDEN_PUBLIC_IDENTITY:
        if marker.lower() in decoded_source or marker.lower() in decoded_surface:
            errors.append(f"forbidden public identity marker {marker}")

    operator_count = decoded_surface.count(LEGAL_OPERATOR_NAME.lower())
    if allow_controller_disclosure:
        if (
            source.count(CONTROLLER_DISCLOSURE) != 1
            or rendered_text.count(CONTROLLER_DISCLOSURE) != 1
            or operator_count != 1
        ):
            errors.append("privacy page must contain exactly one approved controller disclosure")
    elif LEGAL_OPERATOR_NAME.lower() in decoded_source or operator_count:
        errors.append(f"forbidden public identity marker {LEGAL_OPERATOR_NAME}")

    if parser.script_count:
        errors.append("JavaScript is not permitted")
    if parser.form_count:
        errors.append("forms are not permitted")
    if parser.embedded_count:
        errors.append("embedded content is not permitted")
    if parser.unsafe_markup:
        errors.append("unsafe attributes or redirect markup are not permitted")

    for reference in parser.resource_dependencies:
        parsed = urlsplit(reference)
        if parsed.scheme in {"http", "https"} or reference.startswith("//"):
            errors.append(f"external runtime dependency {reference}")

    for reference in parser.external_anchors:
        if reference not in APPROVED_EXTERNAL_ANCHORS:
            errors.append(f"unapproved external link {reference}")

    for email in EMAIL_PATTERN.findall(decoded_surface):
        if email.casefold() not in APPROVED_PUBLIC_EMAILS:
            errors.append("email outside approved exact mailbox set")

    for reference in parser.attribute_values:
        decoded = unquote(unescape(reference))
        if not decoded.casefold().startswith("mailto:"):
            continue
        parsed = urlsplit(decoded)
        headers = parse_qsl(parsed.query, keep_blank_values=True)
        if (
            parsed.path.casefold() not in APPROVED_PUBLIC_EMAILS
            or parsed.netloc
            or parsed.fragment
            or any(ord(character) < 32 for character in decoded)
            or len(headers) != 1
            or headers[0][0] != "subject"
            or not headers[0][1].startswith("Fondary ")
        ):
            errors.append("unapproved Fondary mail link")
    return errors


def collect_errors() -> list[str]:
    errors: list[str] = []
    for relative_path, route in PAGE_PATHS.items():
        path = ROOT / relative_path
        if not path.is_file():
            errors.append(f"missing {relative_path}")
            continue
        source = path.read_text(encoding="utf-8")
        parser = page_parser(source)
        rendered = " ".join(parser.rendered_text)

        if not parser.title.strip():
            errors.append(f"{relative_path}: missing title")
        if not parser.description.strip():
            errors.append(f"{relative_path}: missing meta description")
        if parser.h1_count != 1:
            errors.append(f"{relative_path}: expected one h1, found {parser.h1_count}")
        if parser.main_count != 1:
            errors.append(f"{relative_path}: expected one main, found {parser.main_count}")
        if not parser.skip_link:
            errors.append(f"{relative_path}: missing skip link")
        expected_canonical = f"{CANONICAL_ORIGIN}{route}"
        if parser.canonical != expected_canonical:
            errors.append(
                f"{relative_path}: canonical is {parser.canonical!r}; expected {expected_canonical!r}"
            )
        for expected in REQUIRED_PAGE_TEXT[relative_path]:
            if expected not in rendered:
                errors.append(f"{relative_path}: missing required product/policy copy {expected!r}")
        found_mailboxes = {
            urlsplit(unquote(unescape(value))).path.casefold()
            for value in parser.attribute_values
            if unquote(unescape(value)).casefold().startswith("mailto:")
        }
        if found_mailboxes != PAGE_MAILBOXES[relative_path]:
            errors.append(
                f"{relative_path}: public mailboxes {sorted(found_mailboxes)!r} do not match the approved route set"
            )
        errors.extend(
            f"{relative_path}: {message}"
            for message in public_policy_errors(
                source,
                parser,
                allow_controller_disclosure=relative_path == Path("privacy.html"),
            )
        )
        errors.extend(f"{relative_path}: {message}" for message in parser.image_errors)
        for marker in FORBIDDEN_TRACKERS:
            if marker in source.lower():
                errors.append(f"{relative_path}: forbidden tracker reference {marker}")
        for reference in parser.internal_links:
            if not local_target(reference).exists():
                errors.append(f"{relative_path}: broken internal reference {reference}")

    registered = set(PAGE_PATHS)
    for relative_path in repository_html_paths():
        if relative_path in registered:
            continue
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        parser = page_parser(source)
        errors.extend(
            f"{relative_path}: {message}"
            for message in public_policy_errors(source, parser)
        )
        errors.extend(f"{relative_path}: {message}" for message in parser.image_errors)
        if relative_path == Path("404.html"):
            if parser.h1_count != 1 or parser.main_count != 1:
                errors.append("404.html must contain exactly one h1 and one main")
            for reference in parser.internal_links:
                if not local_target(reference).exists():
                    errors.append(f"404.html: broken internal reference {reference}")
        else:
            errors.append(f"unregistered HTML page {relative_path}")

    expected_files = (
        ".nojekyll",
        "404.html",
        "AGENTS.md",
        "CNAME",
        "README.md",
        "robots.txt",
        "sitemap.xml",
        "styles.css",
        "assets/fondary-icon.png",
        "assets/fondary-home.png",
        "assets/fondary-capture.png",
        "assets/fondary-search.png",
        "assets/dm-sans.ttf",
        "assets/dm-sans-license.txt",
        "assets/cormorant-garamond.ttf",
        "assets/cormorant-garamond-license.txt",
    )
    for relative_path in expected_files:
        if not (ROOT / relative_path).is_file():
            errors.append(f"missing {relative_path}")

    for relative_path, expected_digest in EXPECTED_ASSET_SHA256.items():
        path = ROOT / relative_path
        if path.is_file() and sha256(path.read_bytes()).hexdigest() != expected_digest:
            errors.append(f"{relative_path}: differs from the approved Fondary app asset")

    cname = ROOT / "CNAME"
    if not cname.is_file() or cname.read_text(encoding="utf-8").strip() != "getfondary.com":
        errors.append("CNAME must contain only getfondary.com")

    agents = ROOT / "AGENTS.md"
    if not agents.is_file():
        errors.append("missing AGENTS.md")
    else:
        agent_text = agents.read_text(encoding="utf-8")
        for marker in (
            "https://github.com/ashrayastudio/getfondary.git",
            "`gh` CLI",
            "macOS-keyring-backed credential helper",
            "Hermes is a bounded backup",
            "A sandbox denial requires narrow escalation",
            "D-016",
            "D-027",
            "D-039",
            "D-040",
            "D-041",
        ):
            if marker not in agent_text:
                errors.append(f"AGENTS.md missing governance marker {marker}")

    stylesheet = ROOT / "styles.css"
    if stylesheet.is_file():
        css = stylesheet.read_text(encoding="utf-8")
        for marker in (
            "--teal: #3d7a72",
            "--teal-dk: #2c5a54",
            "--linen: #f0ebe1",
            "--text: #0a1612",
            "--text-md: #3a4a42",
            'url("/assets/dm-sans.ttf")',
            'url("/assets/cormorant-garamond.ttf")',
            "prefers-reduced-motion",
        ):
            if marker not in css:
                errors.append(f"styles.css missing required brand/accessibility marker {marker}")
        if "@import" in css or "http://" in css or "https://" in css:
            errors.append("styles.css must not import external runtime resources")
        for gradient in ("linear-gradient(", "radial-gradient(", "conic-gradient("):
            if gradient in css:
                errors.append("styles.css must not use gradients")

    try:
        sitemap = ET.parse(ROOT / "sitemap.xml")
        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locations = {element.text for element in sitemap.findall("sm:url/sm:loc", namespace)}
        expected_locations = {f"{CANONICAL_ORIGIN}{route}" for route in PAGE_PATHS.values()}
        if locations != expected_locations:
            errors.append("sitemap routes do not exactly match the public page set")
    except (ET.ParseError, OSError) as error:
        errors.append(f"invalid sitemap: {error}")

    return errors


def run_self_test() -> int:
    rejected = (
        ("<p>Ashraya&#32;Studio</p>", "forbidden public identity marker"),
        ('<a href="mailto:help@example.com?subject=Fondary%20support">Support</a>', "email outside approved exact mailbox"),
        (f"<p>{LEGAL_OPERATOR_NAME}</p>", "forbidden public identity marker"),
        ("<p>&copy; 2026</p>", "forbidden public identity marker"),
        ("<form></form>", "forms are not permitted"),
        ("<script></script>", "JavaScript is not permitted"),
        ('<img src="https://example.invalid/pixel.png" alt="">', "external runtime dependency"),
        ('<iframe src="/remote"></iframe>', "embedded content is not permitted"),
        ('<a href="https://example.invalid/">External</a>', "unapproved external link"),
        ('<main onload="alert(1)"></main>', "unsafe attributes"),
    )
    for source, expected in rejected:
        parser = page_parser(source)
        if not any(expected in error for error in public_policy_errors(source, parser)):
            print(f"self-test did not reject {expected}", file=sys.stderr)
            return 1

    for address in (
        "other@gmail.com",
        "support+fondary@madebykal.com",
        "hello@madebykal.com",
        "support@madebykal.com.evil.example",
        "support@mail.madebykal.com",
    ):
        source = f'<a href="mailto:{address}?subject=Fondary%20support">Contact</a>'
        if not public_policy_errors(source, page_parser(source)):
            print("self-test accepted an unapproved mailbox", file=sys.stderr)
            return 1

    for suffix in (
        "&amp;cc=other%40gmail.com",
        "&amp;bcc=other%40gmail.com",
        "&amp;subject=duplicate",
        "%0D%0ABcc%3Aother%40gmail.com",
    ):
        source = f'<a href="mailto:{SUPPORT_EMAIL}?subject=Fondary%20support{suffix}">Contact</a>'
        if not public_policy_errors(source, page_parser(source)):
            print("self-test accepted an unsafe mail header", file=sys.stderr)
            return 1

    approved_mail = f'<a href="mailto:{SUPPORT_EMAIL}?subject=Fondary%20support">{SUPPORT_EMAIL}</a>'
    if public_policy_errors(approved_mail, page_parser(approved_mail)):
        print("self-test rejected the approved support mail link", file=sys.stderr)
        return 1

    approved_privacy = f"<p>{CONTROLLER_DISCLOSURE}</p>"
    if public_policy_errors(
        approved_privacy,
        page_parser(approved_privacy),
        allow_controller_disclosure=True,
    ):
        print("self-test rejected the exact privacy controller disclosure", file=sys.stderr)
        return 1

    for source in (
        f"<p>{CONTROLLER_DISCLOSURE}</p><p>{CONTROLLER_DISCLOSURE}</p>",
        f"<p>{LEGAL_OPERATOR_NAME} is the data controller.</p>",
    ):
        errors = public_policy_errors(
            source,
            page_parser(source),
            allow_controller_disclosure=True,
        )
        if not any("exactly one approved controller disclosure" in error for error in errors):
            print("self-test accepted non-standard privacy controller copy", file=sys.stderr)
            return 1

    current_errors = collect_errors()
    if current_errors:
        print("self-test could not validate the approved current site:", file=sys.stderr)
        for error in current_errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Fondary website validator self-test passed.")
    return 0


def main() -> int:
    errors = collect_errors()
    if errors:
        print("Fondary website validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Fondary website structural, identity, privacy, and asset validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_self_test() if "--self-test" in sys.argv[1:] else main())
