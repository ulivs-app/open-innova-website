#!/usr/bin/env python3
"""Estimate the per-visit footprint of the live site: data, energy, CO2e, water.

Measures compressed responses and directly referenced same-origin page assets.
Applies Sustainable Web Design Model v4 coefficients to cold-load bytes, without
a green-hosting discount or a blended new/returning-visitor ratio. This is not
a complete browser trace. Warm-cache transfers and cooling water are scenarios.

The figures on /trasparenza/ and /en/transparency/ come from this script.

Usage: python3 scripts/footprint.py [--base-url https://openinnova.it]
Export charts: --json-output data/footprint.json --version-label RELEASE
Requires: python3, curl
"""

import argparse
import datetime
import hashlib
import json
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
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
    "illustrative scenario": 1.8,
    "AWS Europe 2025": 0.05,  # AWS Italy sustainability fact sheet
}

PETROL_CAR_G_PER_KM = 120
BOTTLE_ML = 500



def fetch_text(url):
    out = subprocess.run(["curl", "-sSf", "--max-time", "30", "--compressed", url],
                         capture_output=True, check=True)
    return out.stdout.decode()


def measure(url):
    """Bytes on the wire for one response: (body, headers, cache-control)."""
    out = subprocess.run(
        ["curl", "-sSf", "--max-time", "30", "-H", "Accept-Encoding: br, gzip", "-o", "/dev/null",
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
    """Collect page assets independently of HTML attribute order, same origin only."""
    class Assets(HTMLParser):
        def __init__(self):
            super().__init__()
            self.urls = set()

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            url = None
            if tag == "link" and set(attrs.get("rel", "").split()) & {"stylesheet", "icon"}:
                url = attrs.get("href")
            elif tag in {"script", "img"}:
                url = attrs.get("src")
            if url:
                absolute = urljoin(base.rstrip("/") + "/", url)
                if urlparse(absolute).netloc == urlparse(base).netloc:
                    self.urls.add(absolute)

    parser = Assets()
    parser.feed(html)
    return sorted(parser.urls)


def report_data(rows, base, version, page_hashes):
    if not rows:
        raise ValueError("The sitemap contains no pages")
    avg_first = sum(row[1] for row in rows) / len(rows)
    avg_next = sum(row[2] for row in rows) / len(rows)
    total_intensity = sum(sum(v) for v in KWH_PER_GB.values())
    return {
        "schema_version": 1,
        "measured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "base_url": base,
        "version_label": version,
        "page_count": len(rows),
        "model": "Sustainable Web Design Model v4",
        "grid_g_co2e_per_kwh": GRID_INTENSITY,
        "energy_kwh_per_gb": KWH_PER_GB,
        "first_bytes": avg_first,
        "next_bytes": avg_next,
        "heaviest_bytes": max(row[1] for row in rows),
        "first": footprint(avg_first),
        "next": footprint(avg_next),
        "segments": [
            {"id": key, "percent": sum(value) / total_intensity * 100}
            for key, value in KWH_PER_GB.items()
        ],
        "water": [
            {"id": "scenario" if index == 0 else "aws_europe_2025",
             "wue_l_per_kwh": wue,
             "ml_per_load": footprint(avg_first)["kwh_dc"] * wue * 1000,
             "loads_per_500ml": 500 / (footprint(avg_first)["kwh_dc"] * wue * 1000)}
            for index, wue in enumerate(WUE.values())
        ],
        "pages": [{"path": p, "first_bytes": f, "next_bytes": n} for p, f, n in rows],
        "page_sha256": page_hashes,
        "assumptions": [
            "Unweighted arithmetic mean across sitemap pages; not actual visitor traffic.",
            "Response body and headers; HTML, same-origin CSS, JS, icons and img src. Not a complete browser/network trace.",
            "Warm cache assumes all page assets already stored; immutable assets fresh, other cacheable assets revalidated with response-header size as a proxy.",
            "No green hosting discount; operational and embodied model energy included.",
            "Scaling by page loads uses fixed coefficients: attribution only, not a measured or marginal consumption curve.",
            "Water scenarios apply WUE to modelled operational data-centre energy, an approximate allocation, not a measurement of this site's cooling water.",
            "Water excludes electricity generation, hardware manufacturing, network and visitor-device water footprints.",
            "AWS Europe 2025 WUE is a regional annual average, not the WUE of a specific CloudFront node."
        ],
        "sources": {
            "model": "https://sustainablewebdesign.org/estimating-digital-emissions/",
            "aws_wue": "https://sustainability.aboutamazon.com/aws-sustainability-fact-sheets/aws-fact-sheet-italy.pdf"
        }
    }


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
    parser.add_argument("--json-output", type=Path, help="Export data for Hugo charts")
    parser.add_argument("--version-label", default="published-site", help="Identity of the measured release")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    assets = {}
    rows = []
    page_hashes = {}
    for page in sitemap_pages(base):
        body, header, _ = measure(page)
        first = next_page = body + header
        html = fetch_text(page)
        page_hashes[page.removeprefix(base) or "/"] = hashlib.sha256(html.encode()).hexdigest()
        for url in subresources(html, base):
            if url not in assets:
                assets[url] = measure(url)
            a_body, a_header, cache = assets[url]
            first += a_body + a_header
            # Immutable assets come from cache; the rest is revalidated (304)
            if "no-store" in cache:
                next_page += a_body + a_header
            elif "immutable" not in cache:
                next_page += a_header
        rows.append((page.removeprefix(base) or "/", first, next_page))

    report = report_data(rows, base, args.version_label, page_hashes)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(report, indent=2) + "\n")

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
