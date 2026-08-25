#!/usr/bin/env python3
"""Fail-closed validation for the temporary neutral Fondary site."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import sys


ROOT = Path(__file__).resolve().parent
PAGES = {
    Path("index.html"): "https://getfondary.com/",
    Path("privacy.html"): "https://getfondary.com/privacy",
}
ALLOWED_VISIBLE_TEXT = (
    "Fondary",
    "Product information is being updated.",
)
FORBIDDEN_SOURCE_MARKERS = (
    "ashraya studio",
    "kalpesh patel",
    "mailto:",
    "copyright",
    "©",
)
FORBIDDEN_CLAIM_MARKERS = (
    "privacy policy",
    "family",
    "price",
    "pricing",
    "app store",
    "download",
    "available now",
    "coming soon",
    "voice",
    "speech",
    "icloud",
    "analytics",
    "tracking",
    "$",
)


class NeutralPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.body_depth = 0
        self.ignored_depth = 0
        self.title_depth = 0
        self.title = ""
        self.description = ""
        self.canonical = ""
        self.h1_count = 0
        self.main_count = 0
        self.script_count = 0
        self.form_count = 0
        self.anchor_count = 0
        self.embedded_count = 0
        self.resource_references: list[str] = []
        self.visible_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "body":
            self.body_depth += 1
        elif tag in {"style", "script"}:
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
                self.resource_references.append(values["src"] or "")
        elif tag == "form":
            self.form_count += 1
        elif tag == "a":
            self.anchor_count += 1
            if values.get("href"):
                self.resource_references.append(values["href"] or "")
        elif tag in {"img", "iframe", "object", "embed", "source"}:
            self.embedded_count += 1
            reference = values.get("src") or values.get("data") or ""
            if reference:
                self.resource_references.append(reference)
        elif tag == "meta" and values.get("name") == "description":
            self.description = values.get("content") or ""
        elif tag == "link" and values.get("rel") == "canonical":
            self.canonical = values.get("href") or ""
        elif tag == "link":
            if values.get("href"):
                self.resource_references.append(values["href"] or "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "body" and self.body_depth:
            self.body_depth -= 1
        elif tag in {"style", "script"} and self.ignored_depth:
            self.ignored_depth -= 1
        if tag == "title" and self.title_depth:
            self.title_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.title_depth:
            self.title += data
        if self.body_depth and not self.ignored_depth:
            normalized = " ".join(data.split())
            if normalized:
                self.visible_text.append(normalized)


def validate_source(source: str, canonical: str) -> list[str]:
    parser = NeutralPageParser()
    parser.feed(source)
    errors: list[str] = []
    lowered = source.lower()
    public_text = " ".join(
        [parser.title, parser.description, *parser.visible_text]
    ).lower()

    if not parser.title.strip():
        errors.append("missing title")
    if parser.description != "Product information for Fondary is being updated.":
        errors.append("unexpected meta description")
    if parser.canonical != canonical:
        errors.append("unexpected canonical")
    if parser.h1_count != 1:
        errors.append("expected exactly one h1")
    if parser.main_count != 1:
        errors.append("expected exactly one main")
    if tuple(parser.visible_text) != ALLOWED_VISIBLE_TEXT:
        errors.append("visible text exceeds the neutral product/update statement")
    if parser.script_count:
        errors.append("JavaScript is not permitted")
    if parser.form_count:
        errors.append("forms are not permitted")
    if parser.anchor_count:
        errors.append("links are not permitted in the neutral package")
    if parser.embedded_count:
        errors.append("embedded assets or content are not permitted")
    if "@import" in lowered or "url(" in lowered:
        errors.append("external or referenced CSS assets are not permitted")
    for marker in FORBIDDEN_SOURCE_MARKERS:
        if marker.lower() in lowered:
            errors.append(f"forbidden claim or identity marker {marker}")
    for marker in FORBIDDEN_CLAIM_MARKERS:
        if marker.lower() in public_text:
            errors.append(f"forbidden public claim marker {marker}")
    for reference in parser.resource_references:
        parsed = urlsplit(reference)
        if parsed.scheme or reference.startswith("//"):
            errors.append(f"external reference {reference}")
    return errors


def run_self_test() -> int:
    source = (ROOT / "index.html").read_text(encoding="utf-8")
    mutations = (
        source.replace("Fondary</p>", "Ashraya Studio</p>"),
        source.replace("</main>", "<p>Download on the App Store</p></main>"),
        source.replace("</main>", "<form></form></main>"),
        source.replace("</main>", "<script></script></main>"),
        source.replace("</main>", '<img src="https://example.invalid/pixel.png" alt=""></main>'),
        source.replace("</main>", '<a href="mailto:test@example.invalid">Contact</a></main>'),
    )
    for number, mutation in enumerate(mutations, start=1):
        if not validate_source(mutation, PAGES[Path("index.html")]):
            print(f"self-test mutation {number} was not rejected", file=sys.stderr)
            return 1
    print("Fondary neutral-site validator self-test passed.")
    return 0


def main() -> int:
    errors: list[str] = []
    for relative_path, canonical in PAGES.items():
        path = ROOT / relative_path
        if not path.is_file():
            errors.append(f"missing {relative_path}")
            continue
        for error in validate_source(path.read_text(encoding="utf-8"), canonical):
            errors.append(f"{relative_path}: {error}")

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
            "/Users/hermes/.local/bin/hermes -z",
            "exclusive operator",
            "D-016",
            "D-027",
        ):
            if marker not in agent_text:
                errors.append(f"AGENTS.md missing governance marker {marker}")

    if errors:
        print("Fondary neutral-site validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Fondary neutral-site validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_self_test() if "--self-test" in sys.argv[1:] else main())
