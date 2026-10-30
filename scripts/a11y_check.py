#!/usr/bin/env python3
"""Accessibility gate for the built site (WCAG 2.2 AA).

Serves the Hugo output folder locally, opens every page in headless Chrome and
checks it in several conditions:
  - axe-core rules (WCAG 2.0/2.1/2.2 A+AA + best practices), light and dark
    colour scheme, desktop and mobile viewport, plus the open dialogs
    (mobile menu, cookie modal) opened with the keyboard;
  - keyboard: every Tab stop must be visible, have a focus indicator with at
    least 3:1 contrast, and not be hidden behind sticky/fixed elements;
  - reflow: no horizontal scrolling at 320 CSS px (WCAG 1.4.10).

deploy.sh runs it on public/ and stops the deploy if anything fails.

Usage: python3 scripts/a11y_check.py [public-dir]
Requires: pip install -r requirements-dev.txt, Google Chrome
Exit: 0 = no violations, 1 = violations found, 2 = setup error
"""

import argparse
import functools
import http.server
import importlib.resources
from pathlib import Path
import re
import sys
import threading

try:
    from playwright.sync_api import Error as PlaywrightError, sync_playwright
except ImportError:
    sys.exit("[a11y] Playwright missing: pip install -r requirements-dev.txt")

AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22a", "wcag22aa", "best-practice"]
DESKTOP = {"viewport": {"width": 1280, "height": 800}}
MOBILE = {"viewport": {"width": 375, "height": 740}, "is_mobile": True, "has_touch": True}
REFLOW = {"viewport": {"width": 320, "height": 640}}
DIALOGS = [("[data-open-nav-menu]", "#nav-menu"), ("[data-open-cookie-modal]", "#cookie-modal")]
MAX_TAB_STOPS = 250
MIN_FOCUS_CONTRAST = 3

# Freeze transitions so styles are read in their final focused state
FREEZE_CSS = "*,*::before,*::after{transition:none!important;animation:none!important;scroll-behavior:auto!important}"

# Helpers installed in the page for the keyboard checks (window.__a11y).
PAGE_HELPERS = r"""
(() => {
  const parse = (str) => {
    const m = /rgba?\(([^)]+)\)/.exec(str || '');
    if (!m) return null;
    const p = m[1].split(/[\s,/]+/).filter(Boolean).map(Number);
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  };
  const over = (top, bottom) => {
    const a = top.a + bottom.a * (1 - top.a);
    if (a === 0) return { r: 0, g: 0, b: 0, a: 0 };
    const mix = (k) => (top[k] * top.a + bottom[k] * bottom.a * (1 - top.a)) / a;
    return { r: mix('r'), g: mix('g'), b: mix('b'), a };
  };
  const lum = (c) => {
    const ch = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
    return 0.2126 * ch(c.r) + 0.7152 * ch(c.g) + 0.0722 * ch(c.b);
  };
  const contrast = (a, b) => {
    const [l1, l2] = [lum(a), lum(b)].sort((x, y) => y - x);
    return (l1 + 0.05) / (l2 + 0.05);
  };
  // Every colour that may sit behind `el` (gradient stops count separately).
  const backdrops = (el) => {
    const layers = [];
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      const cs = getComputedStyle(n);
      const stops = (cs.backgroundImage.match(/rgba?\([^)]+\)/g) || []).map(parse);
      const bg = parse(cs.backgroundColor);
      if (stops.length) { layers.push(stops); break; }
      if (bg && bg.a > 0) {
        layers.push([bg]);
        if (bg.a >= 1) break;
      }
    }
    let result = [{ r: 255, g: 255, b: 255, a: 1 }];
    for (const layer of layers.reverse()) {
      result = layer.flatMap((c) => result.map((under) => over(c, under)));
    }
    return result;
  };
  const isVisible = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return false;
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      const cs = getComputedStyle(n);
      if (cs.visibility === 'hidden' || cs.display === 'none' || Number(cs.opacity) < 0.1) return false;
    }
    return true;
  };
  const unobscured = (el) => {
    const r = el.getBoundingClientRect();
    const pts = [[0.5, 0.5], [0.1, 0.1], [0.9, 0.1], [0.1, 0.9], [0.9, 0.9]];
    return pts.some(([x, y]) => {
      const hit = document.elementFromPoint(r.left + r.width * x, r.top + r.height * y);
      return hit && (hit === el || el.contains(hit) || hit.contains(el));
    });
  };
  const describe = (el) => {
    let s = el.tagName.toLowerCase();
    if (el.id) s += '#' + el.id;
    if (el.classList.length) s += '.' + [...el.classList].join('.');
    const text = (el.getAttribute('aria-label') || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40);
    return text ? `${s} "${text}"` : s;
  };
  const snapshot = (el) => {
    const cs = getComputedStyle(el);
    return {
      outlineStyle: cs.outlineStyle,
      outlineWidth: parseFloat(cs.outlineWidth) || 0,
      outlineColor: cs.outlineColor,
      boxShadow: cs.boxShadow,
      bg: cs.backgroundColor,
      color: cs.color,
      border: cs.borderColor + ' ' + cs.borderWidth,
      decoration: cs.textDecorationLine + ' ' + cs.textDecorationColor,
    };
  };

  // Evaluate the element that currently has focus.
  const assessFocus = (minContrast) => {
    const el = document.activeElement;
    if (!el || el === document.body) return { done: true };
    const key = describe(el) + '|' + (el.getAttribute('href') || '');
    if (!isVisible(el)) return { key, problem: 'receives keyboard focus while invisible' };
    if (!unobscured(el)) return { key, problem: 'focused element is hidden behind another element (sticky/fixed)' };

    const focused = snapshot(el);
    el.blur();
    const idle = snapshot(el);
    el.focus({ preventScroll: true });

    const behind = backdrops(el.parentElement || el);
    if (focused.outlineStyle !== 'none' && focused.outlineWidth >= 1) {
      const oc = parse(focused.outlineColor);
      const worst = Math.min(...behind.map((b) => contrast(oc, b)));
      if (worst < minContrast) {
        return { key, problem: `focus outline contrast ${worst.toFixed(2)}:1 against the background (needs ${minContrast}:1)` };
      }
      return { key };
    }
    if (focused.boxShadow !== idle.boxShadow && focused.boxShadow !== 'none') return { key };
    if (focused.border !== idle.border) return { key };
    if (focused.decoration !== idle.decoration) return { key };
    const a = parse(focused.bg), b = parse(idle.bg);
    if (a && b && focused.bg !== idle.bg) {
      const self = behind[0];
      const ratio = contrast(a.a < 1 ? self : a, b.a < 1 ? self : b);
      if (ratio >= minContrast) return { key };
      return { key, problem: `focus only changes the background (contrast ${ratio.toFixed(2)}:1, needs ${minContrast}:1)` };
    }
    if (focused.color !== idle.color) {
      const ratio = contrast(parse(focused.color), parse(idle.color));
      if (ratio >= minContrast) return { key };
      return { key, problem: `focus only changes the text colour (contrast ${ratio.toFixed(2)}:1, needs ${minContrast}:1)` };
    }
    return { key, problem: 'no visible focus indicator' };
  };

  // A native modal lets Tab move on to the browser UI (activeElement = body):
  // that is fine, reaching page content behind the dialog is not.
  const focusWhere = (selector) => {
    const d = document.querySelector(selector);
    if (d.contains(document.activeElement)) return 'inside';
    return document.activeElement === document.body ? 'browser' : 'page';
  };

  window.__a11y = { assessFocus, focusWhere };
})();
"""

RUN_AXE = """async ([tags, include]) => {
  const context = include ? { include: [include] } : document;
  const result = await window.axe.run(context, { runOnly: { type: 'tag', values: tags }, resultTypes: ['violations'] });
  return result.violations.map((v) => ({
    id: v.id, impact: v.impact, help: v.help, helpUrl: v.helpUrl,
    nodes: v.nodes.map((n) => n.target.join(' ')),
  }));
}"""

CHECK_REFLOW = """(width) => {
  const doc = document.scrollingElement;
  if (doc.scrollWidth <= width + 1) return [];
  const offenders = [...document.querySelectorAll('body *')]
    .filter((el) => el.getBoundingClientRect().right > width + 1 && getComputedStyle(el).position !== 'fixed')
    .filter((el, _, all) => !all.some((o) => o !== el && el.contains(o)))
    .slice(0, 5)
    .map((el) => el.tagName.toLowerCase() + (el.className ? '.' + String(el.className).trim().split(/\\s+/).join('.') : ''));
  return [`page is ${doc.scrollWidth}px wide at ${width}px viewport (horizontal scroll). Widest: ${offenders.join(', ')}`];
}"""


def axe_source():
    """axe-core as bundled by the axe-playwright-python package."""
    return importlib.resources.files("axe_playwright_python").joinpath("axe.min.js").read_text()


def list_pages(root):
    pages = []
    for path in sorted(root.rglob("*.html")):
        # Skip Hugo alias pages (meta refresh redirects with no content)
        if re.search(r'<meta http-equiv="?refresh', path.read_text(errors="ignore"), re.I):
            continue
        rel = path.relative_to(root).as_posix()
        pages.append("/" + re.sub(r"(^|/)index\.html$", r"\1", rel))
    return pages


class SiteHandler(http.server.SimpleHTTPRequestHandler):
    """Static server that answers missing paths with the site's 404 page."""

    def send_error(self, code, message=None, explain=None):
        page = Path(self.directory) / "404.html"
        if code != 404 or not page.exists():
            return super().send_error(code, message, explain)
        body = page.read_bytes()
        self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def start_server(root):
    handler = functools.partial(SiteHandler, directory=str(root))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class Checker:
    def __init__(self, browser, base, axe):
        self.browser = browser
        self.base = base
        self.axe = axe
        self.failures = []  # (path, context, message)

    def add(self, path, context, items):
        self.failures.extend((path, context, item) for item in items)

    def open(self, path, device, scheme):
        # The site's CSP would block the injected axe script
        context = self.browser.new_context(bypass_csp=True, color_scheme=scheme, **device)
        page = context.new_page()
        page.goto(self.base + path, wait_until="load")
        return page

    def run_axe(self, page, include=None):
        if not page.evaluate("typeof window.axe !== 'undefined'"):
            page.add_script_tag(content=self.axe)
        items = []
        for v in page.evaluate(RUN_AXE, [AXE_TAGS, include]):
            lines = [f"[{v['impact']}] {v['id']}: {v['help']}", f"    {v['helpUrl']}"]
            lines += [f"    → {target}" for target in v["nodes"][:5]]
            if len(v["nodes"]) > 5:
                lines.append(f"    … and {len(v['nodes']) - 5} more")
            items.append("\n    ".join(lines))
        return items

    def prepare_keyboard(self, page):
        if page.evaluate("Boolean(window.__a11y)"):
            return
        page.add_style_tag(content=FREEZE_CSS)
        page.evaluate(PAGE_HELPERS)

    def check_keyboard(self, page):
        self.prepare_keyboard(page)
        problems, seen = [], set()
        for _ in range(MAX_TAB_STOPS):
            page.keyboard.press("Tab")
            r = page.evaluate("(min) => window.__a11y.assessFocus(min)", MIN_FOCUS_CONTRAST)
            if r.get("done") or r["key"] in seen:
                break
            seen.add(r["key"])
            if r.get("problem"):
                problems.append(f"{r['key']}: {r['problem']}")
        return problems

    def check_dialog_keyboard(self, page, dialog):
        """Inside an open modal: focus must start in the dialog, stay there, and be visible."""
        self.prepare_keyboard(page)
        problems, seen = [], set()
        for i in range(MAX_TAB_STOPS):
            where = page.evaluate("(sel) => window.__a11y.focusWhere(sel)", dialog)
            if where == "browser" and i > 0:
                break
            if where != "inside":
                problems.append(f"focus {'reaches the page behind' if i else 'does not start inside'} the open dialog")
                break
            r = page.evaluate("(min) => window.__a11y.assessFocus(min)", MIN_FOCUS_CONTRAST)
            if r.get("done") or r["key"] in seen:
                break
            seen.add(r["key"])
            if r.get("problem"):
                problems.append(f"{r['key']}: {r['problem']}")
            page.keyboard.press("Tab")
        return problems

    def check_dialogs(self, page, path, scheme):
        for opener, dialog in DIALOGS:
            if not page.query_selector(opener):
                continue
            context = f"mobile/{scheme} {dialog}"
            # Open with the keyboard, as a keyboard user would
            page.focus(opener)
            page.keyboard.press("Enter")
            if not page.eval_on_selector(dialog, "d => d.open"):
                self.add(path, context, [f"{opener} does not open {dialog}"])
                continue
            self.add(path, context, self.run_axe(page, dialog))
            self.add(path, context + " keyboard", self.check_dialog_keyboard(page, dialog))
            page.keyboard.press("Escape")
            if page.eval_on_selector(dialog, "d => d.open"):
                self.add(path, context, [f"Escape does not close {dialog}"])

    def check_page(self, path):
        for scheme in ("light", "dark"):
            page = self.open(path, DESKTOP, scheme)
            self.add(path, f"desktop/{scheme}", self.run_axe(page))
            self.add(path, f"desktop/{scheme} keyboard", self.check_keyboard(page))
            page.context.close()

            page = self.open(path, MOBILE, scheme)
            self.add(path, f"mobile/{scheme}", self.run_axe(page))
            self.check_dialogs(page, path, scheme)
            page.context.close()

        page = self.open(path, REFLOW, "light")
        self.add(path, "reflow 320px", page.evaluate(CHECK_REFLOW, REFLOW["viewport"]["width"]))
        page.context.close()


def report(failures, page_count):
    if not failures:
        print(f"[a11y] OK: no violations on {page_count} pages.")
        return 0
    current = None
    for path, context, item in failures:
        head = f"{path} ({context})"
        if head != current:
            print(f"\n{head}")
            current = head
        print(f"  - {item}")
    print(f"\n[a11y] FAILED: {len(failures)} problems. Fix them before deploying.")
    return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", nargs="?", default="public", help="built site folder (default: public)")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"[a11y] {root} not found: build the site first (hugo).", file=sys.stderr)
        return 2
    try:
        axe = axe_source()
    except ModuleNotFoundError:
        print("[a11y] axe-core missing: pip install -r requirements-dev.txt", file=sys.stderr)
        return 2

    pages = list_pages(root)
    server = start_server(root)
    base = f"http://127.0.0.1:{server.server_address[1]}"
    print(f"[a11y] Checking {len(pages)} pages from {args.root} (WCAG 2.2 AA)…")
    try:
        with sync_playwright() as pw:
            try:
                # The Chrome installed on the machine: no browser download needed
                browser = pw.chromium.launch(channel="chrome")
            except PlaywrightError:
                print("[a11y] Google Chrome not found. Install it from https://www.google.com/chrome/", file=sys.stderr)
                return 2
            checker = Checker(browser, base, axe)
            for path in pages:
                checker.check_page(path)
                print(".", end="", flush=True)
            print()
            browser.close()
    finally:
        server.shutdown()
    return report(checker.failures, len(pages))


if __name__ == "__main__":
    sys.exit(main())
