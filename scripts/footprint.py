#!/usr/bin/env python3
"""Estimate the per-visit footprint of the live site: data, energy, CO2e, water.

Measures every page in the sitemap the way a browser loads it (compressed
body + response headers, plus same-origin CSS/JS/icons), then applies the
Sustainable Web Design Model v4. Per-visit CO2e matches CO2.js v0.19
`new co2({ model: "swd", version: 4 }).perVisit(bytes, false)`.

The figures on /trasparenza/ and /en/transparency/ come from this script.

Usage: python3 scripts/footprint.py [--base-url https://openinnova.it]
Requires: python3, curl
"""

import argparse
import re
import subprocess

# --- Sustainable Web Design Model v4 ----------------------------------------
# https://sustainablewebdesign.org/estimating-digital-emissions/
# kWh per GB transferred: (operational, embodied)
KWH_PER_GB = {
    "data_center": (0.055, 0.012),
    "network": (0.059, 0.013),
    "device": (0.080, 0.081),
}
GRID_INTENSITY = 494  # gCO2e/kWh, global average used by SWDM v4
GB = 1e9  # decimal, as in CO2.js
# Upper bound per rating, gCO2e per page view
# https://sustainablewebdesign.org/digital-carbon-ratings/
RATINGS = [("A+", 0.040), ("A", 0.079), ("B", 0.145),
           ("C", 0.209), ("D", 0.278), ("E", 0.359)]

# --- Water --------------------------------------------------------------------
# Water Usage Effectiveness: litres per kWh of data-center energy
WUE = {
    "industry average": 1.8,
    "AWS Europe 2025": 0.05,  # AWS Italy sustainability fact sheet
}

PETROL_CAR_G_PER_KM = 120
BOTTLE_ML = 500

RESOURCE_RE = re.compile(
    r'<link[^>]+rel="(?:stylesheet|icon)"[^>]*href="([^"]+)"'
    r'|<script[^>]+src="([^"]+)"'
    r'|<img[^>]+src="([^"]+)"'
)


def fetch_text(url):
    out = subprocess.run(["curl", "-sSf", "--compressed", url],
                         capture_output=True, check=True)
    return out.stdout.decode()


def measure(url):
    """Bytes on the wire for one response: (body, headers, cache-control)."""
    out = subprocess.run(
        ["curl", "-sSf", "-H", "Accept-Encoding: br, gzip", "-o", "/dev/null",
         "-D", "-", "-w", "\n%{size_download} %{size_header}", url],
        capture_output=True, check=True, text=True,
    ).stdout
    headers, sizes = out.rsplit("\n", 1)
    body, header = map(int, sizes.split())
    cache = re.search(r"(?im)^cache-control:\s*(.+?)\s*$", headers)
    return body, header, cache.group(1) if cache else ""


def sitemap_pages(base):
    urls = re.findall(r"<loc>([^<]+)</loc>", fetch_text(base + "/sitemap.xml"))
    pages = []
    for url in urls:
        if url.endswith(".xml"):
            pages += re.findall(r"<loc>([^<]+)</loc>", fetch_text(url))
        else:
            pages.append(url)
    return sorted(set(pages))


def subresources(html, base):
    found = set()
    for match in RESOURCE_RE.finditer(html):
        url = next(g for g in match.groups() if g)
        url = base + url if url.startswith("/") else url
        if url.startswith(base):
            found.add(url)
    return sorted(found)


def footprint(nbytes):
    gb = nbytes / GB
    kwh = gb * sum(op + em for op, em in KWH_PER_GB.values())
    kwh_dc = gb * KWH_PER_GB["data_center"][0]
    return {"wh": kwh * 1e3, "g": kwh * GRID_INTENSITY, "kwh_dc": kwh_dc}


def rating(grams):
    return next((name for name, limit in RATINGS if grams <= limit), "F")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default="https://openinnova.it")
    base = parser.parse_args().base_url.rstrip("/")

    assets = {}
    rows = []
    for page in sitemap_pages(base):
        body, header, _ = measure(page)
        first = next_page = body + header
        for url in subresources(fetch_text(page), base):
            if url not in assets:
                assets[url] = measure(url)
            a_body, a_header, cache = assets[url]
            first += a_body + a_header
            # Immutable assets come from cache; the rest is revalidated (304)
            if "immutable" not in cache:
                next_page += a_header
        rows.append((page.removeprefix(base) or "/", first, next_page))

    print(f"{'page':<28}{'first visit':>14}{'next page':>12}  (bytes)")
    for path, first, next_page in rows:
        print(f"{path:<28}{first:>14}{next_page:>12}")

    avg_first = sum(r[1] for r in rows) / len(rows)
    max_first = max(r[1] for r in rows)
    avg_next = sum(r[2] for r in rows) / len(rows)
    avg = footprint(avg_first)
    heaviest = footprint(max_first)

    print(f"\nFirst visit, average : {avg_first / 1e3:.1f} KB "
          f"(heaviest page {max_first / 1e3:.1f} KB)")
    print(f"Next page, average   : {avg_next / 1e3:.1f} KB")
    print(f"Energy per visit     : {avg['wh']:.4f} Wh "
          f"(heaviest {heaviest['wh']:.4f} Wh)")
    print(f"CO2e per visit       : {avg['g']:.4f} g "
          f"(heaviest {heaviest['g']:.4f} g), rating {rating(heaviest['g'])}")
    print(f"1M visits            : {avg['g'] * 1e3:.2f} kg CO2e = "
          f"{avg['g'] * 1e6 / PETROL_CAR_G_PER_KM:.1f} km by petrol car")
    for label, wue in WUE.items():
        ml = avg["kwh_dc"] * wue * 1e3
        print(f"Water @ {wue} L/kWh ({label}): {ml:.5f} mL per visit, "
              f"{BOTTLE_ML / ml:,.0f} visits per {BOTTLE_ML} mL")


if __name__ == "__main__":
    main()
