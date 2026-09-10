#!/usr/bin/env python3
"""Fail-closed validation for the approved Fondary website and privacy policy."""

from __future__ import annotations

from html.parser import HTMLParser
from html import unescape
from pathlib import Path
from urllib.parse import unquote
import re
import sys
import tempfile


ROOT = Path(__file__).resolve().parent
PAGES = {
    Path("index.html"): "https://getfondary.com/",
    Path("privacy.html"): "https://getfondary.com/privacy",
}
SUPPORT_WARNING = "Please do not send private memories, health details, voice recordings, or exports."
CONTROLLER_SENTENCE = "The data controller is Kalpesh Patel."
GOOGLE_PRIVACY = "https://policies.google.com/privacy"
GITHUB_PRIVACY = "https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement"
HOME_TEXT = (
    "Fondary",
    "Product information is being updated.",
    "Fondary support:",
    "appportfolio.contact@gmail.com",
    SUPPORT_WARNING,
    "The email link opens your email app. Nothing is sent or attached automatically.",
    "Privacy policy",
)
PRIVACY_TEXT = (
    "Fondary",
    "Privacy Policy",
    "Effective September 10, 2026.",
    "Short version",
    "Fondary is designed to keep your memories under your control. Memories are stored locally by default. Fondary does not sell memory content, use it for advertising, or operate a server that receives memory content for syncing or AI training.",
    "Fondary does not require a separate app account. Optional personal iCloud sync uses your Apple account.",
    "If you enable personal iCloud sync, Apple stores and synchronizes your memories through your private CloudKit database. Personal sync is off by default. Family collaboration and urgent family alerts are not included in this release.",
    "Information you add",
    "You may enter memory titles, descriptions, dates, categories, tags, and names of people. This content can be sensitive. Fondary stores it in the app's file-protected local repository until you delete it.",
    "Voice capture",
    "Voice audio is used transiently for speech recognition and is not saved as an audio recording. Fondary requires Apple's on-device speech recognition support and otherwise asks you to type. A saved transcript becomes memory content.",
    "Optional personal iCloud sync",
    "Personal iCloud sync is available at every Fondary tier. If you enable it, Fondary sends memory records to your private CloudKit database under your Apple account. Fondary does not operate the sync server.",
    "Deleting a synchronized memory creates a content-free deletion record so an older device cannot restore the deleted memory. That record contains only the memory's random identifier and deletion date, not its title, description, people, categories, tags, or search data. A deletion made while sync is off is kept locally and synchronized if you later turn sync on.",
    "Turning sync off stops CloudKit work. It does not delete records already in your iCloud database. Apple controls iCloud account processing and infrastructure under Apple's own terms and privacy policy.",
    "Apple Watch capture",
    "The Fondary Watch app is capture-only. Before the iPhone confirms a save, the Watch may retain the newly dictated text with a random identifier, timestamp, and delivery state in a file-protected outbox. It transfers that pending capture to the paired iPhone using Apple's WatchConnectivity service.",
    "After a saved or rejected acknowledgement, the Watch deletes the pending entry. Fondary does not copy your memory archive, search index, or saved memory bodies to the Watch.",
    "Purchases and Apple services",
    "Apple processes App Store purchases, subscription state, and restores. Fondary keeps a limited local entitlement cache so temporary StoreKit unavailability does not incorrectly remove paid access.",
    "Fondary also uses Apple system services for optional biometric lock, Siri and App Intents, local notifications, speech synthesis, and user-selected sharing destinations.",
    "Sharing and exports",
    "You can create PDF or JSON exports or open Apple's share sheet. Plain-text sharing first shows the exact payload, includes only the title by default, and lets you explicitly add memory details or the date. Fondary sends an export only to the destination you select.",
    "Exports may contain private memory content. Review the destination and preview before sharing. Family collaboration, participant invitations, shared CloudKit databases, and urgent recipient notifications are not part of this release.",
    "Analytics, advertising, and tracking",
    "Fondary includes no third-party analytics SDK, advertising SDK, or cross-app tracking SDK. Product and crash-quality decisions may use aggregated reports provided through Apple's App Store Connect and Xcode tools. Memory, voice, search, person, and support content is not added to product analytics.",
    "Support communications",
    "Fondary support:",
    "appportfolio.contact@gmail.com",
    "If you email support, your email address and the message or attachments you choose to send are used to respond to your request. The email link opens your email app. Nothing is sent or attached automatically.",
    SUPPORT_WARNING,
    "Support correspondence is handled by your email provider and Gmail. Their own privacy policies also apply.",
    "Google privacy policy",
    "We monitor the support inbox and delete resolved conversations from the support mailbox within 90 days, unless legally required to retain them longer. Copies retained by your email provider or Gmail are subject to their own policies.",
    "Website hosting",
    "This site is hosted on GitHub Pages. GitHub receives technical request information, such as your IP address, when serving the site. This site's code adds no contact forms, analytics, advertising, or cookies.",
    "GitHub privacy statement",
    "Your choices and deletion",
    "You can keep iCloud sync off, turn it on or off in Settings, export selected content, delete an individual memory, or delete all memories. When personal sync is enabled now or later, Fondary uses content-free deletion records to prevent an older device from restoring deleted memories.",
    "Privacy questions and policy changes",
    "Use the support contact above for privacy questions or to request access, correction, or deletion of your support messages. Do not send identity documents or sensitive personal information with your initial request.",
    CONTROLLER_SENTENCE,
    "Changes to this policy will appear on this page with an updated effective date.",
    "Back to Fondary support",
)
APPROVED_SUPPORT_LINK = "mailto:appportfolio.contact@gmail.com?subject=Fondary%20support"
FORBIDDEN_SOURCE_MARKERS = (
    "ashraya",
    "ashrayastudio",
    "kalpesh patel",
    "copyright",
    "©",
)


def repository_html_paths(root: Path = ROOT) -> list[Path]:
    """Return every repository HTML source while excluding Git internals."""
    return sorted(
        path.relative_to(root)
        for path in root.rglob("*.html")
        if ".git" not in path.relative_to(root).parts
    )


class SupportPageParser(HTMLParser):
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
        self.links: list[str] = []
        self.attribute_values: list[str] = []
        self.visible_text: list[str] = []
        self.unsafe_markup = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        self.attribute_values.extend(value for _, value in attrs if value)
        if len(values) != len(attrs) or any(name.startswith("on") for name in values):
            self.unsafe_markup = True
        if tag == "meta" and values.get("http-equiv"):
            self.unsafe_markup = True
        if any(name in values for name in ("srcdoc", "srcset", "ping", "action", "formaction")):
            self.unsafe_markup = True
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
            self.links.append(values.get("href") or "")
            if values.get("href"):
                self.resource_references.append(values["href"] or "")
        elif tag in {"img", "iframe", "object", "embed", "source", "audio", "video", "svg", "base"}:
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
    parser = SupportPageParser()
    parser.feed(source)
    errors: list[str] = []
    decoded = source
    for _ in range(5):
        decoded = unquote(unescape(decoded))
    lowered = decoded.lower()
    public_text = " ".join(
        [parser.title, parser.description, *parser.visible_text, *parser.attribute_values]
    ).lower()

    privacy = canonical == PAGES[Path("privacy.html")]
    expected_text = PRIVACY_TEXT if privacy else HOME_TEXT
    expected_title = "Fondary Privacy Policy" if privacy else "Fondary — Product information is being updated"
    expected_description = "How Fondary handles app, website, and support information." if privacy else "Product information for Fondary is being updated."
    expected_links = [APPROVED_SUPPORT_LINK, GOOGLE_PRIVACY, GITHUB_PRIVACY, "/"] if privacy else [APPROVED_SUPPORT_LINK, "/privacy"]
    if canonical not in PAGES.values():
        errors.append("unregistered canonical")
    if parser.title.strip() != expected_title:
        errors.append("unexpected title")
    if parser.description != expected_description:
        errors.append("unexpected meta description")
    if parser.canonical != canonical:
        errors.append("unexpected canonical")
    if parser.h1_count != 1:
        errors.append("expected exactly one h1")
    if parser.main_count != 1:
        errors.append("expected exactly one main")
    if tuple(parser.visible_text) != expected_text:
        errors.append("visible text differs from the exact approved website/privacy copy")
    if parser.unsafe_markup:
        errors.append("unsafe attributes or redirect markup are not permitted")
    if parser.script_count:
        errors.append("JavaScript is not permitted")
    if parser.form_count:
        errors.append("forms are not permitted")
    if parser.links != expected_links:
        errors.append("links differ from the exact approved route/mail/privacy set")
    if parser.embedded_count:
        errors.append("embedded assets or content are not permitted")
    if "@import" in lowered or "url(" in lowered:
        errors.append("external or referenced CSS assets are not permitted")
    identity_source = lowered
    if privacy:
        exact_paragraph = f"<p>{CONTROLLER_SENTENCE}</p>"
        if source.count(exact_paragraph) != 1:
            errors.append("exactly one approved controller paragraph is required on privacy")
        identity_source = identity_source.replace(exact_paragraph.lower(), "", 1)
    for marker in FORBIDDEN_SOURCE_MARKERS:
        if marker.lower() in identity_source:
            errors.append(f"forbidden claim or identity marker {marker}")
    for email in re.findall(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", unquote(public_text)):
        if email != "appportfolio.contact@gmail.com":
            errors.append("unapproved public mailbox")
    for reference in parser.resource_references:
        if reference not in expected_links:
            errors.append("unapproved resource reference")
    return errors


def run_self_test() -> int:
    source = (ROOT / "index.html").read_text(encoding="utf-8")
    mutations = (
        source.replace("<main ", '<main title="Ashraya&#32;Studio" '),
        source.replace("<main ", '<main title="%2541shraya" '),
        source.replace("<main ", '<main title="Kalpesh Patel" '),
        source.replace("<main ", '<main title="other%40gmail.com" '),
        source.replace(APPROVED_SUPPORT_LINK, "mailto:other@gmail.com?subject=Fondary%20support"),
        source.replace(APPROVED_SUPPORT_LINK, APPROVED_SUPPORT_LINK + "&amp;cc=other@gmail.com"),
        source.replace("appportfolio.contact@gmail.com", "appportfolio.contact+fondary@gmail.com"),
        source.replace("appportfolio.contact@gmail.com", "appportfoliocontact@gmail.com"),
        source.replace("appportfolio.contact@gmail.com", "appportfolio.contact@gmail.com.evil.example"),
        source.replace("Fondary</p>", "Ashraya</p>"),
        source.replace("</main>", "<p>Download on the App Store</p></main>"),
        source.replace("</main>", "<form></form></main>"),
        source.replace("</main>", "<script></script></main>"),
        source.replace("</main>", '<img src="https://example.invalid/pixel.png" alt=""></main>'),
        source.replace("</main>", '<a href="mailto:test@example.invalid">Contact</a></main>'),
        source.replace("<body>", '<body onload="alert(1)">'),
        source.replace("</head>", '<meta http-equiv="refresh" content="0;url=https://example.invalid"></head>'),
        source.replace('href="/privacy"', 'href="/privacy" ping="https://example.invalid"'),
        source.replace("</main>", '<p>The data controller is Kalpesh Patel.</p></main>'),
    )
    for number, mutation in enumerate(mutations, start=1):
        if not validate_source(mutation, PAGES[Path("index.html")]):
            print(f"self-test mutation {number} was not rejected", file=sys.stderr)
            return 1
    privacy = (ROOT / "privacy.html").read_text(encoding="utf-8")
    privacy_mutations = (
        privacy.replace(CONTROLLER_SENTENCE, "The data controller is Fondary."),
        privacy.replace(f"<p>{CONTROLLER_SENTENCE}</p>", ""),
        privacy.replace("</main>", f"<p>{CONTROLLER_SENTENCE}</p></main>"),
        privacy.replace("<main ", '<main title="Kalpesh Patel" '),
        privacy.replace("90 days", "365 days"),
        privacy.replace("Memories are stored locally by default.", "Memories are uploaded by default."),
        privacy.replace("private CloudKit database", "shared CloudKit database", 1),
        privacy.replace("Gmail", "another provider"),
        privacy.replace(GOOGLE_PRIVACY, "https://policies.google.com.evil.example/privacy"),
        privacy.replace(APPROVED_SUPPORT_LINK, APPROVED_SUPPORT_LINK + "&amp;body=private"),
        privacy.replace("</main>", '<iframe src="https://example.invalid"></iframe></main>'),
    )
    for number, mutation in enumerate(privacy_mutations, start=1):
        if not validate_source(mutation, PAGES[Path("privacy.html")]):
            print(f"privacy self-test mutation {number} was not rejected", file=sys.stderr)
            return 1
    for path, canonical in PAGES.items():
        if validate_source((ROOT / path).read_text(encoding="utf-8"), canonical):
            print(f"self-test approved page {path} was rejected", file=sys.stderr)
            return 1
    with tempfile.TemporaryDirectory(prefix="fondary-site-validator.") as temporary:
        root = Path(temporary)
        future = root / "future" / "nested.html"
        future.parent.mkdir(parents=True)
        future.write_text("<p>Future</p>", encoding="utf-8")
        if repository_html_paths(root) != [Path("future/nested.html")]:
            print("self-test did not discover a nested future HTML page", file=sys.stderr)
            return 1
    print(f"Fondary website self-test passed: {len(mutations) + len(privacy_mutations)} negative fixtures, 2 approved pages, future-page discovery.")
    return 0


def main() -> int:
    errors: list[str] = []
    for relative_path in repository_html_paths():
        if relative_path not in PAGES:
            errors.append(f"unregistered HTML page {relative_path}")
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
        for obsolete in (
            "/Users/hermes/.local/bin/hermes -z",
            "exclusive operator",
        ):
            if obsolete in agent_text:
                errors.append(f"AGENTS.md contains obsolete governance marker {obsolete}")

    if errors:
        print("Fondary website validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Fondary website validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_self_test() if "--self-test" in sys.argv[1:] else main())
