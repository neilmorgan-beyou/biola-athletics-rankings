#!/usr/bin/env python3
"""Weekly QUILL recap-context feed file (contract: recap-context/README.md in
edmshep/sid-article-generation).

Usage: python3 recap_context.py [--today YYYY-MM-DD] [--out DIR]
Writes <DIR or recap/>/<academic year>/biola-recap-context-YYYY-MM-DD.json and prints a summary.

Facts per in-season sport (QUILL sport slugs):
  poll      Biola's current national poll position (volatile)
  poll      Biola's current regional ranking, where one is published (volatile)
  record    record vs. ranked opponents this season and in all covered seasons (volatile)
  record    most recent win over a No. 1 / Top 5 / Top 10 team (volatile)
  poll      opponents Biola has played this season or last that are ranked / receiving votes now (volatile, team level)
  storyline "first win over a Top N team since ..." for this season's wins over ranked teams (stable)
No head-to-head series facts until the record books (#135) are the source (Eddie, 2026-09-30).
Every ranking is the poll in effect on game day, read from the poll itself.
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from join_games_polls import key as name_key, AMBIGUOUS  # noqa: E402

PAGE = "https://athletics.biola.edu/sports/2026/9/30/rankings-history.aspx"
# QUILL slug -> (sport name in this repo, poll archive file or None)
SPORTS = {
    "volleyball": ("Women's Volleyball", "womens-volleyball"),
    "mens-soccer": ("Men's Soccer", "mens-soccer"),
    "womens-soccer": ("Women's Soccer", "womens-soccer"),
    "mens-basketball": ("Men's Basketball", "mens-basketball"),
    "womens-basketball": ("Women's Basketball", "womens-basketball"),
    "baseball": ("Baseball", "baseball"),
    "softball": ("Softball", "softball"),
    "mens-water-polo": ("Men's Water Polo", "mens-water-polo"),
    "womens-water-polo": ("Women's Water Polo", "womens-water-polo"),
    "mens-tennis": ("Men's Tennis", "mens-tennis"),
    "womens-tennis": ("Women's Tennis", "womens-tennis"),
    "mens-cross-country": ("Men's Cross Country", None),
    "womens-cross-country": ("Women's Cross Country", None),
}
MON = ["Jan.", "Feb.", "March", "April", "May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."]
POLL_NAME = {"NCAA DII": "NCAA Division II", "mixed": "national"}


def d(s):
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return date(1900, 1, 1)  # partial dates ("2017-11") are never current


def md(s, year=False):
    x = d(s)
    return "%s %d" % (MON[x.month - 1], x.day) + (", %d" % x.year if year else "")


def rk(r, tied=False):
    return ("tied for No. %d" if tied else "No. %d") % r


def is_biola(name):
    return name_key(name).split("|")[0] == "biola"


def wlt(a):
    return "%d-%d" % (a[0], a[1]) + ("-%d" % a[2] if a[2] else "")


def poll_name(url):
    """The poll's name in QUILL's poll calendar (recap-context/README.md), or None for a poll QUILL
    has no schedule for (those ranks last a week there; tell Eddie when a new one appears)."""
    u = url.lower()
    if "avca.org" in u and "division-ii-women" in u:
        return "avca-d2-women"
    if "ncaa.com/rankings/" in u and "/d2/regional-ranking" in u:
        if "/soccer-" in u:
            return "ncaa-d2-regional-soccer"
        if "/volleyball-women/" in u:
            return "ncaa-d2-regional-volleyball"
        return None
    if "unitedsoccercoaches.org" in u:
        return "usc-d2"
    if "collegiatewaterpolo.org" in u and "mens-varsity" in u and "womens" not in u:
        return "cwpa-mens-varsity"
    if "ustfccca.org" in u and "ncaa-dii" in u and "cross-country" in u:
        if "regional" in u:
            return "ustfccca-d2-xc-regional"
        if "national" in u:
            return "ustfccca-d2-xc-national"
    return None


def fact(text, category, volatility, as_of, source_url):
    assert len(text) <= 320, text
    assert source_url and source_url.startswith("https://"), source_url
    f = {"text": text, "category": category, "volatility": volatility, "as_of": str(as_of)[:10],
         "source_url": source_url}
    if category == "poll" and poll_name(source_url):
        f["poll"] = poll_name(source_url)
    return f


def main():
    today = d(sys.argv[sys.argv.index("--today") + 1]) if "--today" in sys.argv else date.today()
    out_dir = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else HERE / "recap"
    acad = "%d-%02d" % ((today.year, (today.year + 1) % 100) if today.month >= 7 else (today.year - 1, today.year % 100))
    games_all = json.loads((HERE / "games/all-games.json").read_text())["games"]
    vr = json.loads((HERE / "data/vs-records.json").read_text())
    rows = json.loads((HERE / "rankings-merged.json").read_text())["rows"]

    sports_out = {}
    for slug, (sport, pfile) in SPORTS.items():
        games = sorted([g for g in games_all if g["sport"] == sport and not g.get("exhibition")
                        and g.get("result") in ("W", "L", "T") and g.get("date") and d(g["date"]) <= today],
                       key=lambda g: g["date"])
        cur_season = games[-1]["season"] if games else None
        last_game = games[-1]["date"] if games else None
        polls = []
        if pfile:
            polls = sorted([p for p in json.loads((HERE / "polls" / (pfile + ".json")).read_text())["polls"]
                            if p.get("release_date") and d(p["release_date"]) <= today
                            and p["division"] in ("NCAA DII", "mixed") and not p.get("postseason_final")],
                           key=lambda p: p["release_date"])
        latest = polls[-1] if polls else None
        # In season: a game or a poll in the last 21 days.
        recent = [x for x in (last_game, latest and latest["release_date"]) if x]
        xc_rows = [r for r in rows if r["sport"] == sport and r.get("date") and (today - d(r["date"])).days <= 16
                   and str(r.get("era", "")).startswith("NCAA")]
        if pfile and not any((today - d(x)).days <= 21 for x in recent):
            continue
        if not pfile and not xc_rows:
            continue
        facts = []

        # Biola's own poll position
        if latest and (today - d(latest["release_date"])).days <= 21:
            pname = "%s poll" % latest["poll"].replace(" (formerly NSCAA)", "")
            wk = latest.get("week") or ""
            t = next((t for t in latest["teams"] if is_biola(t["team_raw"])), None)
            rv = next((t for t in latest.get("receiving_votes", []) if is_biola(t["team_raw"])), None)
            if t:
                txt = "Biola is %s in the %s (%s, released %s)%s." % (
                    rk(t["rank"], t.get("tied")), pname, wk, md(latest["release_date"]),
                    (" with %d points" % t["points"]) if t.get("points") else "")
            elif rv:
                txt = "Biola is receiving votes in the %s (%s, released %s)." % (pname, wk, md(latest["release_date"]))
            else:
                txt = "Biola is not ranked or receiving votes in the %s (%s, released %s)." % (
                    pname, wk, md(latest["release_date"]))
            facts.append(fact(txt, "poll", "volatile", latest["release_date"], latest.get("source_url") or PAGE))

        # Rankings from rows: XC national, and regional rankings for every sport
        best = {}
        for r in rows:
            if r["sport"] != sport or not r.get("date") or (today - d(r["date"])).days > 16:
                continue
            if not str(r.get("era", "")).startswith("NCAA") or not (r.get("source_url") or "").startswith("https://"):
                continue
            sc = (r.get("scope") or "").lower()
            if sc == "national" and pfile:
                continue
            k = (sc, r.get("poll"), r.get("region"))
            if k not in best or r["date"] > best[k]["date"]:
                best[k] = r
        for (sc, poll, region), r in sorted(best.items(), key=lambda kv: kv[0][0]):
            rank = str(r["rank"])
            if rank.upper().startswith("RV"):
                pos = "receiving votes"
            elif rank.upper().startswith("T"):
                pos = "tied for No. %s" % rank[1:]
            else:
                pos = "No. %s" % rank
            if sc == "national":
                where = "in the %s" % poll
            elif poll.startswith("NCAA DII Regional Rankings"):
                # Region name as printed: "West" -> "the West Region", "Super-Region 4" stays as is.
                reg = (region if "region" in (region or "").lower() else "the %s Region" % region) if region else ""
                where = "in %s of the NCAA Division II regional rankings" % reg if reg else "in the NCAA Division II regional rankings"
            else:
                where = "in the %s%s" % ("%s Region " % region if region else "", poll.replace(" Regional Rankings", " regional rankings"))
            when = ("%s%s" % ((r.get("week") or "")[:1].lower(), (r.get("week") or "")[1:])
                    if poll.startswith("NCAA DII Regional Rankings") else "%s, released %s" % (r.get("week") or "", md(r["date"])))
            facts.append(fact("Biola is %s %s (%s)." % (pos, where, when),
                              "poll", "volatile", r["date"], r["source_url"]))

        # Records vs ranked (same numbers as the Rankings History page)
        ver = [g for g in vr["games"] if g["sport"] == sport]
        cov = vr["covered"].get(sport, [])
        if pfile and cov and games:
            this = [g for g in ver if g["season"] == cur_season and g["date"] <= last_game]

            def tally(gs, cap):
                a = [0, 0, 0]
                for g in gs:
                    if g["opponent_rank"] <= cap:
                        a["WLT".index(g["result"])] += 1
                return a
            t25, t10 = tally(this, 25), tally(this, 10)
            facts.append(fact(
                "Biola is %s this season against opponents ranked in the national poll at the time they played%s." % (
                    wlt(t25), (", including %s against top-10 teams" % wlt(t10)) if sum(t10) else ""),
                "record", "volatile", last_game, PAGE))
            past = [g for g in ver if g["date"] <= last_game]
            a25, a10, a5, a1 = (tally(past, c) for c in (25, 10, 5, 1))
            facts.append(fact(
                "Since %d, Biola is %s against nationally ranked opponents, %s against top-10 teams, %s against "
                "top-5 teams and %s against No. 1 teams (rank from the poll in effect on game day)." % (
                    min(cov), wlt(a25), wlt(a10), wlt(a5), wlt(a1)),
                "record", "volatile", last_game, PAGE))
            for label, cap in (("No. 1", 1), ("top-5", 5), ("top-10", 10)):
                wins = [g for g in past if g["result"] == "W" and g["opponent_rank"] <= cap]
                if wins:
                    w = wins[-1]
                    facts.append(fact("Biola's most recent win over a %s team was %s, %s over %s %s." % (
                        label, md(w["date"], True), (w.get("score") or "").strip(), rk(w["opponent_rank"], w.get("tied")),
                        w["opponent_raw"]), "record", "volatile", last_game, PAGE))
            # First-since storylines for this season's wins over ranked teams (stable: history can't change)
            for w in [g for g in this if g["result"] == "W"]:
                for label, cap in (("top-10", 10), ("ranked", 25)):
                    if w["opponent_rank"] > cap:
                        continue
                    prev = [g for g in ver if g["result"] == "W" and g["opponent_rank"] <= cap and g["date"] < w["date"]]
                    since = ("its first over a %s team since %s (vs. %s %s)" % (
                        label, md(prev[-1]["date"], True), rk(prev[-1]["opponent_rank"], prev[-1].get("tied")),
                        prev[-1]["opponent_raw"])) if prev else ("its first over a %s team since at least %d" % (label, min(cov)))
                    facts.append(fact("Biola's %s win over %s %s was %s." % (
                        md(w["date"], True), rk(w["opponent_rank"], w.get("tied")), w["opponent_raw"], since),
                        "storyline", "stable", w["date"], PAGE))
                    break

        # Opponents (team level): ranked or receiving votes in the latest poll, if Biola played them this season or last.
        # Shared names (Concordia, Dominican...) use the reviewed alias target, else the poll's own wording.
        al = json.loads((HERE / "polls/aliases.json").read_text())
        poll_alias = {**al.get("_global", {}), **al.get("_poll:" + sport, {})}
        if latest and (today - d(latest["release_date"])).days <= 21 and games:
            seasons = sorted({g["season"] for g in games})[-2:]
            seen = {}
            for g in games:
                if g["season"] in seasons:
                    seen.setdefault(name_key(g["opponent_raw"]).split("|")[0], g["opponent_raw"])
            pname = "%s poll" % latest["poll"].replace(" (formerly NSCAA)", "")
            for t in latest["teams"]:
                k = name_key(t["team_raw"]).split("|")[0]
                if k in seen and not is_biola(t["team_raw"]):
                    facts.append(fact("%s is %s in the %s (%s, released %s)." % (
                        (poll_alias.get(t["team_raw"], t["team_raw"]) if k in AMBIGUOUS else seen[k]), rk(t["rank"], t.get("tied")), pname, latest.get("week") or "", md(latest["release_date"])),
                        "poll", "volatile", latest["release_date"], latest.get("source_url") or PAGE))
            for t in latest.get("receiving_votes", []):
                k = name_key(t["team_raw"]).split("|")[0]
                if k in seen and not is_biola(t["team_raw"]):
                    facts.append(fact("%s is receiving votes in the %s (%s, released %s)." % (
                        (poll_alias.get(t["team_raw"], t["team_raw"]) if k in AMBIGUOUS else seen[k]), pname, latest.get("week") or "", md(latest["release_date"])),
                        "poll", "volatile", latest["release_date"], latest.get("source_url") or PAGE))

        if facts:
            ct = last_game or max(f["as_of"] for f in facts)
            sports_out[slug] = {"current_through": str(ct)[:10], "facts": facts[:25]}

    doc = {"schema_version": 1,
           "generated_at": "%sT%s-07:00" % (today.isoformat(), "15:00:00"),
           "sports": sports_out}
    path = out_dir / acad / ("biola-recap-context-%s.json" % today.isoformat())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print(path)
    for s, v in sports_out.items():
        print("\n[%s] current_through %s, %d facts" % (s, v["current_through"], len(v["facts"])))
        for f in v["facts"]:
            print("  - (%s/%s, %s) %s" % (f["category"], f["volatility"], f["as_of"], f["text"]))


if __name__ == "__main__":
    main()
