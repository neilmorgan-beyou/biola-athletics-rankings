#!/usr/bin/env python3
"""Archive the NCAA's published Division II regional rankings (NPI-based from 2026-27) from NCAA.com.

Usage: python3 ncaa_regional.py [--today YYYY-MM-DD] [--test-season]

Reads only the published page https://www.ncaa.com/rankings/<sport>/d2/regional-rankings (never the
stats.ncaa.org nitty gritties; Neil, 2026-10-06). The page is replaced in place each week and usually
carries a sport only for the last three weeks or so of its regular season; between seasons it keeps
showing last season's final release, which is ignored.

For each release not seen before (keyed by sport + the page's datePublished):
  - the whole table is appended to polls/ncaa-regional.json (append-only snapshots);
  - Biola's row, if Biola is ranked in its region, is appended to data/current-season.json, which the
    page builder and recap_context.py already read (scope "regional", region "West").
Prints one line per sport. A page that cannot be read prints "NEEDS-MANUAL <url>" for the routine to
report; it never stops the refresh.
--test-season accepts any season (to test the parser on last season's pages); it writes nothing.
"""
import html
import json
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).parent
ARCHIVE = HERE / "polls" / "ncaa-regional.json"
CURRENT = HERE / "data" / "current-season.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
PAGE = "https://www.ncaa.com/rankings/%s/d2/regional-rankings"

# NCAA.com slug -> (sport name in this repo, season kind)
SPORTS = {
    "volleyball-women": ("Women's Volleyball", "fall"),
    "soccer-men": ("Men's Soccer", "fall"),
    "soccer-women": ("Women's Soccer", "fall"),
    "basketball-men": ("Men's Basketball", "winter"),
    "basketball-women": ("Women's Basketball", "winter"),
    "baseball": ("Baseball", "spring"),
    "softball": ("Softball", "spring"),
}
MON = ["Jan.", "Feb.", "March", "April", "May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."]


def season_window(kind, today):
    """(season label, first and last date a current-season release can be 'through')."""
    a = today.year if today.month >= 7 else today.year - 1  # academic year start
    if kind == "fall":
        return str(a), date(a, 8, 1), date(a + 1, 1, 31)
    if kind == "winter":
        return "%d-%02d" % (a, (a + 1) % 100), date(a, 10, 15), date(a + 1, 4, 15)
    return str(a + 1), date(a + 1, 1, 15), date(a + 1, 6, 30)


def fetch(url):
    r = subprocess.run(["curl", "-s", "--compressed", "-A", UA, "-w", "\n%{http_code}", url],
                       capture_output=True, text=True, timeout=60)
    body, _, code = r.stdout.rpartition("\n")
    return (body if code == "200" else None), code


def text(cell):
    return html.unescape(re.sub(r"<[^>]+>", "", cell)).strip()


def parse(page):
    pub = re.search(r'"datePublished":"([0-9T:\-+]+)"', page)
    thr = re.search(r'rankings-last-updated">\s*Through Games\s*([A-Z]{3})\.?\s+(\d+),\s*(\d{4})', page)
    tab = re.search(r"<table.*?</table>", page, re.S)
    if not (pub and thr and tab):
        return None
    through = datetime.strptime("%s %s %s" % (thr.group(1).title(), thr.group(2), thr.group(3)), "%b %d %Y").date()
    heads = [re.sub(r"\s+", " ", text(h)).upper() for h in re.findall(r"<th[^>]*>(.*?)</th>", tab.group(0), re.S)]
    regions, region, cols = {}, None, heads[2:]
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", tab.group(0), re.S):
        cells = [text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if not cells or not any(cells):
            continue
        if cells[0] and not cells[0].isdigit():
            # A region row. Some pages repeat column names in it, in their own order; use those.
            region = cells[0].title()
            regions[region] = []
            if any(cells[2:]):
                cols = [re.sub(r"\s+", " ", c).upper() for c in cells[2:]]
        elif cells[0].isdigit() and region:
            regions[region].append({"rank": int(cells[0]), "team_raw": cells[1],
                                    "cells": {k: c for k, c in zip(cols, cells[2:]) if k and c}})
    if not regions:
        return None
    return {"release_date": pub.group(1)[:10], "through": through.isoformat(), "columns": [h for h in heads if h],
            "regions": regions}


def main():
    today = date.fromisoformat(sys.argv[sys.argv.index("--today") + 1]) if "--today" in sys.argv else date.today()
    test = "--test-season" in sys.argv
    arch = json.loads(ARCHIVE.read_text()) if ARCHIVE.exists() else {
        "about": "NCAA.com Division II regional rankings, one snapshot per release (append-only). Written by ncaa_regional.py.",
        "snapshots": []}
    cur = json.loads(CURRENT.read_text()) if CURRENT.exists() else {"rows": []}
    seen = {(s["sport"], s["release_date"]) for s in arch["snapshots"]}
    changed = False
    for slug, (sport, kind) in SPORTS.items():
        url = PAGE % slug
        season, lo, hi = season_window(kind, today)
        in_window = lo <= today <= hi
        page, code = fetch(url)
        snap = parse(page) if page else None
        if not snap:
            print("%s: %s %s" % (sport, "NEEDS-MANUAL" if in_window else "unreadable (out of season)", url)
                  + ("" if page else " (HTTP %s)" % code))
            continue
        thr = date.fromisoformat(snap["through"])
        if not test and not (lo <= thr <= hi):
            print("%s: page still shows an earlier season (through %s); nothing new" % (sport, snap["through"]))
            continue
        if (sport, snap["release_date"]) in seen:
            print("%s: release of %s already archived" % (sport, snap["release_date"]))
            continue
        biola = [(reg, t) for reg, ts in snap["regions"].items() for t in ts if t["team_raw"].strip() == "Biola"]
        print("%s: NEW release %s (through %s), %d regions, Biola %s" % (
            sport, snap["release_date"], snap["through"], len(snap["regions"]),
            ("No. %d %s" % (biola[0][1]["rank"], biola[0][0])) if biola else "not ranked"))
        if test:
            continue
        snap.update({"sport": sport, "season": season, "source_url": url,
                     "basis": "NPI" if lo.year - (1 if kind == "spring" else 0) >= 2026 else "regional advisory committee"})
        arch["snapshots"].append(snap)
        for reg, t in biola:
            d = date.fromisoformat(snap["through"])
            c = t["cells"]
            cur["rows"].append({
                "season": season, "era": "NCAA DII",
                "poll": "NCAA DII Regional Rankings (NPI)" if snap["basis"] == "NPI" else "NCAA DII Regional Rankings",
                "scope": "regional", "region": reg,
                "week": "Through games %s %d" % (MON[d.month - 1], d.day),
                "date": snap["release_date"],
                "record_at_time": next((v for k, v in c.items() if "IN-REGION" not in k and "RECORD" in k), None),
                "confidence": "primary", "sport": sport, "rank": str(t["rank"]), "points": None,
                "source_url": url,
                "notes": "Published on NCAA.com %s (datePublished), through games %s. In-region record %s. Read by ncaa_regional.py."
                         % (snap["release_date"], snap["through"], next((v for k, v in c.items() if "IN-REGION" in k), "n/a"))})
        changed = True
    if changed:
        ARCHIVE.write_text(json.dumps(arch, indent=1, ensure_ascii=False) + "\n")
        CURRENT.write_text(json.dumps(cur, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
