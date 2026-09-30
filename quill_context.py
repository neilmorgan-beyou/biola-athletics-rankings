#!/usr/bin/env python3
"""Rankings context block for QUILL's season-context files.

Usage: python3 quill_context.py <quill-sport-slug> <season-year> [--today YYYY-MM-DD]
   e.g. python3 quill_context.py volleyball 2026   -> quill/volleyball-2026.md (and stdout)

Writes one markdown section, "## Rankings Context (auto)", meant to sit in
season-context/<slug>-<year>.md in edmshep/sid-article-generation. Every ranking in it is
read from the published poll in effect on game day (polls/*.json), never from a schedule.
Head-to-head series come from games/all-games.json (every result on athletics.biola.edu).
"""
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from join_games_polls import key as name_key  # noqa: E402

# QUILL sport slug -> this repo's sport name and poll file.
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
}
MON = ["Jan.", "Feb.", "March", "April", "May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."]
CATS = [("No. 1", 1), ("Top 5", 5), ("Top 10", 10), ("Top 25", 25)]


def dt(s):
    d = date.fromisoformat(str(s)[:10])
    return "%s %d, %d" % (MON[d.month - 1], d.day, d.year)


def sy(season):
    return int(str(season)[:4])


def rk(r, tied=False):
    return ("T-%d" if tied else "No. %d") % r


def wlt(a):
    return "%d-%d" % (a[0], a[1]) + ("-%d" % a[2] if a[2] else "")


def main():
    slug, year = sys.argv[1], int(sys.argv[2])
    today = date.fromisoformat(sys.argv[sys.argv.index("--today") + 1]) if "--today" in sys.argv else date.today()
    sport, pfile = SPORTS[slug]
    polls = json.loads((HERE / "polls" / (pfile + ".json")).read_text())["polls"]
    games = [g for g in json.loads((HERE / "games/all-games.json").read_text())["games"]
             if g["sport"] == sport and not g.get("exhibition") and g.get("result") in ("W", "L", "T")]
    # The page's own counted games (own-division poll archived, game checkable), so the numbers agree.
    vr = json.loads((HERE / "data/vs-records.json").read_text())
    ver = [g for g in vr["games"] if g["sport"] == sport]
    covered = vr["covered"].get(sport, [])
    aliases = json.loads((HERE / "polls/aliases.json").read_text())
    exact = {" ".join(k.lower().split()): name_key(v) for k, v in aliases.get(sport, {}).items()}
    glob_ = {name_key(k): name_key(v) for k, v in aliases.get("_global", {}).items()}
    canon = lambda n: exact.get(" ".join((n or "").lower().split())) or glob_.get(name_key(n), name_key(n))
    try:
        sha = subprocess.run(["git", "-C", str(HERE), "rev-parse", "--short", "HEAD"], capture_output=True,
                             text=True).stdout.strip()
    except OSError:
        sha = "?"

    season_polls = sorted([p for p in polls if sy(p["season"]) == year and p.get("release_date")
                           and p["release_date"] <= today.isoformat() and p["division"] in ("NCAA DII", "mixed")
                           and not p.get("postseason_final")], key=lambda p: p["release_date"])
    L = ["## Rankings Context (auto)",
         "*Generated %s from github.com/neilmorgan-beyou/biola-athletics-rankings @ %s (the data behind "
         "athletics.biola.edu Rankings History). Do not hand-edit; it is regenerated weekly. Every ranking here was "
         "read from the published national poll in effect on game day (the latest poll released on or before the "
         "game), never from a schedule listing or tournament seed.*" % (dt(today.isoformat()), sha), ""]

    # 1. Biola's own ranking this season
    L.append("### Biola's ranking this season")
    if not season_polls:
        L.append("- No %s poll released yet this season." % sport)
    else:
        poll_name = season_polls[-1]["poll"]
        hist = []
        for p in season_polls:
            t = next((t for t in p["teams"] if name_key(t["team_raw"]).split("|")[0] == "biola"), None)
            rv = next((t for t in p.get("receiving_votes", []) if name_key(t["team_raw"]).split("|")[0] == "biola"), None)
            val = rk(t["rank"], t.get("tied")) if t else ("receiving votes" if rv else "not ranked")
            hist.append((p, val))
        last_p, last_v = hist[-1]
        L.append("- **Current (%s, %s, released %s):** %s%s" % (
            poll_name, last_p.get("week") or "", dt(last_p["release_date"]), last_v,
            (" (%s points)" % next(t for t in last_p["teams"] if name_key(t["team_raw"]).split("|")[0] == "biola")["points"])
            if last_v.startswith(("No.", "T-")) and next(t for t in last_p["teams"] if name_key(t["team_raw"]).split("|")[0] == "biola").get("points") else ""))
        L.append("- **Week by week:** " + "; ".join("%s %s" % (p.get("week") or dt(p["release_date"]), v) for p, v in hist))
        ranked_weeks = [p for p, v in hist if v.startswith(("No.", "T-"))]
        if ranked_weeks and len(ranked_weeks) == 1 and hist[-1][1].startswith(("No.", "T-")):
            L.append("- This is Biola's first week ranked in this poll **this season**. Do not call it a program first "
                     "unless the Rankings History page or the record book says so.")
    L.append("")

    # 2. Current poll, so the drafter can tell whether tonight's opponent is ranked
    if season_polls:
        p = season_polls[-1]
        L.append("### Current national poll (%s, %s, released %s)" % (p["poll"], p.get("week") or "", dt(p["release_date"])))
        L.append(", ".join("%s %s" % (rk(t["rank"], t.get("tied")), t["team_raw"]) for t in p["teams"]))
        if p.get("receiving_votes"):
            L.append("Receiving votes: " + ", ".join(t["team_raw"] for t in p["receiving_votes"]))
        L.append("*An opponent's rank in a recap is the rank in the poll in effect on game day. For a game played "
                 "before this poll's release date, use the earlier poll (see the games list below).*")
        L.append("")

    # 3. Record vs ranked, this season and all-time
    def tally(gs):
        out = {c: [0, 0, 0] for c, _ in CATS}
        for g in gs:
            for c, cap in CATS:
                if g["opponent_rank"] <= cap:
                    out[c]["WLT".index(g["result"])] += 1
        return out
    seasons_cov = sorted(set(covered) | {year})
    this = [g for g in ver if sy(g["season"]) == year]
    L.append("### Record vs. ranked opponents")
    t_this, t_all = tally(this), tally(ver)
    L.append("- **This season:** " + ", ".join("vs %s %s" % (c, wlt(t_this[c])) for c, _ in CATS))
    L.append("- **All seasons covered (%d-%d):** " % (min(seasons_cov), max(seasons_cov)) +
             ", ".join("vs %s %s" % (c, wlt(t_all[c])) for c, _ in CATS))
    for c, cap in CATS:
        wins = sorted([g for g in ver if g["result"] == "W" and g["opponent_rank"] <= cap], key=lambda g: g["date"])
        if wins:
            w = wins[-1]
            L.append("- **Most recent win over a %s team:** %s, %s over %s %s (%s poll of %s)" % (
                c, dt(w["date"]), (w.get("score") or "").strip(), rk(w["opponent_rank"], w.get("tied")), w["opponent_raw"],
                w["poll"].split(" ")[0], dt(w["poll_release_date"])))
    if this:
        L.append("- **This season's games vs ranked opponents:**")
        for g in sorted(this, key=lambda g: g["date"]):
            L.append("  - %s: %s %s vs %s %s (%s, released %s)" % (
                dt(g["date"]), g["result"], (g.get("score") or "").strip(), rk(g["opponent_rank"], g.get("tied")),
                g["opponent_raw"], g["poll"], dt(g["poll_release_date"])))
    L.append("*Coverage: only seasons whose polls are archived are counted; before %d the record vs. ranked teams "
             "is unknown, not zero. Never write \"first win over a Top-10 team\" unless the most-recent-win line "
             "above supports it.*" % min(seasons_cov))
    L.append("")

    # 4. Head-to-head series vs this season's opponents
    opps = []
    for g in sorted([g for g in games if sy(g["season"]) == year], key=lambda g: g["date"]):
        k = canon(g["opponent_raw"]).split("|")[0]
        if k not in [o[0] for o in opps]:
            opps.append((k, g["opponent_raw"]))
    if opps:
        L.append("### All-time series vs. this season's opponents")
        L.append("| Opponent | Series (W-L-T) | First meeting | Last result before this season |")
        L.append("|---|---|---|---|")
        for k, shown in opps:
            gs = sorted([g for g in games if canon(g["opponent_raw"]).split("|")[0] == k], key=lambda g: g["date"] or "")
            rec = [sum(g["result"] == x for g in gs) for x in "WLT"]
            before = [g for g in gs if sy(g["season"]) < year]
            last = before[-1] if before else None
            L.append("| %s | %s | %s | %s |" % (
                shown, wlt(rec), (gs[0]["date"] or gs[0]["season"])[:4],
                ("%s %s (%s)" % (last["result"], (last.get("score") or "").strip(), dt(last["date"]))) if last and last.get("date") else "first meeting this season"))
        L.append("*Series counts every non-exhibition result listed on athletics.biola.edu, matched by school name "
                 "(renamed schools and inconsistent listings can split a series). If this disagrees with the record "
                 "book, the record book wins; flag it.*")
        L.append("")

    out = "\n".join(L).rstrip() + "\n"
    (HERE / "quill").mkdir(exist_ok=True)
    (HERE / "quill" / ("%s-%d.md" % (slug, year))).write_text(out)
    print(out)


if __name__ == "__main__":
    main()
