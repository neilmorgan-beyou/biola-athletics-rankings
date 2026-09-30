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
    "Men's Golf", "Women's Golf",
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


def rank_num(r):
    """Sort value for a rank: numbers ascend, RV after every number."""
    if isinstance(r, (int, float)):
        return int(r)
    m = re.search(r"(\d+)", str(r or ""))
    return int(m.group(1)) if m else 999


def rank_label(r):
    if r is None or r == "":
        return ""
    t = str(r).strip().upper()
    if t.startswith("RV"):
        return "RV"
    if rank_num(r) == 999:
        return "Ranked"
    return ("T-%d" if t.startswith("T") else "No. %d") % rank_num(r)


# ---------------------------------------------------------------- load
rows, summaries, games, vs_notes, gaps = [], [], [], [], []
FINAL = ["volleyball", "soccer", "basketball", "bat-sports", "xc-track", "other-sports", "vs-ranked"]
for f in (DATA / (n + ".json") for n in FINAL):
    if not f.exists():
        print("missing (not finished yet?):", f.name)
        continue
    d = json.loads(f.read_text())
    rows += d.get("rows", [])
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

# Dedupe poll rows on the fields that identify one published ranking.
seen, uniq = set(), []
conf_rank = {"primary": 0, "biola-news": 1, "secondary": 2}
for r in sorted(rows, key=lambda r: conf_rank.get(r.get("confidence"), 3)):
    k = (r.get("sport"), str(r.get("season")), r.get("poll"), r.get("region"),
         str(r.get("week")), str(r.get("date")), str(r.get("rank")))
    if k in seen:
        continue
    seen.add(k)
    uniq.append(r)
rows = sorted(uniq, key=lambda r: (sport_key(r.get("sport")), -season_start(r.get("season")),
                                    r.get("poll") or "", r.get("date") or ""))

games = [g for g in games if g.get("result") in ("W", "L", "T")]
games.sort(key=lambda g: (sport_key(g.get("sport")), g.get("date") or ""), reverse=False)

# Season summaries: take the agent's where given, fill the rest from rows.
by_season = defaultdict(list)
for r in rows:
    by_season[(r["sport"], str(r["season"]), r.get("poll"), r.get("region"))].append(r)
summ = {}
for (sp, se, poll, region), rs in by_season.items():
    wk = lambda r: str(r.get("week") or "").lower()
    ranked = [r for r in rs if rank_num(r.get("rank")) < 999]
    pre = next((r for r in rs if "pre" in wk(r)), None)
    fin = next((r for r in rs if "final" in wk(r)), None)
    peak = min(ranked, key=lambda r: rank_num(r["rank"])) if ranked else None
    src = (fin or peak or rs[0]).get("source_url")
    summ[(sp, se, poll, region)] = {
        "sport": sp, "season": se, "poll": poll, "region": region,
        "scope": rs[0].get("scope"), "era": rs[0].get("era"),
        "preseason": pre and pre.get("rank"), "peak": peak and peak.get("rank"),
        "final": fin and fin.get("rank"),
        "weeks_ranked": len(ranked) or None, "source_url": src,
    }
for s in summaries:
    k = (s.get("sport"), str(s.get("season")), s.get("poll"), s.get("region"))
    cur = summ.setdefault(k, {"sport": k[0], "season": k[1], "poll": k[2], "region": k[3],
                              "scope": s.get("scope"), "era": s.get("era")})
    for fld in ("preseason", "peak", "final", "weeks_ranked", "source_url"):
        if s.get(fld) not in (None, "") and cur.get(fld) in (None, ""):
            cur[fld] = s[fld]
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
    if g["result"] == "W" and rk < 999 and (s["best"] is None or rk < rank_num(s["best"].get("opponent_rank"))):
        s["best"] = g


def wlt(a):
    return "%d-%d" % (a[0], a[1]) + ("-%d" % a[2] if a[2] else "")


def pct(a):
    n = sum(a)
    return "" if not n else ("%.3f" % ((a[0] + a[2] / 2) / n)).lstrip("0")


# ---------------------------------------------------------------- stats strip
numbered = [r for r in rows if rank_num(r.get("rank")) < 999
            and (r.get("scope") or "").lower() in ("national", "regional")]
seasons_ranked = {(r["sport"], str(r["season"])) for r in numbered}
sports_ranked = {r["sport"] for r in numbered}
national = [r for r in numbered if (r.get("scope") or "").lower() == "national"
            and re.match(r"(NAIA|NCAA)", r.get("era") or "")]
best = min(national, key=lambda r: (rank_num(r["rank"]), season_start(r["season"]))) if national else None
tot = [sum(rec[s]["all"][i] for s in rec) for i in range(3)]
stats = [
    (str(len(sports_ranked)), "Programs ranked nationally or regionally"),
    (str(len(seasons_ranked)), "Team-seasons ranked nationally or regionally"),
    (("No. %d" % rank_num(best["rank"])) if best else "-",
     ("Highest national ranking: %s, %s" % (best["sport"], best["season"])) if best else "Highest ranking"),
    (wlt(tot) if games else "-", "All-time record vs. ranked opponents"),
]

# ---------------------------------------------------------------- render
def opts(values):
    return "".join('<option value="%s">%s</option>' % (e(v), e(v)) for v in values)


sports_present = sorted({r["sport"] for r in rows} | {g["sport"] for g in games}, key=sport_key)
eras = sorted({r.get("era") or "" for r in rows} - {""})
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
        '<td data-v="%s">%s</td><td>%s</td></tr>' % (
            e(s["sport"]), e(s.get("era")), e(s.get("scope")),
            e(s["sport"]), season_start(s["season"]), e(s["season"]),
            e(s.get("era")), e(s.get("poll")) + (" (%s)" % e(s["region"]) if s.get("region") else ""),
            rank_num(s.get("preseason")), e(rank_label(s.get("preseason"))),
            rank_num(s.get("peak")), e(rank_label(s.get("peak"))),
            rank_num(s.get("final")), e(rank_label(s.get("final"))),
            s.get("weeks_ranked") or 0, e(s.get("weeks_ranked") or ""),
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
            rank_num(r.get("rank")), e(rank_label(r.get("rank"))),
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
            rank_num(g.get("opponent_rank")), e(rank_label(g.get("opponent_rank") or "RV")),
            e(g.get("opponent")), e(g.get("location") or ""), g["result"].lower(),
            e(g["result"] + (" " + g["score"] if g.get("score") else "")), e(g.get("event") or "")))

def place_label(r):
    st = (r.get("status") or "").lower()
    if st != "placed":
        lab = st.capitalize() if st else ""
        if r.get("interim") and r.get("place") is not None:
            lab += " (%s at interim)" % ordinal(r.get("place"))
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
        return ("%.2f" % float(v)).rstrip("0").rstrip(".")
    except ValueError:
        return str(v)


def dept_rows(rs, group_key, out_of_key):
    out = []
    for r in sorted(rs, key=lambda r: (-season_start(r.get("season")), r.get("award") or "")):
        placed = (r.get("status") or "").lower() == "placed"
        out.append(
            '<tr data-sport="%s"%s><td>%s</td><td data-v="%d">%s</td><td>%s</td>'
            '<td data-v="%s" class="%s">%s</td><td data-v="%s">%s</td><td data-v="%s">%s</td><td>%s</td></tr>' % (
                e(r.get("award")), '' if placed else ' class="is-quiet"',
                e(r.get("award")), season_start(r.get("season")), e(r.get("season")),
                e(r.get(group_key) or ""),
                r.get("place") if placed and r.get("place") is not None else 999,
                "rk-peak" if placed else "rk-status", e(place_label(r)),
                r.get("points") if placed and r.get("points") not in (None, "") else -1,
                e(fmt_pts(r.get("points")) if placed else ""),
                r.get(out_of_key) or 0, e(r.get(out_of_key) or ""),
                src(r)))
    return "".join(out)


dc = dept.get("directors-cup", {}).get("rows", [])
cc = dept.get("conference-cup", {}).get("rows", [])
dc_html = dept_rows(dc, "body", "schools_scored")
cc_html = dept_rows(cc, "conference", "schools")


def award_filter(tid, rs):
    return (
        '<div class="rk-filters" data-for="%s">'
        '<label><span>Award</span><select data-f="sport"><option value="">All awards</option>%s</select></label>'
        '<p class="rk-count" aria-live="polite"></p></div>' % (tid, opts(sorted({r.get("award") for r in rs if r.get("award")})))
    )


era_sel = '<label><span>Era</span><select data-f="era"><option value="">All eras</option>%s</select></label>' % opts(eras)
scope_sel = '<label><span>Poll type</span><select data-f="scope"><option value="">National and regional</option>%s</select></label>' % opts(scopes)
res_sel = '<label><span>Result</span><select data-f="res"><option value="">All results</option><option value="W">Wins</option><option value="L">Losses</option><option value="T">Ties</option></select></label>'

# Every No. 1 national ranking (NAIA/NCAA), one entry per sport-season, citing the
# strongest source found so a poll-archive citation is distinguishable from a
# Biola self-report.
ones = {}
for r in national:
    if rank_num(r["rank"]) != 1:
        continue
    k = (r["sport"], str(r["season"]))
    if k not in ones or conf_rank.get(r.get("confidence"), 3) < conf_rank.get(ones[k].get("confidence"), 3):
        ones[k] = r
SRC_WORD = {"primary": "poll", "biola-news": "Biola release", "secondary": "other report"}
ones_html = ""
if ones:
    parts = []
    for sp in sorted({k[0] for k in ones}, key=sport_key):
        yrs = sorted((k[1] for k in ones if k[0] == sp), key=season_start)
        cites = ", ".join('%s (<a href="%s">%s</a>)' % (e(y), e(ones[(sp, y)].get("source_url") or ""),
                          SRC_WORD.get(ones[(sp, y)].get("confidence"), "source")) for y in yrs)
        parts.append("<strong>%s</strong> %s" % (e(sp), cites))
    ones_html = '<p class="rk-ones"><span class="k">No. 1 nationally</span> ' + "; ".join(parts) + ".</p>"

stat_html = "".join('<div class="rk-stat"><span class="n">%s</span><span class="l">%s</span></div>' % (e(n), e(l))
                    for n, l in stats)

CSS = (Path(__file__).parent / "rankings.css").read_text()
JS = (Path(__file__).parent / "rankings.js").read_text()

body = f"""
<!-- RANKINGS HISTORY -- Sidearm sport file body. GENERATED by build_rankings_page.py;
     edit the data or the builder, not this file.
     CMS: Hide the sport file title = Yes, Full Width = Yes, sport General.
     Exception to the sibling build rules, same as the FAQ page: one inline script for
     filter/sort. All tables are static HTML; controls stay hidden until the script runs.
     Poll rows: {len(rows)}. Season summaries: {len(summ)}. Games vs ranked: {len(games)}. -->
<style type="text/css">@import url('https://use.typekit.net/awl5tbv.css');
{CSS}
</style>

<div class="biola-cmp rk-app">

<div class="cmp-hero">
<p class="cmp-eyebrow">Program history</p>
<h1>Rankings <span>history</span></h1>
<p class="cmp-lede">Every published national and regional poll ranking we can document for Biola Athletics, the department's Directors' Cup and conference all-sport finishes, from the NAIA era through NCAA Division II, plus each program's record against ranked opponents. Biola University is a Christian university in La Mirada, California, competing in NCAA Division II as a member of the PacWest Conference across eighteen varsity programs.</p>
</div>

<div class="rk-stats">{stat_html}</div>
{ones_html}

<p class="cmp-note"><strong>About this page.</strong> Rankings come from the published polls themselves where an archive survives, and otherwise from Biola Athletics news releases written at the time. "RV" means receiving votes. Ranks shown for opponents are as listed on Biola's schedules at game time. Every entry links to its source, labeled by type: <em>Poll</em> is the published poll itself, <em>Biola</em> is a Biola Athletics release or publication from the time, and <em>Other</em> is another school, conference or media report. Know of a ranking that is missing? Let the athletics communications office know.</p>

<nav class="rk-jump" aria-label="On this page"><a href="#rk-dept">Department standings</a><a href="#rk-seasons">Ranked seasons</a><a href="#rk-polls">Every poll appearance</a><a href="#rk-vs">Record vs. ranked</a><a href="#rk-games">Games vs. ranked</a></nav>

<div class="cmp-sec" id="rk-dept">
<h2 class="cmp-h">Department standings</h2>
<p class="cmp-sub">Biola's finish in the all-sports competitions that score every program together: the Directors' Cup nationally, and each conference's all-sport award. "Did not place" means the final standings exist and Biola is not in them. "Not eligible" covers Biola's three provisional NCAA years, when it could not score. "No data found" means no final standings could be located.</p>
<h3 class="rk-h3">Directors' Cup</h3>
{award_filter("t-dc", dc)}
<div class="rk-wrap"><table class="rk-table" id="t-dc">
<thead><tr>{th("Award","0")}{th("Season","1","num")}{th("Division","2")}{th("Finish","3","num")}{th("Points","4","num")}{th("Schools scored","5","num")}<th scope="col">Source</th></tr></thead>
<tbody>{dc_html}</tbody></table></div>
<h3 class="rk-h3">Conference all-sport award</h3>
<p class="cmp-sub">Score is the conference's published average per sport. The PacWest Academic Achievement Award ranks department GPA and is listed for completeness.</p>
{award_filter("t-cc", cc)}
<div class="rk-wrap"><table class="rk-table" id="t-cc">
<thead><tr>{th("Award","0")}{th("Season","1","num")}{th("Conference","2")}{th("Finish","3","num")}{th("Score","4","num")}{th("Schools","5","num")}<th scope="col">Source</th></tr></thead>
<tbody>{cc_html}</tbody></table></div>
</div>

<div class="cmp-sec" id="rk-seasons">
<h2 class="cmp-h">Ranked seasons</h2>
<p class="cmp-sub">One row per season and poll: preseason, highest and final ranking. Select a column heading to sort.</p>
{filters("t-seasons", era_sel + scope_sel)}
<div class="rk-wrap"><table class="rk-table" id="t-seasons">
<thead><tr>{th("Sport","0")}{th("Season","1","num")}{th("Era","2")}{th("Poll","3")}{th("Preseason","4","num")}{th("Peak","5","num")}{th("Final","6","num")}{th("Weeks","7","num")}<th scope="col">Source</th></tr></thead>
<tbody>{"".join(s_rows)}</tbody></table></div>
</div>

<div class="cmp-sec" id="rk-polls">
<h2 class="cmp-h">Every poll appearance</h2>
<p class="cmp-sub">Each week Biola appeared in a published poll, ranked or receiving votes.</p>
{filters("t-polls", era_sel + scope_sel)}
<div class="rk-wrap"><table class="rk-table" id="t-polls">
<thead><tr>{th("Sport","0")}{th("Season","1","num")}{th("Poll","2")}{th("Type","3")}{th("Week","4")}{th("Date","5")}{th("Rank","6","num")}{th("Record","7")}<th scope="col">Source</th></tr></thead>
<tbody>{"".join(p_rows)}</tbody></table></div>
</div>

<div class="cmp-sec" id="rk-vs">
<h2 class="cmp-h is-blue">Record vs. ranked opponents</h2>
<p class="cmp-sub">All-time, against opponents shown as ranked on Biola's schedule at game time.</p>
<div class="rk-wrap"><table class="rk-table" id="t-vs">
<thead><tr>{th("Sport","0")}{th("Vs. ranked","1","num")}{th("Pct.","2","num")}{th("Vs. top 10","3","num")}{th("Vs. top 5","4","num")}<th scope="col">Highest-ranked win</th></tr></thead>
<tbody>{"".join(v_cards)}</tbody></table></div>
</div>

<div class="cmp-sec" id="rk-games">
<h2 class="cmp-h is-blue">Games vs. ranked opponents</h2>
<p class="cmp-sub">Every result against a ranked opponent.</p>
{filters("t-games", res_sel)}
<div class="rk-wrap"><table class="rk-table" id="t-games">
<thead><tr>{th("Sport","0")}{th("Date","1")}{th("Opp. rank","2","num")}{th("Opponent","3")}{th("Site","4")}{th("Result","5")}{th("Notes","6")}</tr></thead>
<tbody>{"".join(g_rows)}</tbody></table></div>
</div>

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
      "description": "Every documented national and regional poll ranking for Biola Athletics, NAIA through NCAA Division II, and each program's record against ranked opponents.",
      "inLanguage": "en-US",
      "about": {{ "@id": "https://www.biola.edu/#organization" }},
      "isPartOf": {{ "@type": "WebSite", "name": "Biola University Athletics", "url": "https://athletics.biola.edu" }}
    }}
  ]
}}
</script>
"""
body = body.encode("ascii", "xmlcharrefreplace").decode("ascii")
(OUT / "rankings-history-sportfile-body.html").write_text(body)
(OUT / "rankings-history-preview.html").write_text(
    '<!doctype html><html lang="en"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    '<title>Rankings History</title><style>body{margin:0;background:#fff;}'
    '.pv{max-width:1180px;margin:0 auto;padding:32px 16px;}</style></head>'
    '<body><div class="pv">' + body + '</div></body></html>')
(OUT / "rankings-merged.json").write_text(json.dumps(
    {"rows": rows, "season_summaries": summ, "games": games, "gaps": gaps, "vs_notes": vs_notes}, indent=1))
print("rows=%d summaries=%d games=%d body=%dKB" % (len(rows), len(summ), len(games), len(body) // 1024))
