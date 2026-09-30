#!/usr/bin/env python3
"""Gatekeeper for the weekly refresh. Exit 0 = safe to publish; exit 1 = do not publish.

Usage: python3 validate.py [--baseline <git-ref>]   (default baseline: HEAD)

Checks
 1. Poll archives are well formed: unique poll_id, release dates parse, ranks never go down,
    every poll lists teams.
 2. Games are well formed: unique game_id, results W/L/T.
 3. History is frozen: compared with the baseline commit,
      - no verified game (data/vs-ranked-verified.json) dated more than 45 days ago appears,
        disappears, or changes rank/result;
      - no ranking row (rankings-merged.json) for a season that ended before the current school
        year appears, disappears or changes.
    Anything that changes history needs a person, so it fails the run instead of publishing.
 4. The published data file exists, has every part, and is not dramatically smaller than the
    baseline (a sign of a broken build).
Writes validate-report.md either way.
"""
import json
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
ref = sys.argv[sys.argv.index("--baseline") + 1] if "--baseline" in sys.argv else "HEAD"
problems, notes = [], []


def at_ref(path):
    try:
        return json.loads(subprocess.run(["git", "-C", str(HERE), "show", "%s:%s" % (ref, path)],
                                         capture_output=True, text=True, check=True).stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return None


def d(s):
    try:
        return date.fromisoformat(str(s)[:10])
    except (TypeError, ValueError):
        return None


def season_start(s):
    m = re.match(r"(\d{4})", str(s or ""))
    return int(m.group(1)) if m else 0


# 1. polls
for pf in sorted((HERE / "polls").glob("*.json")):
    if pf.name == "aliases.json" or pf.name.startswith("backup-"):
        continue
    pd_ = json.loads(pf.read_text())
    ids = [p.get("poll_id") for p in pd_.get("polls", [])]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        problems.append("%s: duplicate poll_id %s" % (pf.name, sorted(dup)[:5]))
    for p in pd_.get("polls", []):
        if p.get("release_date") and not d(p["release_date"]):
            problems.append("%s %s: bad release_date %r" % (pf.name, p.get("poll_id"), p["release_date"]))
        ranks = [t.get("rank") for t in p.get("teams", []) if isinstance(t.get("rank"), int)]
        if not p.get("teams"):
            problems.append("%s %s: poll has no teams" % (pf.name, p.get("poll_id")))
        elif any(b < a for a, b in zip(ranks, ranks[1:])):
            problems.append("%s %s: ranks out of order" % (pf.name, p.get("poll_id")))

# 2. games
games = json.loads((HERE / "games/all-games.json").read_text())["games"]
gids = [g["game_id"] for g in games]
if len(gids) != len(set(gids)):
    problems.append("games: duplicate game_id")
bad = [g["game_id"] for g in games if g.get("result") not in ("W", "L", "T")]
if bad:
    problems.append("games: %d rows without W/L/T, e.g. %s" % (len(bad), bad[:3]))

# 3. history frozen
today = date.today()
cutoff = today - timedelta(days=45)
school_year = today.year if today.month >= 7 else today.year - 1
old_v = at_ref("data/vs-ranked-verified.json")
new_v = json.loads((HERE / "data/vs-ranked-verified.json").read_text())
if old_v is None:
    notes.append("No baseline verified file at %s; history check skipped." % ref)
else:
    sig = lambda g: (g["game_id"], g.get("opponent_rank"), g.get("result"), g.get("poll_release_date"))
    o = {sig(g) for g in old_v["games"] if d(g["date"]) and d(g["date"]) < cutoff}
    n = {sig(g) for g in new_v["games"] if d(g["date"]) and d(g["date"]) < cutoff}
    if o != n:
        problems.append("History changed: %d verified games older than %s added/changed, %d removed/changed. "
                        "Added: %s Removed: %s" % (len(n - o), cutoff, len(o - n), sorted(n - o)[:8], sorted(o - n)[:8]))
    notes.append("Verified games: %d (baseline %d)." % (len(new_v["games"]), len(old_v["games"])))

old_m = at_ref("rankings-merged.json")
new_m = json.loads((HERE / "rankings-merged.json").read_text())
if old_m is not None:
    past = lambda rows: {json.dumps(r, sort_keys=True) for r in rows
                         if season_start(r.get("season")) - (0 if "-" in str(r.get("season")) else 1) < school_year - 1}
    o, n = past(old_m["rows"]), past(new_m["rows"])
    if o != n:
        problems.append("History changed: %d past-season ranking rows differ from baseline." % len(o ^ n))
    added = len(new_m["rows"]) - len(old_m["rows"])
    notes.append("Ranking rows: %d (%+d vs baseline)." % (len(new_m["rows"]), added))

# 4. published data
dp = HERE / "docs/rankings-data.json"
if not dp.exists():
    problems.append("docs/rankings-data.json missing")
else:
    data = json.loads(dp.read_text())
    for k in ("rk-seasons", "rk-polls", "rk-dept", "rk-vs", "rk-stats", "rk-ones", "rk-asof"):
        if not data.get("parts", {}).get(k):
            problems.append("data file part %s is empty" % k)
    old_d = at_ref("docs/rankings-data.json")
    if old_d and len(json.dumps(data)) < 0.9 * len(json.dumps(old_d)):
        problems.append("data file shrank by more than 10%% vs baseline (%d -> %d bytes)"
                        % (len(json.dumps(old_d)), len(json.dumps(data))))

ok = not problems
report = ["# Validation report (%s)" % today, "", "Result: **%s**" % ("PASS" if ok else "FAIL"), ""]
report += ["## Problems", ""] + ["- " + p for p in problems] + [""] if problems else []
report += ["## Notes", ""] + ["- " + n for n in notes]
(HERE / "validate-report.md").write_text("\n".join(report) + "\n")
print("\n".join(report))
sys.exit(0 if ok else 1)
