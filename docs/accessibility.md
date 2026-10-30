# Accessibility

Target: **WCAG 2.2 level AA** (the level referenced by EN 301 549 and the European Accessibility Act), on every page, in both languages, in light and dark mode.

## Automated gate

`scripts/deploy.sh` runs [`scripts/a11y_check.py`](../scripts/a11y_check.py) on the fresh build and **aborts the deploy** if anything fails (it also creates `.venv` with the tooling the first time). Run it yourself before deploying:

```bash
# once: Playwright + axe-core, dev only, nothing is shipped
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt

hugo && .venv/bin/python scripts/a11y_check.py
```

It drives the Google Chrome already installed on the machine (no browser download). Every page is opened in headless Chrome and checked for:

| Check | Conditions | WCAG |
|---|---|---|
| axe-core rules (WCAG 2.0/2.1/2.2 A+AA + best practices) | desktop and mobile, light and dark | most of 1.x–4.x |
| Mobile menu and cookie dialog, opened with the keyboard: axe rules, focus starts inside and stays out of the page behind, Escape closes | mobile, light and dark | 2.1.1, 2.1.2, 2.4.3 |
| Every Tab stop is visible, not covered by the sticky header or fixed buttons, and has a focus indicator with ≥3:1 contrast | desktop, light and dark | 2.4.7, 2.4.11, 1.4.11 |
| No horizontal scrolling at 320 CSS px | 320×640 | 1.4.10 |

`SKIP_A11Y=1 ./scripts/deploy.sh` exists only for emergencies, and asks for confirmation.

## What automation cannot judge

Before publishing new or changed content, check these by hand:

- **Link text** makes sense out of context ("Scopri GestiSCU", not "clicca qui").
- **Headings** follow the outline: one `h1` (page title or hero), then `##`/`###` in Markdown without skipping levels.
- **Images** (none today): meaningful `alt`, or `alt=""` if decorative. Charts need the same data in text, as the footprint shortcode does.
- **Forms**: every field has a visible `<label for>`; required fields use `required` and are explained in the text above the form.
- **Language**: text in another language inside a page gets `lang` (`<span lang="en">…</span>`), except names and common loanwords.
- **Plain language**: short sentences, no unexplained jargon (see the brand voice).
- **Screen reader pass** on changed templates: VoiceOver (macOS ⌘F5, iOS) — landmarks, headings rotor, menu and dialogs.
- **Zoom** to 200% and 400% in the browser: nothing cut off or overlapping.

## Rules for templates and CSS

- Colours: use the tokens in `assets/css/style.css`. Text needs 4.5:1 (3:1 for ≥24px or ≥18.66px bold), UI boundaries and icons 3:1. White text goes only on `--color-fill-green`/`--color-fill-green-strong`, never on `--color-secondary` (which is lighter in dark mode). Green text on `--color-primary-light` uses `--color-on-tint`.
- Focus: rings use `--color-focus`, which follows the colour scheme. A section with a dark background in light mode must override it to white. Never `outline: none` without a replacement indicator.
- Floating buttons (cookie badge, back to top): `html` has a `scroll-padding-bottom` as tall as them, so a focused element is never scrolled underneath (2.4.11, technique C43). Below 80.5rem, where there is no empty side margin, the cookie badge hides while scrolling down. It is also hidden while the footer, which has the same button, is in view.
- Table of contents: a `<details>` closed in the HTML (no layout shift on small screens), opened as a sticky sidebar by `scripts.js` from 68.75rem. The current section gets `aria-current` and is marked with a bar and bold, not colour alone.
- Links in running text stay underlined; colour alone is not enough (1.4.1).
- Do not use ARIA menu roles (`menubar`, `menu`, `menuitem`) for site navigation: they promise arrow-key behaviour the site does not have.
- Hidden interactive elements must also be `visibility: hidden` (or `hidden`/`inert`), not just `opacity: 0`.
- Motion: animate only inside `prefers-reduced-motion: no-preference`, or keep it subtle; the global reduced-motion rule neutralises transitions.
- Modals: native `<dialog>` with `showModal()` (focus trap, Escape and focus return come for free).

## Accessibility statement

Published at `/accessibilita/` and `/en/accessibility/` (content files `accessibilita.md` / `accessibility.md`); the footer link appears only when the page is not a draft. Review it at least once a year and after significant changes: update the date, the conformance status and the known limitations, in both languages.

Legal position (checked 30 October 2026, to re-check if the company changes):

- **EAA / D.Lgs. 82/2022**: not applicable. The site is not one of the services in scope (no e-commerce contracts with consumers), and micro-enterprises (<10 people and turnover or balance sheet ≤ €2M) are exempt for services.
- **Legge 4/2004 (Stanca)**: art. 3 c. 1-bis applies only above €500M average turnover. Art. 3 c. 1 also covers private companies that receive **public contributions or incentives to deliver their services online**: if that ever happens, the statement becomes mandatory (AgID form, every year by 23 September).

## References

- [WCAG 2.2](https://www.w3.org/TR/WCAG22/) and [Understanding WCAG 2.2](https://www.w3.org/WAI/WCAG22/Understanding/)
- [WAI-ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [axe-core rules](https://dequeuniversity.com/rules/axe/)
- [AgID – Linee guida sull'accessibilità degli strumenti informatici](https://www.agid.gov.it/it/design-servizi/accessibilita)
