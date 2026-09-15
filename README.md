# Fondary website

Static website for [getfondary.com](https://getfondary.com), hosted with GitHub Pages.

The site has no backend, analytics, advertising, tracking, forms, cookies, or remote runtime dependencies. It uses Fondary’s approved app icon, current development screenshots, and locally hosted brand fonts.

## Pages

- `/` — pre-release product overview
- `/privacy` — full privacy policy
- `/support/` — support and common questions
- `/terms/` — Apple Standard EULA information

## Local validation

```sh
python3 -B validate_site.py
python3 -B validate_site.py --self-test
```

Passing local validation does not prove that a commit was created, pushed, built by GitHub Pages, or published.
