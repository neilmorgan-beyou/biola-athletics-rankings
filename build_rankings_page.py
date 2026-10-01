#!/usr/bin/env python3
"""Build the Rankings History sport-file body from the research JSON.

Usage: python3 build_rankings_page.py <data_dir> [out_dir]

Reads every *.json in data_dir:
  - files with "rows" / "season_summaries"  -> poll appearances
  - vs-ranked.json with "games" / "summary" -> record against ranked opponents
Writes:
  rankings-history-sportfile-body.html  (paste into Sidearm, CKEditor Source view)
  rankings-history-preview.html         (same body wrapped in a page, for local review)
  rankings-merged.json                  (the deduped dataset the page was built from)

Page follows the sibling-page build rules (scoped .biola-cmp CSS, official 2026
palette, pure ASCII source) with one deliberate exception copied from the FAQ
page: an inline script for filter/sort. Every table is rendered as static HTML,
so with no script the page is complete and readable; the controls are hidden in
CSS until the script adds .js-on.
"""
import html
import json
import os
from datetime import date
import re
import sys
from collections import defaultdict
from pathlib import Path

DATA = Path(sys.argv[1])
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parent

SPORT_ORDER = [
    "Baseball", "Men's Basketball", "Women's Basketball",
    "Men's Cross Country", "Women's Cross Country",
    "Men's Soccer", "Women's Soccer", "Softball",
    "Men's Swimming & Diving", "Women's Swimming & Diving",
    "Men's Tennis", "Women's Tennis",
    "Men's Track & Field", "Women's Track & Field",
    "Women's Volleyball", "Men's Water Polo", "Women's Water Polo",
    "Men's Golf", "Women's Golf", "Wrestling",
]


def sport_key(s):
    return SPORT_ORDER.index(s) if s in SPORT_ORDER else len(SPORT_ORDER)


def season_start(season):
    m = re.match(r"(\d{4})", str(season or ""))
    return int(m.group(1)) if m else 0


def e(s):
    """HTML-escape and force pure-ASCII output (non-ASCII -> numeric entity)."""
    s = html.escape("" if s is None else str(s), quote=True)
    return s.encode("ascii", "xmlcharrefreplace").decode("ascii")


def rank_kind(r):
    if r is None or r == "":
        return "none"
    if isinstance(r, (int, float)):
        return "num"
    t = str(r).strip().upper()
    if t.startswith("RV"):
        return "rv"
    if t.startswith("NR") or t in ("NOT RANKED", "UNRANKED"):
        return "nr"
    if "TOP" in t and re.search(r"\d", t):
        return "top"
    return "num" if re.search(r"\d", t) else "other"


def is_ranked(r):
    return rank_kind(r) in ("num", "top")


def rank_num(r):
    """Sort value: numbers ascend, then RV (900), NR (950), unknown/blank (999)."""
    k = rank_kind(r)
    if k in ("num", "top"):
        return int(r) if isinstance(r, (int, float)) else int(re.search(r"(\d+)", str(r)).group(1))
    return {"rv": 900, "nr": 950}.get(k, 999)


def rank_label(r, unknown=""):
    """unknown: what to print for a missing rank ("Ranked" for a poll row whose
    position was not published; "" for an empty summary cell)."""
    k = rank_kind(r)
    if k == "none":
        return unknown
    if k == "rv":
        return "RV"
    if k == "nr":
        return "NR"
    if k == "top":
        return "Top %d" % rank_num(r)
    if k == "num":
        return ("T-%d" if str(r).strip().upper().startswith("T") else "No. %d") % rank_num(r)
    return str(r)


def phase(week):
    """Order of a poll within its season: 0 preseason, 1 in-season, 2 final
    regular-season, 3 final, 4 postseason/post-championship."""
    w = (week or "").lower()
    if re.match(r"\s*pre-?season", w):
        return 0
    if re.search(r"post|end of season", w):
        return 4
    if "final" in w and "regular" in w:
        return 2
    if "final" in w:
        return 3
    return 1


# ---------------------------------------------------------------- load
rows, summaries, games, vs_notes, gaps = [], [], [], [], []
FINAL = ["volleyball", "soccer", "basketball", "bat-sports", "xc-track", "other-sports", "deep-history", "current-season", "vs-ranked"]
for f in (DATA / (n + ".json") for n in FINAL):
    if not f.exists():
        print("missing (not finished yet?):", f.name)
        continue
    d = json.loads(f.read_text())
    # Conference preseason polls predict a finish; they are not rankings.
    rows += [r for r in d.get("rows", []) if (r.get("scope") or "").lower() != "conference"
             and r.get("confidence") in ("primary", "biola-news", "secondary")]  # drops a column-shifted row
    summaries += d.get("season_summaries", [])
    gaps += ["%s: %s" % (f.stem, g) for g in d.get("gaps", [])]
    if "games" in d:
        games += d["games"]
        vs_notes += d.get("notes", [])

dept = {}
for n in ("directors-cup", "conference-cup"):
    f = DATA / (n + ".json")
    if f.exists():
        dept[n] = json.loads(f.read_text())
    else:
        print("missing (not finished yet?):", f.name)

# Status corrections to the research data, applied here so the raw files stay as
# delivered. Key: (file, body/conference, season) -> new status.
STATUS_FIXES = {
    # Provisional NCAA members cannot score; "did not place" would read as a miss.
    ("directors-cup", "NCAA DII", "2016-17"): "not eligible",
    ("directors-cup", "NCAA DII", "2017-18"): "not eligible",
    ("directors-cup", "NCAA DII", "2018-19"): "not eligible",
    # NACDA published no final DII standings in the COVID years.
    ("directors-cup", "NCAA DII", "2019-20"): "award not held",
    ("directors-cup", "NCAA DII", "2020-21"): "award not held",
}
AWARD_NAMES = [  # (substring of research name, public name)
    ("Academic Achievement", "PacWest Academic Achievement Award"),
    ("Commissioner's Cup", "PacWest Commissioner's Cup"),
    ("NCCAA", "NCCAA Presidential Award"),
]
for n, d in dept.items():
    for r in d.get("rows", []):
        for sub, name in AWARD_NAMES:
            if sub in (r.get("award") or ""):
                r["award_raw"], r["award"] = r["award"], name
        k = (n, r.get("body") or r.get("conference"), str(r.get("season")))
        if k in STATUS_FIXES:
            r["status_raw"], r["status"] = r.get("status"), STATUS_FIXES[k]

# Opposition-review corrections (data/review-corrections.json).
CORR = json.loads((DATA / "review-corrections.json").read_text()) if (DATA / "review-corrections.json").exists() else {}


def _apply(dst, src, drop=("season", "body", "award_match", "_keep_source")):
    for k, v in src.items():
        if k not in drop:
            dst[k] = v


dcr = dept.get("directors-cup", {}).get("rows", [])
for fix in CORR.get("directors_cup_rows", []) + CORR.get("directors_cup_fields", []):
    hit = [r for r in dcr if r.get("body") == fix["body"] and str(r.get("season")) == fix["season"]]
    for r in hit:
        _apply(r, fix)
ccr = dept.get("conference-cup", {}).get("rows", [])
for fix in CORR.get("conference_rows", []) + CORR.get("conference_fields", []):
    hit = [r for r in ccr if fix["award_match"] in (r.get("award") or "") and str(r.get("season")) == fix["season"]]
    assert len(hit) == 1, ("conference correction matches %d rows" % len(hit), fix)
    _apply(hit[0], fix)

for upd in CORR.get("poll_row_updates", []):
    m_ = upd["match"]
    for r in rows:
        if (r.get("sport") == m_["sport"] and str(r.get("season")) == m_["season"] and r.get("rank") == m_["rank"]
                and m_["source_url_contains"] in (r.get("source_url") or "")):
            r.update(upd["set"])
_pfx = CORR.get("poll_rules", {}).get("drop_week_prefix")
if _pfx:
    rows = [r for r in rows if not str(r.get("week") or "").startswith(_pfx)]

# Current seasons: Biola's own appearances are read straight from the poll archive (polls/*.json),
# which the weekly routine keeps up to date, and replace the hand-researched rows for those
# seasons and divisions. Older seasons keep the researched rows (regional polls, notes, sources).
CURRENT_FROM = int(os.environ.get("CURRENT_FROM", "2026"))
sys.path.insert(0, str(Path(__file__).parent))
from join_games_polls import key as _pkey
ERA = {"NCAA DII": "NCAA DII", "NAIA": "NAIA", "NAIA DI": "NAIA", "mixed": "NCAA DII"}
derived = []
for pf in sorted((Path(__file__).parent / "polls").glob("*.json")):
    if pf.name == "aliases.json" or pf.name.startswith("backup-"):
        continue
    pd_ = json.loads(pf.read_text())
    for p in pd_.get("polls", []):
        if season_start(p.get("season")) < CURRENT_FROM or not p.get("release_date"):
            continue
        hit = [t for t in p.get("teams", []) if _pkey(t.get("team_raw")).split("|")[0] == "biola"]
        rv = [t for t in p.get("receiving_votes", []) if _pkey(t.get("team_raw")).split("|")[0] == "biola"]
        if not hit and not rv:
            continue
        t = (hit or rv)[0]
        derived.append({
            "sport": pd_["sport"], "season": str(p["season"]), "era": ERA.get(p.get("division"), p.get("division")),
            "poll": p["poll"], "scope": "national", "region": None, "week": p.get("week"),
            "date": p["release_date"], "rank": (("T%d" % t["rank"]) if t.get("tied") else t["rank"]) if hit else "RV",
            "points": t.get("points"), "record_at_time": t.get("record"), "source_url": p.get("source_url"),
            "confidence": p.get("confidence") or "primary", "notes": "From the poll archive (polls/%s)" % pf.name})
cover = {(r["sport"], season_start(r["season"]), r["era"]) for r in derived}
rows = [r for r in rows if not ((r.get("sport"), season_start(r.get("season")), r.get("era")) in cover
                                and (r.get("scope") or "") == "national")] + derived

# Dedupe poll rows. Exact repeats first, then the same poll reported twice
# (poll archive + Biola story, dates a few days apart), then rows reconstructed
# from a later poll's "previous" column when that earlier poll is already present.
from datetime import date as _date, timedelta


def pdate(sv):
    try:
        return _date.fromisoformat(str(sv)[:10])
    except ValueError:
        return None


conf_rank = {"primary": 0, "biola-news": 1, "secondary": 2}
grp = lambda r: (r.get("sport"), str(r.get("season")), r.get("poll"), r.get("region"))
seen, uniq, dropped = set(), [], []
for r in sorted(rows, key=lambda r: conf_rank.get(r.get("confidence"), 3)):
    k = grp(r) + (str(r.get("week")), str(r.get("date")), str(r.get("rank")))
    if k in seen:
        dropped.append(("exact", r))
        continue
    near = next((u for u in uniq if grp(u) == grp(r) and rank_num(u.get("rank")) == rank_num(r.get("rank"))
                 and pdate(u.get("date")) and pdate(r.get("date"))
                 and abs((pdate(u["date"]) - pdate(r["date"])).days) <= 3), None)
    if near:
        dropped.append(("same poll, dates within 3 days", r))
        continue
    if r.get("confidence") == "biola-news" and pdate(r.get("date")):
        cited = next((u for u in uniq if grp(u) == grp(r) and u.get("confidence") == "primary"
                      and rank_num(u.get("rank")) == rank_num(r.get("rank")) and pdate(u.get("date"))
                      and 0 <= (pdate(r["date"]) - pdate(u["date"])).days <= 7), None)
        if cited:
            dropped.append(("Biola story citing a poll already present", r))
            continue
    m = re.match(r"poll before (\d{4}-\d{2}-\d{2})", str(r.get("week") or ""), re.I)
    if m:
        # The poll just before `before` that we do have: if it shows the same rank
        # within four weeks (holiday gaps), the reconstructed row is that poll.
        before = pdate(m.group(1))
        prior = [u for u in rows if grp(u) == grp(r) and pdate(u.get("date"))
                 and timedelta(0) < before - pdate(u["date"]) <= timedelta(days=28)]
        last = max(prior, key=lambda u: u["date"]) if prior else None
        if (last and rank_num(last.get("rank")) == rank_num(r.get("rank"))
                and conf_rank.get(last.get("confidence"), 3) <= conf_rank.get(r.get("confidence"), 3)):
            dropped.append(("reconstructed poll already present", r))
            continue
    seen.add(k)
    uniq.append(r)
rows = sorted(uniq, key=lambda r: (sport_key(r.get("sport")), -season_start(r.get("season")),
                                    r.get("poll") or "", phase(r.get("week")), r.get("date") or ""))

# Receiving-votes opponents are not ranked; keep them out of the record.
GR = CORR.get("game_rules", {})


def game_ok(g):
    if g.get("result") not in ("W", "L", "T") or not is_ranked(g.get("opponent_rank")):
        return False
    if rank_num(g["opponent_rank"]) > GR.get("max_rank", 999):
        return False
    raw = g.get("rank_listed_raw") or ""
    if any(x in raw for x in GR.get("exclude_rank_raw", [])):
        return False
    if GR.get("exclude_division_mismatch"):
        ncaa_era = season_start(g.get("season")) >= 2017
        if ("NAIA" in raw and ncaa_era) or ("NCAA" in raw and not ncaa_era):
            return False
    for sp, se, ev, _why in GR.get("exclude_event_contains", []):
        if g["sport"] == sp and str(g.get("season")) == se and ev in (g.get("event") or ""):
            return False
    return True


games = [g for g in games if game_ok(g)]
for g in games:
    g["opponent"] = CORR.get("opponent_display", {}).get(g.get("opponent_raw"), g.get("opponent"))
games.sort(key=lambda g: (sport_key(g.get("sport")), g.get("date") or ""))

# Season summaries. Computed from the rows, then the researchers' own season
# summaries win wherever they state a value: they read the whole season
# (postseason polls, flagged discrepancies) and the heuristic cannot.
by_season = defaultdict(list)
for r in rows:
    by_season[grp(r)].append(r)
summ = {}
for key, rs in by_season.items():
    ranked = [r for r in rs if is_ranked(r.get("rank"))]
    pre = next((r for r in rs if phase(r.get("week")) == 0), None)
    fins = [r for r in rs if phase(r.get("week")) >= 2]
    fin = max(fins, key=lambda r: (phase(r.get("week")), r.get("date") or "")) if fins else None
    peak = min(ranked, key=lambda r: rank_num(r["rank"])) if ranked else None
    summ[key] = {
        "sport": key[0], "season": key[1], "poll": key[2], "region": key[3],
        "scope": rs[0].get("scope"), "era": rs[0].get("era"),
        "preseason": pre and pre.get("rank"), "peak": peak and peak.get("rank"),
        "final": fin and fin.get("rank"), "source_url": (fin or peak or rs[0]).get("source_url"),
    }


def poll_norm(p):
    return re.sub(r"\s+", " ", re.sub(r"\([^)]*\)", "", (p or "").lower())).strip()


unmatched = []
for s_ in summaries:
    cands = [k for k in summ if k[0] == s_.get("sport") and k[1] == str(s_.get("season")) and k[2] == s_.get("poll")]
    if not cands:
        cands = [k for k in summ if k[0] == s_.get("sport") and k[1] == str(s_.get("season"))
                 and poll_norm(k[2]) == poll_norm(s_.get("poll"))]
    if len(cands) > 1:  # national and regional groups share a poll name
        want_region = "region" in (s_.get("poll") or "").lower()
        cands = [k for k in cands if bool(k[3]) == want_region]
    if len(cands) != 1:
        unmatched.append(s_)
        continue
    cur = summ[cands[0]]
    for fld in ("preseason", "peak", "final"):
        if s_.get(fld) not in (None, ""):
            cur[fld] = s_[fld]
summ = sorted(summ.values(), key=lambda s: (sport_key(s["sport"]), -season_start(s["season"]),
                                             s.get("poll") or ""))

# Record vs ranked, per sport.
rec = defaultdict(lambda: {"all": [0, 0, 0], "top10": [0, 0, 0], "top5": [0, 0, 0], "best": None})
IDX = {"W": 0, "L": 1, "T": 2}
for g in games:
    s = rec[g["sport"]]
    i = IDX[g["result"]]
    rk = rank_num(g.get("opponent_rank"))
    s["all"][i] += 1
    if rk <= 10:
        s["top10"][i] += 1
    if rk <= 5:
        s["top5"][i] += 1
    if g["result"] == "W" and (s["best"] is None or rk < rank_num(s["best"].get("opponent_rank"))):
        s["best"] = g


def wlt(a):
    return "%d-%d" % (a[0], a[1]) + ("-%d" % a[2] if a[2] else "")


def pct(a):
    n = sum(a)
    return "" if not n else ("%.3f" % ((a[0] + a[2] / 2) / n)).lstrip("0")


# ---------------------------------------------------------------- stats strip
# Headline counts: NAIA and NCAA polls only (NCCAA is shown in the tables but
# not counted), one team-season per sport and season year (indoor and outdoor
# track in the same year count once).
PR = CORR.get("poll_rules", {})
numbered = [r for r in rows if is_ranked(r.get("rank")) and re.match(r"(NAIA|NCAA)", r.get("era") or "")
            and rank_num(r["rank"]) <= PR.get("headline_max_rank", 999)
            and not any(x in (r.get("poll") or "") for x in PR.get("headline_exclude_polls", []))]
seasons_ranked = {(r["sport"], season_start(r["season"])) for r in numbered}
sports_ranked = {r["sport"] for r in numbered}
national = [r for r in numbered if (r.get("scope") or "").lower() == "national"]
ones = {}
for r in national:
    if rank_num(r["rank"]) != 1:
        continue
    k = (r["sport"], str(r["season"]))
    better = lambda a: (conf_rank.get(a.get("confidence"), 3), a.get("date") or "9999")
    if k not in ones or better(r) < better(ones[k]):
        ones[k] = r
tot = [sum(rec[s]["all"][i] for s in rec) for i in range(3)]
top10_finals = len({(x["sport"], season_start(x["season"])) for x in summ
                    if (x.get("scope") or "") == "national" and re.match(r"(NAIA|NCAA)", x.get("era") or "")
                    and is_ranked(x.get("final")) and rank_num(x["final"]) <= 10})
best_n = min((rank_num(r["rank"]) for r in national), default=None)
stats = [
    (str(len(sports_ranked)), "Programs ranked nationally or regionally"),
    (str(len(seasons_ranked)), "Team-seasons ranked nationally or regionally"),
    (("No. %d" % best_n) if best_n else "-",
     ("Highest national ranking, reached in %d seasons (listed below)" % len(ones)) if ones else "Highest national ranking"),
    (str(top10_finals), "Seasons finishing in a national top 10"),
]
print("dedupe dropped:", len(dropped), "| unmatched researcher summaries:", len(unmatched))

# ---------------------------------------------------------------- render
# Every organization gets its own Era line (Neil, 2026-10-01). The "other" era holds only NCCAA polls.
LABELS = {"other": "NCCAA", "NAIA/AIAW (unstated)": "Not stated", "national": "National", "regional": "Regional"}
ERA_ORDER = ["AIAW", "NAIA", "NCAA DII", "other", "NAIA/AIAW (unstated)"]


def opts(values):
    return "".join('<option value="%s">%s</option>' % (e(v), e(LABELS.get(v, v))) for v in values)


sports_present = sorted({r["sport"] for r in rows} | {g["sport"] for g in games}, key=sport_key)
eras = sorted({r.get("era") or "" for r in rows} - {""}, key=lambda v: (ERA_ORDER.index(v) if v in ERA_ORDER else 99, v))
scopes = sorted({r.get("scope") or "" for r in rows} - {""})
polls = sorted({r.get("poll") or "" for r in rows} - {""})


def filters(tid, extra=""):
    return (
        '<div class="rk-filters" data-for="%s">'
        '<label><span>Sport</span><select data-f="sport"><option value="">All sports</option>%s</select></label>'
        '%s'
        '<label class="rk-q"><span>Search</span><input type="search" data-f="q" placeholder="Opponent, poll, season..."></label>'
        '<p class="rk-count" aria-live="polite"></p>'
        '</div>' % (tid, opts(sports_present), extra)
    )


def th(label, key, kind="text"):
    return '<th scope="col" data-k="%s" data-t="%s"><button type="button">%s</button></th>' % (key, kind, e(label))


SRC_TEXT = {"primary": "Poll", "biola-news": "Biola", "secondary": "Other"}


def src(r):
    return link(r.get("source_url"), SRC_TEXT.get(r.get("confidence"), "Source"))


def link(url, text="Source"):
    return '<a href="%s">%s</a>' % (e(url), text) if url else ""


# Section 1: season summaries
s_rows = []
for s in summ:
    s_rows.append(
        '<tr data-sport="%s" data-era="%s" data-scope="%s">'
        '<td>%s</td><td data-v="%d">%s</td><td>%s</td><td>%s</td>'
        '<td data-v="%d">%s</td><td data-v="%d" class="rk-peak">%s</td><td data-v="%d">%s</td>'
        '<td>%s</td></tr>' % (
            e(s["sport"]), e(s.get("era")), e(s.get("scope")),
            e(s["sport"]), season_start(s["season"]), e(s["season"]),
            e(LABELS.get(s.get("era"), s.get("era"))), e(s.get("poll")) + (" (%s)" % e(s["region"]) if s.get("region") and s["region"].lower() not in (s.get("poll") or "").lower() else ""),
            rank_num(s.get("preseason")), e(rank_label(s.get("preseason"))),
            rank_num(s.get("peak")), e(rank_label(s.get("peak"))),
            rank_num(s.get("final")), e(rank_label(s.get("final"))),
            link(s.get("source_url"))))

# Section 2: every poll appearance
p_rows = []
for r in rows:
    p_rows.append(
        '<tr data-sport="%s" data-era="%s" data-scope="%s">'
        '<td>%s</td><td data-v="%d">%s</td><td>%s</td><td>%s</td><td>%s</td>'
        '<td data-v="%s">%s</td><td data-v="%d" class="rk-peak">%s</td><td>%s</td><td>%s</td></tr>' % (
            e(r["sport"]), e(r.get("era")), e(r.get("scope")),
            e(r["sport"]), season_start(r["season"]), e(r["season"]),
            e(r.get("poll")), e((r.get("scope") or "").capitalize()) + (" - %s" % e(r["region"]) if r.get("region") else ""),
            e(r.get("week")), e(r.get("date") or ""), e(r.get("date") or ""),
            rank_num(r.get("rank")), e(rank_label(r.get("rank"), unknown="Ranked")),
            e(r.get("record_at_time") or ""), src(r)))

# Section 3: record vs ranked
v_cards = []
for sp in sorted(rec, key=sport_key):
    s = rec[sp]
    b = s["best"]
    v_cards.append(
        '<tr data-sport="%s"><td>%s</td><td data-v="%s">%s</td><td data-v="%s">%s</td>'
        '<td data-v="%s">%s</td><td data-v="%s">%s</td><td>%s</td></tr>' % (
            e(sp), e(sp), pct(s["all"]) or 0, wlt(s["all"]), pct(s["all"]) or 0, pct(s["all"]),
            pct(s["top10"]) or 0, wlt(s["top10"]), pct(s["top5"]) or 0, wlt(s["top5"]),
            ("No. %d %s, %s" % (rank_num(b["opponent_rank"]), e(b["opponent"]), e(b.get("date") or ""))) if b else ""))
g_rows = []
for g in games:
    g_rows.append(
        '<tr data-sport="%s" data-res="%s"><td>%s</td><td data-v="%s">%s</td><td data-v="%d">%s</td>'
        '<td>%s</td><td>%s</td><td class="rk-res is-%s">%s</td><td>%s</td></tr>' % (
            e(g["sport"]), e(g["result"]), e(g["sport"]), e(g.get("date") or ""), e(g.get("date") or ""),
            rank_num(g.get("opponent_rank")), e(rank_label(g.get("opponent_rank"))),
            e(g.get("opponent")), e(g.get("location") or ""), g["result"].lower(),
            e(g["result"] + (" " + g["score"] if g.get("score") else "")), e(g.get("event") or "")))

def place_label(r):
    st = (r.get("status") or "").lower()
    if st != "placed":
        lab = st.capitalize() if st else ""
        if r.get("interim") and r.get("place") is not None:
            if st == "award not held":
                lab = "Not completed"
            lab += " (%s%s at interim)" % ("T-" if r.get("tied") else "", ordinal(r.get("place")))
        return lab
    return ("T-%s" if r.get("tied") else "%s") % ordinal(r.get("place"))


def ordinal(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n or "")
    suf = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return "%d%s" % (n, suf)


def fmt_pts(v):
    if v in (None, ""):
        return ""
    try:
        return ("%.3f" % float(v)).rstrip("0").rstrip(".")
    except ValueError:
        return str(v)


def dept_rows(rs, group_key, out_of_key, show_points=True):
    out = []
    for r in sorted(rs, key=lambda r: (-season_start(r.get("season")), r.get("award") or "")):
        placed = (r.get("status") or "").lower() == "placed"
        out.append(
            '<tr data-sport="%s"%s><td>%s</td><td data-v="%d">%s</td><td>%s</td>'
            '<td data-v="%s" class="%s">%s</td>%s<td data-v="%s">%s</td><td>%s</td></tr>' % (
                e(r.get("award")), '' if placed else ' class="is-quiet"',
                e(r.get("award")), season_start(r.get("season")), e(r.get("season")),
                e(r.get(group_key) or ""),
                r.get("place") if placed and r.get("place") is not None else 999,
                "rk-peak" if placed else "rk-status", e(place_label(r)),
                ('<td data-v="%s">%s</td>' % (r.get("points") if placed and r.get("points") not in (None, "") else -1,
                                              e(fmt_pts(r.get("points")) if placed else ""))) if show_points else "",
                r.get(out_of_key) or 0, e(r.get(out_of_key) or ""),
                link(r.get("source_url"), {"primary": "Official", "biola-news": "Biola"}.get(r.get("confidence"), "Other"))))
    return "".join(out)


dc = dept.get("directors-cup", {}).get("rows", [])
cc = dept.get("conference-cup", {}).get("rows", [])
dc_html = dept_rows(dc, "body", "schools_scored")
cc_html = dept_rows(cc, "conference", "schools", show_points=False)


def award_filter(tid, rs):
    return (
        '<div class="rk-filters" data-for="%s">'
        '<label><span>Award</span><select data-f="sport"><option value="">All awards</option>%s</select></label>'
        '<p class="rk-count" aria-live="polite"></p></div>' % (tid, opts(sorted({r.get("award") for r in rs if r.get("award")})))
    )


era_sel = '<label><span>Era</span><select data-f="era"><option value="">All eras</option>%s</select></label>' % opts(eras)
scope_sel = '<label><span>Poll type</span><select data-f="scope"><option value="">National and regional</option>%s</select></label>' % opts(scopes)
res_sel = '<label><span>Result</span><select data-f="res"><option value="">All results</option><option value="W">Wins</option><option value="L">Losses</option><option value="T">Ties</option></select></label>'

SRC_WORD = {"primary": "poll", "biola-news": "Biola release", "secondary": "other report"}
ones_html = ""
if ones:
    parts = []
    for sp in sorted({k[0] for k in ones}, key=sport_key):
        yrs = sorted((k[1] for k in ones if k[0] == sp), key=season_start)
        cites = ", ".join('%s (<a href="%s">%s</a>)' % (e(y), e(ones[(sp, y)].get("source_url") or ""),
                          ones[(sp, y)].get("cite_label") or SRC_WORD.get(ones[(sp, y)].get("confidence"), "source")) for y in yrs)
        parts.append("<strong>%s</strong> %s" % (e(sp), cites))
    ones_html = '<p class="rk-ones"><span class="k">No. 1 nationally</span> ' + "; ".join(parts) + ".</p>"

stat_html = "".join('<div class="rk-stat"><span class="n">%s</span><span class="l">%s</span></div>' % (e(n), e(l))
                    for n, l in stats)

CSS = (Path(__file__).parent / "rankings.css").read_text()
JS = (Path(__file__).parent / "rankings.js").read_text()

# Record vs. ranked opponents stays off the page until every opponent rank is
# verified against the published poll in effect on game day (Neil, 2026-09-29).
def show_result(g):
    """Result + score, winner's score first; forfeits marked and their court score hidden."""
    if re.search(r"forfeit", (g.get("event") or "") + " " + (g.get("score") or ""), re.I):
        return g["result"] + " (forfeit)"
    m = re.match(r"^\s*(\d+)\s*-\s*(\d+)", g.get("score") or "")
    if not m:
        return g["result"] + (" " + g["score"] if g.get("score") else "")
    a, b = int(m.group(1)), int(m.group(2))
    hi, lo = max(a, b), min(a, b)
    return "%s %d-%d" % (g["result"], hi, lo) if g["result"] == "W" else \
           "%s %d-%d" % (g["result"], lo, hi) if g["result"] == "L" else "%s %d-%d" % (g["result"], a, b)


VS_CATS = [("No. 1", 1), ("Top 5", 5), ("Top 10", 10), ("Top 25", 25)]


SPRING = {"Baseball", "Softball", "Men's Tennis", "Women's Tennis", "Women's Water Polo"}


def biola_division(sport, season):
    """Biola's own division for a season: NAIA through the 2016-17 school year, NCAA DII after."""
    sy = season_start(season) - (1 if sport in SPRING else 0)
    if sy > 2016:
        return "NCAA DII"
    return "NAIA DI" if "Basketball" in sport else "NAIA"  # NAIA split basketball into DI/DII


def build_vs():
    """Record explorer from data/vs-ranked-verified.json (poll-verified ranks only)."""
    vf = DATA / "vs-ranked-verified.json"
    gf = Path(__file__).parent / "games" / "all-games.json"
    if not vf.exists():
        return "", ""
    vg = [g for g in json.loads(vf.read_text())["games"] if g.get("result") in ("W", "L", "T")]
    if not vg:
        return "", ""
    allg = [g for g in json.loads(gf.read_text())["games"]
            if g.get("result") in ("W", "L", "T") and not g.get("exhibition")
            and not (g["sport"] == "Women's Volleyball" and (g.get("score") or "").strip() in ("1-0", "0-1"))]
    sys.path.insert(0, str(Path(__file__).parent))
    from join_games_polls import stale_poll, SAME_DAY
    own = defaultdict(list)  # (sport, season year) -> Biola's own-division polls
    sched_ok = set()
    for pf in (Path(__file__).parent / "polls").glob("*.json"):
        if pf.name == "aliases.json":
            continue
        pd = json.loads(pf.read_text())
        for p in pd.get("polls", []):
            if p.get("release_date") and p.get("division") in ("mixed", biola_division(pd.get("sport"), p.get("season"))):
                own[(pd.get("sport"), season_start(p.get("season")))].append(p)
                if str(p.get("season")) in (pd.get("schedule_complete") or {}).get(p["division"], []):
                    sched_ok.add((pd.get("sport"), season_start(p.get("season"))))

    def checkable(g):
        """A game can be checked when a poll of Biola's own division was in effect and not stale
        (same rule as join_games_polls.stale_poll): not before the season's first poll, and not
        across a hole in the archive."""
        series = [p for p in own.get((g["sport"], season_start(g["season"])), []) if not p.get("postseason_final")]
        gd = g.get("date") or ""
        prior = [p for p in series if p["release_date"] < gd or (SAME_DAY and p["release_date"] == gd)]
        if not prior:
            return False
        cur = max(prior, key=lambda p: p["release_date"])
        if (g["sport"], season_start(g["season"])) in sched_ok:
            return True
        return not stale_poll(cur, date.fromisoformat(gd), series)

    chk = defaultdict(lambda: [0, 0])
    season_label = {}
    for g in allg:
        k = (g["sport"], season_start(g["season"]))
        season_label.setdefault(k, str(g["season"]))
        chk[k][1] += 1
        if checkable(g):
            chk[k][0] += 1
    vg = [g for g in vg if checkable(g)
          and not (g["sport"] == "Women's Volleyball" and (g.get("score") or "").strip() in ("1-0", "0-1"))]
    polled = set()
    for pf in (Path(__file__).parent / "polls").glob("*.json"):
        if pf.name == "aliases.json":
            continue
        pd = json.loads(pf.read_text())
        for p in pd.get("polls", []):
            sp_, se_ = pd.get("sport"), p.get("season")
            # A season is covered only when the poll of Biola's own division is archived.
            if p.get("division") in ("mixed", biola_division(sp_, se_)) and p.get("release_date"):
                k_ = (sp_, season_start(se_))
                if chk[k_][1] and chk[k_][0] * 2 >= chk[k_][1]:
                    polled.add(k_)
    sports = sorted({g["sport"] for g in vg} | {sp for sp, _ in polled}, key=sport_key)
    label = dict(season_label)
    vg = [g for g in vg if (g["sport"], season_start(g["season"])) in polled]
    cell = defaultdict(lambda: [0, 0, 0])
    for g in vg:
        r = rank_num(g["opponent_rank"])
        for lab, cap in VS_CATS:
            if r <= cap:
                for se in (season_start(g["season"]), "All seasons"):
                    cell[(g["sport"], se, lab)][IDX[g["result"]]] += 1
    rows_html, season_opts = [], set()
    for sp in sports:
        seasons = sorted({se for s_, se in polled if s_ == sp}, reverse=True)
        for se in ["All seasons"] + seasons:
            lab_ = se if se == "All seasons" else label.get((sp, se), str(se))
            if se != "All seasons":
                season_opts.add(lab_)
            tds = "".join('<td data-v="%s">%s</td>' % (pct(cell[(sp, se, lab)]) or -1, wlt(cell[(sp, se, lab)]) if sum(cell[(sp, se, lab)]) else "&ndash;")
                          for lab, _ in VS_CATS)
            if se == "All seasons":
                ck = [sum(chk[(sp, y)][0] for y in seasons), sum(chk[(sp, y)][1] for y in seasons)]
            else:
                ck = chk[(sp, se)]
            part = ck[0] < ck[1]
            rows_html.append('<tr data-sport="%s" data-season="%s"%s><td>%s</td><td data-v="%d">%s</td>%s'
                             '<td data-v="%d"%s>%d of %d</td></tr>' % (
                e(sp), e(lab_), ' class="is-total"' if se == "All seasons" else "", e(sp),
                9999 if se == "All seasons" else se, e(lab_), tds,
                ck[0], ' class="rk-partial" title="Some games had no archived poll in effect"' if part else "", ck[0], ck[1]))
    g_rows = []
    for g in sorted(vg, key=lambda g: (sport_key(g["sport"]), g["date"]), reverse=True):
        g_rows.append('<tr data-sport="%s" data-season="%s" data-res="%s"><td>%s</td><td data-v="%s">%s</td>'
                      '<td data-v="%d">%s%d</td><td>%s</td><td>%s</td><td class="rk-res is-%s">%s</td><td>%s</td></tr>' % (
                          e(g["sport"]), e(g["season"]), g["result"], e(g["sport"]), e(g["date"]), e(g["date"]),
                          rank_num(g["opponent_rank"]), "T-" if g.get("tied") else "No. ", rank_num(g["opponent_rank"]),
                          e(g["opponent_raw"]), e(g.get("location") or ""), g["result"].lower(),
                          e(show_result(g)),
                          '<a href="%s">%s %s</a>' % (e(g.get("poll_source_url") or ""),
                                                      e({"mixed": "CWPA"}.get(g.get("poll_division"), g.get("poll_division") or "")),
                                                      e(g["poll_release_date"]))))
    sport_sel = '<label><span>Program</span><select data-f="sport"><option value="">All programs</option>%s</select></label>' % opts(sports)
    season_sel = ('<label><span>Season</span><select data-f="season"><option value="">All seasons</option>%s</select></label>'
                  % "".join('<option value="%s">%s</option>' % (e(x), e(x)) for x in sorted(season_opts, key=season_start, reverse=True)))
    def spans(ys):
        ys, out, i = sorted(ys), [], 0
        while i < len(ys):
            j = i
            while j + 1 < len(ys) and ys[j + 1] == ys[j] + 1:
                j += 1
            out.append(str(ys[i]) if i == j else "%d-%s" % (ys[i], str(ys[j])[-2:]))
            i = j + 1
        return ", ".join(out)
    def span_labels(sp):
        ys = sorted({se for s_, se in polled if s_ == sp})
        if not ys:
            return ""
        return label.get((sp, ys[0]), str(ys[0])) + (" to " + label.get((sp, ys[-1]), str(ys[-1])) if len(ys) > 1 else "")
    covered = "; ".join("%s %s" % (sp, span_labels(sp)) for sp in sports)
    tab = ('<a class="rk-tab is-quiet" role="tab" id="tab-rk-vs" href="#rk-vs" aria-controls="rk-vs">'
           '<span class="t">Vs. ranked opponents</span><span class="d">Records by program and season</span></a>\n')
    panel = f"""<section class="cmp-sec rk-panel" id="rk-vs" role="tabpanel" aria-labelledby="tab-rk-vs">
<h2 class="cmp-h is-blue">Record vs. ranked opponents</h2>
<p class="cmp-sub">Every opponent's ranking is read from the published national poll in effect on game day (the latest poll released on or before the game), never from a schedule listing or tournament seed. The polls used are the NAIA and NCAA Division II coaches' polls (and the national water polo poll); opponents ranked only in NCAA Division I polls are not included. Only seasons whose polls have been archived are included: {e(covered)}.</p>
<div class="rk-filters" data-for="t-vsrec">{sport_sel}{season_sel}<p class="rk-count" aria-live="polite"></p></div>
<div class="rk-wrap"><table class="rk-table" id="t-vsrec">
<thead><tr>{th("Program","0")}{th("Season","1","num")}{th("Vs. No. 1","2","num")}{th("Vs. Top 5","3","num")}{th("Vs. Top 10","4","num")}{th("Vs. Top 25","5","num")}{th("Games checked","6","num")}</tr></thead>
<tbody>{"".join(rows_html)}</tbody></table></div>
<p class="cmp-sub">Games checked counts the games with an archived poll of Biola's own division in effect on game day. Games before a season's first archived poll, or across a missing stretch of polls, cannot be checked and are left out. Seasons where fewer than half the games could be checked are not shown.</p>
<h3 class="rk-h3">Games</h3>
<div class="rk-filters" data-for="t-vsgames">{sport_sel}{season_sel}{res_sel}<p class="rk-count" aria-live="polite"></p></div>
<div class="rk-wrap"><table class="rk-table" id="t-vsgames">
<thead><tr>{th("Program","0")}{th("Date","1")}{th("Opp. rank","2","num")}{th("Opponent","3")}{th("Site","4")}{th("Result","5")}<th scope="col">Poll in effect (released)</th></tr></thead>
<tbody>{"".join(g_rows)}</tbody></table></div>
</section>
"""
    # Same numbers the page shows, for other consumers (quill_context.py).
    (DATA / "vs-records.json").write_text(json.dumps({
        "covered": {sp: sorted({se for s_, se in polled if s_ == sp}) for sp in sports},
        "labels": {"%s|%s" % k: v for k, v in label.items()},
        "games": vg}, indent=0))
    return tab, panel


VS_TAB, VS_PANEL = build_vs()
from datetime import datetime, timezone
DATA_URL = "https://neilmorgan-beyou.github.io/biola-athletics-rankings/rankings-data.json"
GENERATED = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
_today = date.today()
ASOF = "%s %d, %d" % (["Jan.", "Feb.", "March", "April", "May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."][_today.month - 1],
                      _today.day, _today.year)


# ---------------------------------------------------------------- currently ranked
# Delivered through the hosted data (prepended to the No. 1 line), so it needs no Sidearm edit.
MON = ["Jan.", "Feb.", "March", "April", "May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."]
POLL_SHORT = [("AVCA", "AVCA"), ("United Soccer", "United Soccer Coaches"), ("USTFCCCA", "USTFCCCA"), ("NFCA", "NFCA"),
              ("NCBWA", "NCBWA"), ("NABC", "NABC"), ("WBCA", "WBCA"), ("ITA", "ITA"), ("CWPA", "CWPA"),
              ("CSCAA", "CSCAA"), ("NCAA", "NCAA"), ("NAIA", "NAIA"), ("D2SIDA", "D2SIDA"), ("D2CSC", "D2CSC")]


def poll_short(name):
    return next((v for k, v in POLL_SHORT if k in (name or "")), name or "")


def when(ds):
    d_ = date.fromisoformat(ds[:10])
    return "%s %d" % (MON[d_.month - 1], d_.day)


def currently_ranked(today=None):
    today = today or date.today()
    entries = defaultdict(dict)  # sport -> {"national": row, "regional": row}
    archived = set()
    for pf in sorted((Path(__file__).parent / "polls").glob("*.json")):
        if pf.name == "aliases.json" or pf.name.startswith("backup-"):
            continue
        pd_ = json.loads(pf.read_text())
        archived.add(pd_["sport"])
        latest = {}
        for p in pd_.get("polls", []):
            if p.get("release_date") and not p.get("postseason_final"):
                if p["division"] not in latest or p["release_date"] > latest[p["division"]]["release_date"]:
                    latest[p["division"]] = p
        for dv, p in latest.items():
            if dv not in ("NCAA DII", "mixed") or (today - date.fromisoformat(p["release_date"])).days > 30:
                continue
            t = next((t for t in p.get("teams", []) if _pkey(t.get("team_raw")).split("|")[0] == "biola"), None)
            if t:
                entries[pd_["sport"]]["national"] = {"rank": ("T%d" % t["rank"]) if t.get("tied") else t["rank"],
                                                     "poll": p["poll"], "date": p["release_date"],
                                                     "source_url": p.get("source_url")}
    for r in rows:  # sports without a poll archive, and regional rankings everywhere
        sc = (r.get("scope") or "").lower()
        if sc not in ("national", "regional") or not r.get("date") or not is_ranked(r.get("rank")):
            continue
        if sc == "national" and r["sport"] in archived:
            continue
        age = (today - date.fromisoformat(str(r["date"])[:10])).days
        if age < 0 or age > 16 or not re.match(r"NCAA", r.get("era") or ""):
            continue
        cur = entries[r["sport"]].get(sc)
        if not cur or r["date"] > cur["date"]:
            entries[r["sport"]][sc] = dict(r)
    cards = []
    for sp in sorted(entries, key=sport_key):
        e_ = entries[sp]
        if not e_:
            continue
        lines = []
        for sc, label in (("national", "nationally"), ("regional", "")):
            r = e_.get(sc)
            if not r:
                continue
            where = label if sc == "national" else ("%s Region" % r["region"] if r.get("region") else "regionally")
            lines.append('<span class="r"><b>%s</b> %s</span><span class="s">%s, %s &middot; <a href="%s">source</a></span>' % (
                e(rank_label(r["rank"])), e(where), e(poll_short(r["poll"])), when(r["date"]), e(r.get("source_url") or "")))
        cards.append('<div class="rk-now-card"><span class="t">%s</span>%s</div>' % (e(sp), "".join(lines)))
    if not cards:
        return ""
    style = ("<style>.biola-cmp .rk-now{border:1px solid var(--border);border-top:4px solid var(--red);border-radius:0 0 var(--r-sm) var(--r-sm);"
             "padding:14px 16px 16px;margin:0 0 22px}.biola-cmp .rk-now h2{font-family:var(--fd);font-weight:600;text-transform:uppercase;"
             "font-size:20px;margin:0 0 10px;display:flex;justify-content:space-between;align-items:baseline;gap:10px}"
             ".biola-cmp .rk-now h2 small{font-family:var(--fb);font-size:12px;font-weight:600;text-transform:none;color:var(--muted)}"
             ".biola-cmp .rk-now-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px}"
             ".biola-cmp .rk-now-card{background:var(--surface-alt);border-radius:var(--r-sm);padding:10px 12px}"
             ".biola-cmp .rk-now-card .t{display:block;font-family:var(--fd);font-weight:600;text-transform:uppercase;font-size:16px;margin-bottom:4px}"
             ".biola-cmp .rk-now-card .r{display:block;font-size:14.5px}.biola-cmp .rk-now-card .r b{color:var(--red);font-family:var(--fd);font-size:20px;font-weight:600}"
             ".biola-cmp .rk-now-card .s{display:block;font-size:12px;color:var(--muted);margin-bottom:4px}</style>")
    return (style + '<section class="rk-now" aria-label="Teams currently ranked"><h2>Currently ranked <small>as of %s</small></h2>'
            '<div class="rk-now-grid">%s</div></section>' % (ASOF, "".join(cards)))


NOW_HTML = currently_ranked()


def render(vs_tab, vs_panel):
    return f"""
<!-- RANKINGS HISTORY -- Sidearm sport file body. GENERATED by build_rankings_page.py;
     edit the data or the builder, not this file.
     CMS: Hide the sport file title = Yes, Full Width = Yes, sport General.
     Exception to the sibling build rules, same as the FAQ page: one inline script for
     filter/sort. All tables are static HTML; controls stay hidden until the script runs.
     Poll rows: {len(rows)}. Season summaries: {len(summ)}. Games vs ranked: {len(games)}. -->
<style type="text/css">@import url('https://use.typekit.net/awl5tbv.css');
{CSS}
</style>

<div class="biola-cmp rk-app" data-src="{DATA_URL}" data-generated="{GENERATED}">

<div class="cmp-hero">
<p class="cmp-eyebrow">Program history</p>
<h1>Rankings <span>history</span></h1>
<p class="cmp-lede">Every published national and regional poll ranking we can document for Biola Athletics, the department's Directors' Cup and conference all-sport finishes, from the NAIA era through NCAA Division II. Biola University is a Christian university in La Mirada, California, competing in NCAA Division II as a member of the PacWest Conference across eighteen varsity programs.</p>
</div>

<div class="rk-stats">{stat_html}</div>
{ones_html}

<p class="cmp-note"><strong>About this page.</strong> Rankings come from the published polls themselves where an archive survives, and otherwise from Biola Athletics news releases written at the time. "RV" means receiving votes. Current through <span class="rk-asof">{ASOF}</span>. Every entry links to its source, labeled by type: <em>Poll</em> is the published poll itself, <em>Biola</em> is a Biola Athletics release or publication from the time, and <em>Other</em> is another school, conference or media report. Know of a ranking that is missing? Let the athletics communications office know.</p>

<nav class="rk-tabs" role="tablist" aria-label="Rankings history sections">
<a class="rk-tab" role="tab" id="tab-rk-seasons" href="#rk-seasons" aria-controls="rk-seasons"><span class="t">Ranked seasons</span><span class="d">Preseason, peak and final rank by year</span></a>
<a class="rk-tab" role="tab" id="tab-rk-polls" href="#rk-polls" aria-controls="rk-polls"><span class="t">Week-by-week polls</span><span class="d">Every poll Biola appeared in</span></a>
<a class="rk-tab" role="tab" id="tab-rk-dept" href="#rk-dept" aria-controls="rk-dept"><span class="t">Department awards</span><span class="d">Directors' Cup and conference all-sport</span></a>
{vs_tab}</nav>

<section class="cmp-sec rk-panel" id="rk-seasons" role="tabpanel" aria-labelledby="tab-rk-seasons">
<h2 class="cmp-h">Ranked seasons</h2>
<p class="cmp-sub">One row per season and poll: preseason, highest and final ranking. Final is the last poll of the season, postseason where one was published. NR means not ranked. Select a column heading to sort.</p>
{filters("t-seasons", era_sel + scope_sel)}
<div class="rk-wrap"><table class="rk-table" id="t-seasons">
<thead><tr>{th("Sport","0")}{th("Season","1","num")}{th("Era","2")}{th("Poll","3")}{th("Preseason","4","num")}{th("Peak","5","num")}{th("Final","6","num")}<th scope="col">Source</th></tr></thead>
<tbody>{"".join(s_rows)}</tbody></table></div>
</section>

<section class="cmp-sec rk-panel" id="rk-polls" role="tabpanel" aria-labelledby="tab-rk-polls">
<h2 class="cmp-h">Every poll appearance</h2>
<p class="cmp-sub">Each week Biola appeared in a published poll, ranked or receiving votes.</p>
{filters("t-polls", era_sel + scope_sel)}
<div class="rk-wrap"><table class="rk-table" id="t-polls">
<thead><tr>{th("Sport","0")}{th("Season","1","num")}{th("Poll","2")}{th("Type","3")}{th("Week","4")}{th("Date","5")}{th("Rank","6","num")}{th("Record","7")}<th scope="col">Source</th></tr></thead>
<tbody>{"".join(p_rows)}</tbody></table></div>
</section>

<section class="cmp-sec rk-panel" id="rk-dept" role="tabpanel" aria-labelledby="tab-rk-dept">
<h2 class="cmp-h is-blue">Department awards</h2>
<p class="cmp-sub">Biola's finish in the all-sports competitions that score every program together: the Directors' Cup nationally, and each conference's all-sport award. "Did not place" means the final standings exist and Biola is not in them. "Not eligible" covers Biola's three provisional NCAA years, when it could not score. "Award not held" and "Not completed" mark seasons with no final standings, including the COVID years. "No data found" means final standings may exist but could not be located.</p>
<h3 class="rk-h3">National all-sports awards</h3>
{award_filter("t-dc", dc)}
<div class="rk-wrap"><table class="rk-table" id="t-dc">
<thead><tr>{th("Award","0")}{th("Season","1","num")}{th("Division","2")}{th("Finish","3","num")}{th("Points","4","num")}{th("Schools scored","5","num")}<th scope="col">Source</th></tr></thead>
<tbody>{dc_html}</tbody></table></div>
<h3 class="rk-h3">Conference all-sport award</h3>
<p class="cmp-sub">Finish only: the GSAC and PacWest scored their awards on different point scales over the years, so their published averages are not comparable. The PacWest Academic Achievement Award ranks department GPA and is listed for completeness.</p>
{award_filter("t-cc", cc)}
<div class="rk-wrap"><table class="rk-table" id="t-cc">
<thead><tr>{th("Award","0")}{th("Season","1","num")}{th("Conference","2")}{th("Finish","3","num")}{th("Schools","4","num")}<th scope="col">Source</th></tr></thead>
<tbody>{cc_html}</tbody></table></div>
</section>

{vs_panel}
<div class="cmp-sec" id="rk-related">
<h2 class="cmp-h is-blue">Related</h2>
<div class="cmp-refs"><a class="cmp-link" href="/sports/2012/7/24/hall-of-fame.aspx"><span class="t">Hall of Fame</span><span class="d">Athletes, coaches and teams honored for their contribution to Biola Athletics.</span></a> <a class="cmp-link" href="/sports/2019/6/19/retired-sports.aspx"><span class="t">Retired sports</span><span class="d">Programs Biola once sponsored and no longer does.</span></a> <a class="cmp-link" href="/sports/2013/10/9/GEN_1009130456.aspx"><span class="t">Quick facts</span><span class="d">The eighteen programs Biola sponsors today, plus conference and facility details.</span></a> <a class="cmp-link" href="/sports/2026/9/4/academics-and-athletics.aspx"><span class="t">Academics and athletics</span><span class="d">The classroom record, the support behind it, and what it means for recruits.</span></a></div>
</div>

</div>

<script>
{JS}
</script>

<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@graph": [
    {{
      "@type": "CollegeOrUniversity",
      "@id": "https://www.biola.edu/#organization",
      "name": "Biola University",
      "url": "https://www.biola.edu",
      "description": "Biola University is a Christian university in La Mirada, California, competing in NCAA Division II as a member of the PacWest Conference across eighteen varsity programs."
    }},
    {{
      "@type": "WebPage",
      "name": "Rankings History",
      "description": "Every documented national and regional poll ranking for Biola Athletics, NAIA through NCAA Division II, plus Directors' Cup and conference all-sport finishes.",
      "inLanguage": "en-US",
      "about": {{ "@id": "https://www.biola.edu/#organization" }},
      "isPartOf": {{ "@type": "WebSite", "name": "Biola University Athletics", "url": "https://athletics.biola.edu" }}
    }}
  ]
}}
</script>
"""
# ---------------------------------------------------------------- phones
# Below 700px every table row becomes a card: first cell is the title, the rest are
# "label: value" pairs. Labels come from each table's own header (data-label on every td).
def label_css(html_):
    """Per-table rules: #t-polls td:nth-child(2)::before{content:"Season"} etc., from each table's header."""
    rules = []
    for tid, thead in re.findall(r'<table class="rk-table" id="([^"]+)">\s*<thead>(.*?)</thead>', html_, re.S):
        heads = [re.sub(r"<[^>]+>", "", h).strip() for h in re.findall(r"<th[^>]*>(.*?)</th>", thead, re.S)]
        for i, h in enumerate(heads[1:], start=2):
            rules.append('.biola-cmp #%s td:nth-child(%d)::before{content:"%s"}' % (tid, i, h.replace('"', "'")))
    return "".join(rules)


MOBILE_CSS = ("<style>.biola-cmp .rk-sort{display:none}@media (max-width:700px){"
              ".biola-cmp.js-on .rk-sort{display:flex;flex-basis:100%}"
              ".biola-cmp .rk-table td.is-sorted::before{color:var(--red)}"
              ".biola-cmp .rk-table td.is-sorted{font-weight:700}"
              ".biola-cmp .rk-wrap{border:0;max-height:75vh;overflow-x:hidden}"
              ".biola-cmp .rk-table thead{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}"
              ".biola-cmp .rk-table,.biola-cmp .rk-table tbody{display:block;width:100%}"
              ".biola-cmp .rk-table tr{display:grid;grid-template-columns:1fr 1fr;gap:2px 12px;border:1px solid var(--border);"
              "border-left:4px solid var(--red);border-radius:var(--r-sm);padding:10px 12px;margin:0 0 10px;background:var(--white)}"
              ".biola-cmp .rk-table tbody tr:nth-child(even){background:var(--white)}"
              ".biola-cmp .rk-table tr.is-hidden{display:none}"
              ".biola-cmp .rk-table td{display:block;border:0;padding:2px 0;white-space:normal !important;font-size:14px}"
              ".biola-cmp .rk-table td:first-child{grid-column:1/-1;font-family:var(--fd);font-weight:600;text-transform:uppercase;font-size:16px;padding-bottom:4px}"
              ".biola-cmp .rk-table td:not(:first-child)::before{display:block;font-size:10.5px;font-weight:700;"
              "letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}"
              ".biola-cmp .rk-table td:empty{display:none}"
              ".biola-cmp .rk-table tr.is-total{border-left-color:var(--black);background:#EFEFEF}"
              ".biola-cmp .rk-filters label,.biola-cmp .rk-filters select,.biola-cmp .rk-filters input{width:100%;min-width:0}"
              ".biola-cmp .rk-filters .rk-q{flex-basis:100%}.biola-cmp .rk-count{margin-left:0}"
              "__LABELS__}</style>")


def mobile_css(html_):
    return MOBILE_CSS.replace("__LABELS__", label_css(html_))


# Hosted data (Neil, 2026-09-30): the Sidearm body carries the light page; on load the script
# fetches docs/rankings-data.json (GitHub Pages) and swaps in the current parts. The weekly
# routine only has to update the JSON, never Sidearm.
full = render(VS_TAB, VS_PANEL).encode("ascii", "xmlcharrefreplace").decode("ascii")


def inner(html_, sec_id):
    m = re.search(r'(<section[^>]*id="%s"[^>]*>)(.*?)(</section>)' % sec_id, html_, re.S)
    return m


parts = {}
for sid in ("rk-seasons", "rk-polls", "rk-dept", "rk-vs"):
    m = inner(full, sid)
    parts[sid] = m.group(2) if m else ""
parts["rk-stats"] = re.search(r'<div class="rk-stats">(.*?)</div>\n', full, re.S).group(1)
parts["rk-ones"] = (mobile_css(full) + NOW_HTML + ones_html).encode("ascii", "xmlcharrefreplace").decode("ascii")
parts["rk-asof"] = ASOF

# Light body: the two heavy panels keep their heading and a placeholder until the data arrives.
body = full
for sid, head in (("rk-polls", "Every poll appearance"), ("rk-vs", "Record vs. ranked opponents")):
    m = inner(body, sid)
    if m:
        ph = ('\n<h2 class="cmp-h%s">%s</h2>\n<p class="cmp-sub rk-loading">Loading the full tables&hellip; '
              'If they do not appear, reload the page.</p>\n' % ("" if sid == "rk-polls" else " is-blue", head))
        body = body[:m.start(2)] + ph + body[m.end(2):]
# The script is served from GitHub Pages too, so behavior changes ship without a Sidearm edit.
JS_URL = "https://neilmorgan-beyou.github.io/biola-athletics-rankings/rankings.js"
script_block = "<script>\n%s\n</script>" % JS
assert script_block in body
body = body.replace(script_block, '<script src="%s"></script>' % JS_URL)
preview_body = full
(OUT / "rankings-history-sportfile-body.html").write_text(body)
(OUT / "docs").mkdir(exist_ok=True)
(OUT / "docs" / "rankings.js").write_text(JS)
(OUT / "docs").mkdir(exist_ok=True)
(OUT / "docs" / "rankings-data.json").write_text(json.dumps({"generated": GENERATED, "parts": parts}))
(OUT / "docs" / ".nojekyll").write_text("")
(OUT / "rankings-history-preview.html").write_text(
    '<!doctype html><html lang="en"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    '<title>Rankings History</title><style>body{margin:0;background:#fff;}'
    '.pv{max-width:1180px;margin:0 auto;padding:32px 16px;}</style></head>'
    '<body><div class="pv">' + preview_body + '</div></body></html>')
(OUT / "rankings-merged.json").write_text(json.dumps(
    {"rows": rows, "season_summaries": summ, "games": games, "gaps": gaps, "vs_notes": vs_notes}, indent=1))
print("rows=%d summaries=%d games=%d body=%dKB data=%dKB" % (len(rows), len(summ), len(games), len(body) // 1024,
      len(json.dumps({"generated": GENERATED, "parts": parts})) // 1024))
