#!/usr/bin/env python3
"""Official NCAA Division II NPI (NCAA Power Index) releases, one record per sport and release.

Usage:
  python3 npi.py add CAPTURE.json    check a capture and append it to npi/releases.json
  python3 npi.py check               re-check every stored release (also run by the builder on load)
  python3 npi.py due [--today D]     print official release dates 1-7 days before D not yet recorded

From 2026-27 the NPI is the sole DII selection metric. NCAA.com's /d2/npi-rankings page only links to
stats.ncaa.org, which blocks scripts and whose terms bar scraping, so every release is read by hand:
Claude, in Neil's Chrome, at Neil's request (Neil accepted the stats.ncaa.org terms himself, 2026-10-12).

Each record keeps the three things Neil asked for (2026-10-12), separately and unrounded:
  national_rank / teams_nationally   Biola's national NPI rank, e.g. 82 of 259
  npi                                the NPI value exactly as printed, e.g. "53.280"
  region_rank / region_teams         Biola's place among its region's teams by NPI rank, e.g. 11 of 32
plus "official": true with "official_basis" (decided once, at `add`: the release date is on the official
schedule and NCAA.com's NPI page links to it), Biola's source row as printed, and the whole region's
standings, so the region rank can be re-derived and checked.
These are positions in a ranking of every team, not poll rankings: the page lists them in their own
table and never counts them as "ranked".
"""
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
FILE = HERE / "npi" / "releases.json"


def _days(a, b):
    a, b = date.fromisoformat(a), date.fromisoformat(b)
    return [(a + timedelta(n)).isoformat() for n in range((b - a).days + 1)]


# Official release dates from the 2026-27 prechampionships manuals (links and quotes in npi/manuals.json; checked
# 2026-10-12): Mondays from four weeks before selections, then daily for the last two weeks. Volleyball and women's
# soccer list the daily dates; men's soccer lists Oct. 12/19/26 and states the two-week daily rule. Neither soccer
# manual says whether selection day (Nov. 9) itself has a release; it is kept here. Other Biola NPI sports
# (basketball, baseball, softball, tennis) are added when their manuals publish (npi/manuals.json).
SCHEDULE = {
    "Women's Soccer": ["2026-10-12", "2026-10-19"] + _days("2026-10-26", "2026-11-09"),
    "Men's Soccer": ["2026-10-12", "2026-10-19"] + _days("2026-10-26", "2026-11-09"),
    "Women's Volleyball": ["2026-10-19", "2026-10-26"] + _days("2026-11-02", "2026-11-15"),
}
# NCAA.com page that announces each sport's release (it links to the stats.ncaa.org table).
NCAA_COM = {
    "Women's Soccer": "https://www.ncaa.com/rankings/soccer-women/d2/npi-rankings",
    "Men's Soccer": "https://www.ncaa.com/rankings/soccer-men/d2/npi-rankings",
    "Women's Volleyball": "https://www.ncaa.com/rankings/volleyball-women/d2/npi-rankings",
}
REQUIRED = ("sport", "season", "release_date", "through", "official", "source_url", "ncaa_com_url",
            "teams_nationally", "national_rank", "npi", "region", "region_rank", "region_teams",
            "region_standings", "read")


def load():
    """Every stored release that passes check_one. A bad record is reported and skipped, never fatal:
    the page build and the QUILL feed must not stop over one record."""
    rel = json.loads(FILE.read_text())["releases"] if FILE.exists() else []
    good = []
    for r in rel:
        problems = check_one(r)
        if problems:
            print("WARNING npi/releases.json: skipped %s %s: %s" % (r.get("sport"), r.get("release_date"), "; ".join(problems)),
                  file=sys.stderr)
        else:
            good.append(r)
    return good


def _iso(v):
    try:
        return date.fromisoformat(v) if isinstance(v, str) and len(v) == 10 else None
    except ValueError:
        return None


def check_one(r):
    """Structural checks. Whether a release is official is decided once, at `add`, against SCHEDULE, and stored
    with its basis; it is not re-checked here, so a later schedule edit cannot invalidate stored records."""
    p = ["missing %s" % k for k in REQUIRED if r.get(k) in (None, "")]
    if p:
        return p
    if r["sport"] not in NCAA_COM:
        p.append("unknown sport %r" % r["sport"])
    if type(r["official"]) is not bool:
        p.append("official must be true or false")
    for k in ("national_rank", "teams_nationally", "region_rank", "region_teams"):
        if type(r[k]) is not int:
            p.append("%s must be a whole number" % k)
    if not (isinstance(r["npi"], str) and re.fullmatch(r"\d{1,3}\.\d{3}", r["npi"])):
        p.append("npi must be the printed value as text, e.g. \"53.280\"")
    rel, thr = _iso(r["release_date"]), _iso(r["through"])
    if not rel or not thr:
        p.append("release_date and through must be YYYY-MM-DD")
    elif not 0 < (rel - thr).days <= 7:
        p.append("through date must be 1-7 days before the release date")
    if not r["source_url"].startswith("https://stats.ncaa.org/selection_rankings/nitty_gritties/"):
        p.append("source_url is not a stats.ncaa.org NPI table")
    if r["sport"] in NCAA_COM and r["ncaa_com_url"] != NCAA_COM[r["sport"]]:
        p.append("ncaa_com_url is not this sport's NCAA.com NPI page")
    if r["official"] and not r.get("official_basis"):
        p.append("official release without official_basis")
    st = r["region_standings"]
    if not (isinstance(st, list) and all(isinstance(x, list) and len(x) == 2 and type(x[0]) is int
                                         and isinstance(x[1], str) for x in st)):
        return p + ["region_standings must be a list of [NPI rank, team] pairs"]
    if p:
        return p
    ranks = [x[0] for x in st]
    if ranks != sorted(ranks) or len(set(ranks)) != len(ranks) or len({x[1] for x in st}) != len(st):
        p.append("region standings are not distinct teams in strictly ascending NPI-rank order")
    if len(st) != r["region_teams"]:
        p.append("region_teams %d but %d teams listed" % (r["region_teams"], len(st)))
    if not r["region_teams"] <= r["teams_nationally"] or (ranks and ranks[-1] > r["teams_nationally"]):
        p.append("region is larger than the national field")
    pos = [i + 1 for i, x in enumerate(st) if x[1] == "Biola"]
    if pos != [r["region_rank"]]:
        p.append("region_rank %s but Biola is at %s in the region standings" % (r["region_rank"], pos))
    elif st[pos[0] - 1][0] != r["national_rank"]:
        p.append("national_rank %s but the region standings list Biola at NPI rank %s" % (r["national_rank"], st[pos[0] - 1][0]))
    if not 1 <= r["national_rank"] <= r["teams_nationally"]:
        p.append("national_rank outside 1..teams_nationally")
    # The source row as printed, as [header, value] pairs (headers can repeat: men's soccer prints "QWB" twice).
    row = r.get("biola_row")
    if not (isinstance(row, list) and all(isinstance(x, list) and len(x) == 2 for x in row)):
        p.append("biola_row must be a list of [header, value] pairs")
    else:
        got = {h: v for h, v in row}
        for h, want in (("Team", "Biola"), ("NPI Rank", str(r["national_rank"])), ("NPI", r["npi"]),
                        ("DII WL", r.get("record"))):
            if got.get(h) != want:
                p.append("biola_row %s is %r but the record says %r" % (h, got.get(h), want))
    return p


def is_current(r, today):
    """True while r is the newest release that should exist: no official date for its sport falls after it
    and on or before today (if one does, a newer release is out, or due, and r is stale)."""
    t = today.isoformat()
    return not any(r["release_date"] < d_ <= t for d_ in SCHEDULE.get(r["sport"], []))


def latest(sport, today=None):
    """The newest official release for a sport on or before today, or None."""
    today = (today or date.today()).isoformat()
    rs = [r for r in load() if r["sport"] == sport and r["official"] and r["release_date"] <= today]
    return max(rs, key=lambda r: r["release_date"]) if rs else None


def in_region(region):
    """'West Region' -> 'in the West Region'; 'Super-Region 4' -> 'in Super-Region 4'."""
    if region[-1].isdigit():
        return "in " + region
    return "in the %s" % (region if "region" in region.lower() else region + " Region")


def ordinal(n):
    return "%d%s" % (n, "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def main():
    a = sys.argv[1:]
    if a[:1] == ["add"] and len(a) == 2:
        new = json.loads(Path(a[1]).read_text())
        if new.get("official") is True and new.get("release_date") not in SCHEDULE.get(new.get("sport"), []):
            raise SystemExit("not added: %s is not an official release date for %s (npi.py SCHEDULE); "
                             "store it with official false, or fix SCHEDULE first" % (new.get("release_date"), new.get("sport")))
        if new.get("official") is True:
            new.setdefault("official_basis", "Release date on the official 2026-27 schedule (npi.py SCHEDULE), "
                                             "linked from NCAA.com's NPI Rankings page")
        problems = check_one(new)
        if problems:
            raise SystemExit("not added: " + "; ".join(problems))
        doc = json.loads(FILE.read_text()) if FILE.exists() else {
            "about": "Official NCAA DII NPI releases, one record per sport and release (append-only). See npi.py.",
            "releases": []}
        if any(r["sport"] == new["sport"] and r["release_date"] == new["release_date"] for r in doc["releases"]):
            raise SystemExit("already recorded: %s %s" % (new["sport"], new["release_date"]))
        doc["releases"].append(new)
        doc["releases"].sort(key=lambda r: (r["release_date"], r["sport"]))
        FILE.parent.mkdir(exist_ok=True)
        FILE.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
        print("added %s %s: %s of %d %s, No. %d of %d nationally, NPI %s" % (
            new["sport"], new["release_date"], ordinal(new["region_rank"]), new["region_teams"], in_region(new["region"]),
            new["national_rank"], new["teams_nationally"], new["npi"]))
    elif a[:1] == ["check"]:
        print("%d releases OK" % len(load()))
    elif a[:1] == ["due"]:
        # Dates before today only (today's release is read after Neil's 8:00 a.m. reminder, before the 17:30 UTC run), and only the
        # last 7 days: an older release that was never read is dropped from the reminders, not chased forever.
        today = date.fromisoformat(a[a.index("--today") + 1]) if "--today" in a else date.today()
        have = {(r["sport"], r["release_date"]) for r in load()}
        for sport, days in SCHEDULE.items():
            for d_ in days:
                age = (today - date.fromisoformat(d_)).days
                if 1 <= age <= 7 and (sport, d_) not in have:
                    print("NPI-READ-NEEDED %s %s %s" % (sport, d_, NCAA_COM[sport]))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
