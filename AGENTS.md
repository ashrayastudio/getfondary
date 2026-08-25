# Fondary Website — Agent Instructions

## Scope and fail-closed rule

This repository is the local static source lead for `getfondary.com`. It is not
evidence that GitHub, GitHub Pages, hosting, DNS, TLS, redirects, public
content, Apple, account, submission, or release state changed.

Nothing is committed, pushed, deployed, published, or represented as current
public evidence unless every applicable gate has current `PASS` evidence.
Missing, stale, conflicting, or `UNKNOWN` evidence keeps the action `BLOCKED`.

## Governing identity and content contract

- `Fondary` is the product name; Recall-to-Fondary is completed history and
  D-016 is not another product rename.
- Ashraya Studio is not approved as provider, operator, seller, or owner.
- The founder's legal name is omitted by default and may appear only when a
  current exact-surface requirement and founder decision support it.
- The `ashrayastudio` GitHub owner, repository URL, contact-domain leads, and
  other established identifiers are technical/contact infrastructure, not
  public legal-operator evidence.
- Until exact product/privacy/commerce/publication gates pass, the authorized
  local package is neutral: only the Fondary product name and the statement
  that product information is being updated. No feature, price, availability,
  App Store, privacy-behavior, operator, collection, contact, or commerce claim
  may be added by assumption.

The central governing source is
`/Users/hermes/Developer/personal-digital-products-ops`, especially D-016,
D-027, and MIG-005/MIG-006 in `docs/DECISION-LOG.md`, `docs/CURRENT-STATE.md`, and
`docs/PUBLIC-SURFACE-CORRECTION-PLAN.md`.

## Responsibility routing

- Codex owns exactly authorized local source/docs edits, local validators,
  diffs, and read-only local Git inspection.
- Hermes is the designated and exclusive operator for every GitHub network
  operation for `ashrayastudio/getfondary` at
  `https://github.com/ashrayastudio/getfondary.git`.
- For ordinary Git data, Hermes must use the existing authenticated Git HTTPS
  path through `/Users/hermes/.local/bin/hermes -z`; Codex must not fall back
  to direct `gh`, API, browser, SSH, or networked Git.
- Every Hermes request must name the exact repository/URL, Git HTTPS transport,
  read-only or mutation class, exact permitted operation, prohibited
  operations, and required sanitized before/after evidence.
- The founder alone authorizes commits, GitHub mutations, deployment,
  publication, DNS/hosting/certificate/redirect changes, Apple/account work,
  legal attestations, submission, and release. Hermes supplies operation, not
  authorization.

## Local validation and mutation boundaries

Run both before proposing a commit:

```text
python3 -B validate_site.py
python3 -B validate_site.py --self-test
```

Also require a reviewed exact diff, `git diff --check HEAD`, a clean index, a
scoped sensitive-pattern scan, and preservation of all unrelated owner work.
Local source, a Git commit, a Hermes push, Pages/hosting configuration, DNS/TLS
repair, and the published result are separate states and require separate
evidence and authority. Never access protected credential/configuration paths
or place credentials, protected contact values, financial records, or account
secrets in this repository.
