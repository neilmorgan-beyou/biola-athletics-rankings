#!/usr/bin/env python3
"""Scrape Biola Eagles results vs ranked opponents from athletics.biola.edu.

Pipeline per sport:
  1. GET /sports/<slug>/schedule and read the season-selector
     <option value="/sports/<slug>/schedule/<season>"> values (gives the real URL form, 2016 vs 2015-16).
  2. GET each season page. Verify its og:title states that season (a bad season silently serves the
     current one). Pull the schedule_txt.ashx?schedule=NNN id from the page.
  3. GET the text feed, verify its title states the same season, parse it.
  4. Parse the season page's rendered game list (<li class="sidearm-schedule-game ...">).

WHY BOTH: the text feed only shows a rank when the SID typed it into the opponent name
("#9 Alaska Anchorage"). Most rankings on this site live in a separate opponent-ranking field that the
schedule page renders as <span>#15</span> before the opponent link, and the text feed DROPS it.
So rank comes from the HTML (span, or a prefix typed into the name), and the feed is joined in
game-by-game as a cross-check (result, tournament column). Span values containing "seed" are seeds,
not ranks, and are excluded. Games with no W/L/T result are excluded.
"""
import concurrent.futures as cf
import html as htmlmod
import json
import os
import re
import time
import urllib.request

BASE = "https://athletics.biola.edu"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(OUT_DIR, "cache")
os.makedirs(CACHE, exist_ok=True)

SPORTS = [  # slug, display name, season type (for dating games when the page gives no year)
    ("womens-volleyball", "Women's Volleyball", "fall"),
    ("mens-soccer", "Men's Soccer", "fall"),
    ("womens-soccer", "Women's Soccer", "fall"),
    ("mens-basketball", "Men's Basketball", "winter"),
    ("womens-basketball", "Women's Basketball", "winter"),
    ("baseball", "Baseball", "spring"),
    ("softball", "Softball", "spring"),
    ("mens-water-polo", "Men's Water Polo", "fall"),
    ("womens-water-polo", "Women's Water Polo", "spring"),
    ("mens-tennis", "Men's Tennis", "spring"),
    ("womens-tennis", "Women's Tennis", "spring"),
]
MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
LONG_MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
     "November", "December"], 1)}

NAME_PREFIX_RE = re.compile(r"^(?:No\.?\s*(\d{1,2})|#\s?(\d{1,2})|\(?(RV)\)?)\s+(.+)$")
SPAN_RANK_RE = re.compile(r"^(?:No\.?\s*|#\s?)(\d{1,3})$")
BIOLA_RANKED_RE = re.compile(r"(?:No\.\s?(\d{1,2})|#(\d{1,2}))\s+Biola\b")


def fetch(url, cache_name=None, tries=4):
    if cache_name:
        p = os.path.join(CACHE, cache_name)
        if os.path.exists(p):
            return open(p, encoding="utf-8", newline="").read()
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
            if cache_name:
                open(os.path.join(CACHE, cache_name), "w", encoding="utf-8", newline="").write(data)
            return data
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"fetch failed {url}: {last}")


def clean(s):
    return re.sub(r"\s+", " ", htmlmod.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


# ---------------------------------------------------------------- season page (HTML)
def parse_page(h):
    m = re.search(r'<meta name="og:title" content="([^"]*)"', h) or re.search(r"<title>([^<]*)</title>", h)
    title = htmlmod.unescape(m.group(1)).strip() if m else ""
    ids = sorted(set(re.findall(r"schedule_txt\.ashx\?schedule=(\d+)", h)))
    # tournament wrappers: record (start offset, name) so games inside can be tagged
    tourneys = []
    for t in re.finditer(r'<div class="sidearm-schedule-tournament"[^>]*>', h):
        ul = h.find("<ul", t.end())
        if ul < 0:
            continue
        tname = clean(h[t.end():ul])[:200]      # header markup is sometimes malformed (<center>..<p>), so strip it
        depth, end = 0, len(h)
        for u in re.finditer(r"<ul\b|</ul>", h[ul:]):
            depth += 1 if u.group(0) != "</ul>" else -1
            if depth == 0:
                end = ul + u.end()
                break
        tourneys.append((t.start(), end, tname))
    starts = [m.start() for m in re.finditer(r'<li[^>]*class="sidearm-schedule-game[ "]', h)]
    games = []
    for n, s in enumerate(starts):
        e = starts[n + 1] if n + 1 < len(starts) else s + 20000
        b = h[s:e]
        cls = re.search(r'class="([^"]*)"', b).group(1)
        at = "Home" if "sidearm-schedule-home-game" in cls else "Away" if "sidearm-schedule-away-game" in cls \
            else "Neutral" if "sidearm-schedule-neutral-game" in cls else None
        dm = re.search(r'sidearm-schedule-game-opponent-date[^>]*>\s*<span>([^<]*)</span>', b)
        name_div = re.search(r'sidearm-schedule-game-opponent-name">(.*?)</div>', b, re.S)
        nd = name_div.group(1) if name_div else ""
        spans = [clean(x) for x in re.findall(r"<span[^>]*>(.*?)</span>", nd, re.S)]
        spans = [x for x in spans if x]
        a = re.search(r"<a[^>]*>(.*?)</a>", nd, re.S)
        name = clean(a.group(1)) if a else clean(re.sub(r"<span[^>]*>.*?</span>", "", nd, flags=re.S))
        rm = re.search(r'sidearm-schedule-game-result[^"]*">(.*?)</div>', b, re.S)
        res_spans = [clean(x) for x in re.findall(r"<span[^>]*>(.*?)</span>", rm.group(1), re.S)] if rm else []
        res_spans = [x for x in res_spans if x]
        loc = re.search(r'sidearm-schedule-game-location">(.*?)</div>', b, re.S)
        locs = [clean(x) for x in re.findall(r"<span[^>]*>(.*?)</span>", loc.group(1), re.S)] if loc else []
        full = re.search(r"on ([A-Z][a-z]+) (\d{1,2}), (\d{4})", b)  # box score / recap aria-labels
        # which tournament wrapper (if any) contains this game: nearest preceding wrapper whose <ul> hasn't closed
        tname = None
        for off, end, tn in tourneys:
            if off < s < end:
                tname = tn
        games.append({"date_text": clean(dm.group(1)) if dm else "", "at": at, "name": name,
                      "rank_spans": spans, "result_spans": res_spans, "venue": ", ".join(x for x in locs if x) or None,
                      "full_date": (full.group(1), full.group(2), full.group(3)) if full else None,
                      "tournament": tname, "game_id": re.search(r'data-game-id="(\d+)"', b).group(1)
                      if 'data-game-id="' in b else None})
    return {"title": title, "txt_ids": ids, "games": games,
            "biola_ranked": [x.group(0) for x in BIOLA_RANKED_RE.finditer(clean(h))]}


def season_page(slug, season):
    p = os.path.join(CACHE, f"page2_{slug}_{season}.json")
    if os.path.exists(p):
        return json.load(open(p))
    info = parse_page(fetch(f"{BASE}/sports/{slug}/schedule/{season}"))
    json.dump(info, open(p, "w"))
    return info


# ---------------------------------------------------------------- text feed
LINE_RE = re.compile(r"^([A-Z][a-z]{2}) (\d{1,2}) \((\w{3})\)\s+(?:(.*?)\s{2,})?(Home|Away|Neutral)\s{2,}(.*)$")
RESULT_RE = re.compile(r"^([WLT])\b[ ,]*(\d+\s*-\s*\d+)\s*(.*)$")


def parse_feed(text):
    lines = [l for l in text.replace("\r", "").split("\n") if l.strip()]
    title = lines[1].strip() if len(lines) > 1 else ""
    games, started = [], False
    for ln in lines:
        if ln.startswith("Date ") and "Opponent" in ln:
            started = True
            continue
        if not started:
            continue
        m = LINE_RE.match(ln.rstrip())
        if not m:
            games.append({"unparsed": ln})
            continue
        mon, day, _, _t, at, rest = m.groups()
        parts = [x for x in re.split(r"\s{2,}", rest.strip()) if x]
        opp, tail = (parts[0] if parts else ""), parts[1:]
        result = tail.pop() if tail and RESULT_RE.match(tail[-1]) else None
        merged = []
        for t in tail:
            if merged and t.startswith("("):
                merged[-1] += " " + t
            else:
                merged.append(t)
        games.append({"mon": mon, "day": day, "at": at, "opponent_raw": opp,
                      "location": merged[0] if merged else None,
                      "tournament": " ".join(merged[1:]) or None, "result_raw": result})
    return title, games


def title_season(title):
    m = re.match(r"^(\d{4}(?:-\d{2})?) .*Schedule$", title or "")
    return m.group(1) if m else None


def years(label):
    y = int(label[:4])
    return {y, y + 1} if "-" in label else {y}


def game_date(label, mon, day, stype, full=None):
    if full:
        return f"{int(full[2]):04d}-{LONG_MONTHS[full[0]]:02d}-{int(full[1]):02d}"
    m = MONTHS[mon]
    if "-" in label:
        y = int(label[:4]) + (0 if m >= 7 else 1)
    else:
        y = int(label)
        if (stype == "winter" and m >= 7) or (stype == "spring" and m >= 8):
            y -= 1
    return f"{y:04d}-{m:02d}-{int(day):02d}"


STATE_PAREN = re.compile(r"^(?:[A-Z][a-z]{1,5}\.|[A-Z]\.[A-Z]\.|[A-Z]{2}|Iowa|Idaho|Ohio|Utah|Texas|Maine|Calif)$")


def normalize(name):
    cm = re.match(r"^Concordia(?: University)?\s*\((?!Calif)([^)]*)\)", name)
    if cm and STATE_PAREN.match(cm.group(1)):
        return f"Concordia ({cm.group(1)})"                 # Concordia (Ore.)/(Neb.) are not Concordia Irvine
    n = re.sub(r"\s*\([^)]*\)", "", name).strip()          # (Calif.), (SCRIMMAGE), (Round of 16)
    n = re.sub(r"\s+-\s+.*$", "", n)                         # 'Lee TN - NAIA First Round'
    n = re.sub(r"^\d+(st|nd|rd|th)-[Ss]eed\s+", "", n)        # '2nd-Seed Point Loma'
    n = n.replace("Pacifiic", "Pacific")
    n = re.sub(r"\s*\*+$", "", n)
    n = re.sub(r"^University of ", "", n)
    n = re.sub(r"\s+[A-Z]{2}$", "", n) if not re.fullmatch(r"[A-Z ]+", n) else n          # trailing state tags: 'Lewis-Clark State ID'
    n = re.sub(r"\s+(University|College)$", "", n)
    aliases = {"California Baptist": "Cal Baptist", "CSU Los Angeles": "Cal State LA",
               "Cal State Los Angeles": "Cal State LA", "Hawaii Hilo": "Hawai'i Hilo",
               "The Master's": "The Master's", "Masters": "The Master's", "Master's": "The Master's",
               "Point Loma Nazarene": "Point Loma", "Azusa Pacific University": "Azusa Pacific",
               "Westmont College": "Westmont", "Concordia": "Concordia Irvine", "Concordia CA": "Concordia Irvine",
               "Concordia University Irvine": "Concordia Irvine", "Cal State San Marcos": "CSU San Marcos",
               "California State University-San Marcos": "CSU San Marcos", "Texas at Brownsville": "Texas-Brownsville",
               "Hawaii Pacific": "Hawai'i Pacific", "Hawaii-Hilo": "Hawai'i Hilo", "UCSB": "UC Santa Barbara",
               "CSUN": "CSU Northridge", "NAVY": "Navy", "Cal State East Bay": "CSU East Bay",
               "Oregon Institute of Technology": "Oregon Tech", "The College of Idaho": "College of Idaho",
               "Pt. Loma Nazarene": "Point Loma", "Cal State Fullerton": "CSU Fullerton"}
    return aliases.get(n, n).strip()


def rec(gs):
    return tuple(sum(g["result"] == r for g in gs) for r in "WLT")


def id_sweep():
    """Titles of every schedule_txt id on the site, to find a duplicate feed when a page points at an empty one."""
    p = os.path.join(CACHE, "id_sweep.json")
    if os.path.exists(p):
        return json.load(open(p))

    def one(i):
        t = fetch(f"{BASE}/services/schedule_txt.ashx?schedule={i}", f"feed_{i}.txt")
        if t.startswith("Error"):
            return i, None, 0
        title, games = parse_feed(t)
        return i, title, len(games)
    out, i, misses = {}, 1, 0
    with cf.ThreadPoolExecutor(12) as ex:
        while misses < 300:
            for j, t, n in ex.map(one, range(i, i + 100)):
                if t:
                    out[str(j)] = {"title": t, "games": n}
                    misses = 0
                else:
                    misses += 1
            i += 100
    json.dump(out, open(p, "w"), indent=0)
    return out


def main():
    sweep = id_sweep()
    out_games, summary, seasons_scanned, notes, audit = [], [], {}, [], {}
    seed_spans, other_spans = [], []
    for slug, sport, stype in SPORTS:
        sel = fetch(f"{BASE}/sports/{slug}/schedule")
        seasons = sorted(set(re.findall(rf'value="/sports/{slug}/schedule/([0-9]{{4}}(?:-[0-9]{{2}})?)"', sel)))
        if not seasons:
            notes.append(f"{sport}: no season selector found")
            continue
        with cf.ThreadPoolExecutor(8) as ex:
            pages = dict(zip(seasons, ex.map(lambda s: season_page(slug, s), seasons)))
        scanned, rank_seasons, sport_games = [], [], []
        for season in seasons:
            pg = pages[season]
            pts = title_season(pg["title"])
            if not pts or not (years(pts) & years(season)):
                notes.append(f"{sport} {season}: page title '{pg['title']}' is not that season (site served "
                             f"another season); skipped")
                continue
            # ---- text feed (cross-check)
            feed = []
            sid = pg["txt_ids"][0] if pg["txt_ids"] else None
            if len(pg["txt_ids"]) != 1:
                notes.append(f"{sport} {season}: page links txt feed ids {pg['txt_ids']}")
            url = f"{BASE}/services/schedule_txt.ashx?schedule={sid}" if sid else None
            if sid:
                ftitle, feed = parse_feed(fetch(url, f"feed_{sid}.txt"))
                fts = title_season(ftitle)
                if not fts or not (years(fts) & years(season)):
                    notes.append(f"{sport} {season}: feed {sid} title '{ftitle}' wrong season; feed ignored")
                    feed = []
                elif not feed:
                    alts = [k for k, v in sweep.items() if v["title"] == ftitle and v["games"] and k != sid]
                    if alts:
                        notes.append(f"{sport} {season}: page links empty feed {sid} and renders no games; "
                                     f"duplicate feed {alts[0]} ('{ftitle}', {sweep[alts[0]]['games']} games) used")
                        sid = alts[0]
                        url = f"{BASE}/services/schedule_txt.ashx?schedule={sid}"
                        ftitle, feed = parse_feed(fetch(url, f"feed_{sid}.txt"))
                if fts and fts != pts:
                    notes.append(f"{sport}: selector season {season} — page titled '{pg['title']}', "
                                 f"feed titled '{ftitle}'")
                label = fts if fts and "-" in fts else pts
            else:
                label = pts
            scanned.append(season)
            page_url = f"{BASE}/sports/{slug}/schedule/{season}"
            if pg["biola_ranked"]:
                notes.append(f"{sport} {season}: Biola shown ranked on page: {pg['biola_ranked']}")
            hgames = pg["games"]
            use_feed_only = not hgames and feed
            joined = len(hgames) == len(feed)
            if hgames and feed and not joined:
                notes.append(f"{sport} {season}: page has {len(hgames)} games, feed {len(feed)}; joined by date+name")
            rows = []
            if use_feed_only:
                for f in feed:
                    if "unparsed" in f:
                        notes.append(f"{sport} {season}: unparsed feed line '{f['unparsed'].strip()}'")
                        continue
                    rows.append((None, f))
            else:
                for i, g in enumerate(hgames):
                    f = feed[i] if joined else None
                    if not joined and feed:
                        mon_day = " ".join(g["date_text"].split()[:2])
                        cands = [x for x in feed if "mon" in x and f"{x['mon']} {x['day']}" == mon_day
                                 and (x["opponent_raw"].split(" (")[0] in g["name"] or g["name"].split(" (")[0]
                                      in x["opponent_raw"])]
                        f = cands[0] if cands else None
                    rows.append((g, f))
            season_ranked = 0
            for g, f in rows:
                # ---------- rank
                rank, marker, raw_rank = None, None, None
                name = g["name"] if g else f["opponent_raw"]
                for sp in (g["rank_spans"] if g else []):
                    if "seed" in sp.lower() or re.match(r"^#\d+ (East|West|North|South|Central)$", sp):
                        seed_spans.append(f"{sport} {season} {g['date_text']} {name}: '{sp}'")
                        continue
                    m = SPAN_RANK_RE.match(sp)
                    if m:
                        rank, marker, raw_rank = int(m.group(1)), "rank field", sp
                    elif sp.upper().strip("()") == "RV" or sp.upper().startswith("RV/"):
                        marker, raw_rank = "RV (rank field)", sp
                    elif re.match(r"^(?:#\d+/#\d+|(?:NCAA DII|NAIA DII|NAIA|NCAA) (?:No\.\s?|#)\d+|\d{1,2})$", sp):
                        # '#9/#14' (two polls; first listed kept), 'NCAA DII No. 14', 'NAIA #9', bare '15'
                        rank, marker, raw_rank = int(re.search(r"\d+", sp.split("/")[0].replace("DII", "")).group(0)), \
                            "rank field", sp
                    else:
                        other_spans.append(f"{sport} {season} {g['date_text']} {name}: '{sp}'")
                opp = name
                pm = NAME_PREFIX_RE.match(name)
                if pm:
                    opp = pm.group(4)
                    if marker is None:
                        if pm.group(3):
                            marker, raw_rank = "RV (typed in name)", "RV"
                        else:
                            rank, marker, raw_rank = int(pm.group(1) or pm.group(2)), "typed in name", \
                                name[:len(name) - len(opp)].strip()
                if marker is None:
                    continue
                season_ranked += 1
                # ---------- result
                result = score = None
                if g and g["result_spans"]:
                    r0 = g["result_spans"][0].rstrip(",").strip()
                    if r0 in ("W", "L", "T") and len(g["result_spans"]) > 1:
                        result, score = r0, " ".join(g["result_spans"][1:])
                if result is None and f and f.get("result_raw"):
                    rm = RESULT_RE.match(f["result_raw"])
                    result, score = rm.group(1), (re.sub(r"\s", "", rm.group(2)) + " " + rm.group(3)).strip()
                if f and f.get("result_raw") and result:
                    rm = RESULT_RE.match(f["result_raw"])
                    if rm and (rm.group(1) != result or re.sub(r"\s", "", rm.group(2)) not in score.replace(" ", "")):
                        notes.append(f"{sport} {season} {name}: page result '{result} {score}' vs feed "
                                     f"'{f['result_raw']}'")
                if result is None:
                    notes.append(f"{sport} {season}: ranked game vs '{name}' "
                                 f"({g['date_text'] if g else f['mon'] + ' ' + f['day']}) has no result; excluded")
                    continue
                if g:
                    dparts = g["date_text"].split()
                    date = game_date(label, dparts[0][:3], dparts[1], stype, g["full_date"]) \
                        if dparts and dparts[0][:3] in MONTHS else None
                else:
                    date = game_date(label, f["mon"], f["day"], stype)
                paren = re.findall(r"\(([^)]*)\)", opp) + re.findall(r"\s-\s(.*)$", opp) + \
                    re.findall(r"^(\d+(?:st|nd|rd|th)-[Ss]eed)\s", opp)
                paren = [x for x in paren if not STATE_PAREN.match(x.strip())]
                ev = [x for x in [g["tournament"] if g else None, f.get("tournament") if f else None] + paren if x]
                ev = list(dict.fromkeys(ev))
                sport_games.append({
                    "sport": sport, "season": season, "date": date,
                    "opponent": normalize(opp),
                    "opponent_raw": f"{raw_rank} {opp}" if marker == "rank field" or marker.startswith("RV (rank")
                    else name,
                    "opponent_rank": rank, "rank_listed_raw": raw_rank, "rank_source": marker,
                    "location": (g["at"] if g else None) or (f["at"] if f else None),
                    "venue": (g["venue"] if g else None) or (f["location"] if f else None),
                    "result": result, "score": score,
                    "event": "; ".join(ev) or None,
                    "source_url": page_url, "feed_url": url,
                })
            if season_ranked:
                rank_seasons.append(season)
            audit[f"{sport} {season}"] = {"page_games": len(hgames), "feed_id": sid, "feed_games": len(feed),
                                          "ranked_listed": season_ranked}
        seasons_scanned[sport] = scanned
        out_games.extend(sport_games)
        w, l, t = rec(sport_games)
        t10 = rec([g for g in sport_games if g["opponent_rank"] and g["opponent_rank"] <= 10])
        t5 = rec([g for g in sport_games if g["opponent_rank"] and g["opponent_rank"] <= 5])
        rv = rec([g for g in sport_games if g["opponent_rank"] is None])
        summary.append({
            "sport": sport, "wins": w, "losses": l, "ties": t,
            "vs_top10": "-".join(map(str, t10)), "vs_top5": "-".join(map(str, t5)),
            "vs_rv_only": "-".join(map(str, rv)),
            "first_season_with_prefix": rank_seasons[0] if rank_seasons else None,
            "seasons_with_rank_data": rank_seasons,
            "seasons_scanned": f"{scanned[0]} to {scanned[-1]} ({len(scanned)} seasons)" if scanned else "none",
        })
    for srow in summary:
        sc, rs = seasons_scanned[srow["sport"]], srow["seasons_with_rank_data"]
        if rs:
            after = [x for x in sc if x > rs[0] and x not in rs]
            notes.append(f"{srow['sport']}: no rank listings in any season before {rs[0]} "
                         f"({sc.index(rs[0])} seasons); later seasons with none: {', '.join(after) or 'none'}")
        else:
            notes.append(f"{srow['sport']}: no rank listings in any season")
    notes.append("No season page or feed shows Biola itself with a rank (searched for '#N Biola' / 'No. N Biola').")
    out_games.sort(key=lambda g: (g["sport"], g["date"] or ""))
    head = [
        "opponent_rank is the rank Biola's SID entered for the opponent at game time (the site's listing, "
        "usually a national poll rank); it is not verified against the polls.",
        "IMPORTANT: most ranks are in Sidearm's separate opponent-ranking field, rendered on the schedule page "
        "as '#15' before the opponent name. The schedule_txt.ashx text feed DROPS that field and only shows ranks "
        "the SID typed into the opponent name itself. rank_source says which ('rank field' vs 'typed in name'). "
        "Ranks were therefore taken from the season page HTML; the text feed was joined in as a cross-check.",
        "RV = receiving votes; opponent_rank is null and those games are in W-L-T but not in top-10/top-5.",
        "Rank-field values that are tournament seeds ('#3 seed', '#7-seed', DII water polo regional seeds like "
        "'#2 East') were ignored as non-rankings. Dual listings like '#9/#14' keep the first number; 'RV/#1 (D3)' "
        "counts as RV; rank_listed_raw keeps the exact text.",
        "Games with no W/L/T result entered were excluded.",
        "Dates: year taken from the page's box-score/recap labels when present, else inferred from the season.",
    ]
    if seed_spans:
        notes.append(f"{len(seed_spans)} rank-field entries were tournament seeds and ignored: " + "; ".join(seed_spans))
    if other_spans:
        notes.append("Unrecognized rank-field values (not counted): " + "; ".join(other_spans))
    out = {"games": out_games, "summary": summary, "seasons_scanned": seasons_scanned,
           "notes": head + notes, "audit": audit}
    path = os.path.join(OUT_DIR, "vs-ranked.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    print(f"wrote {path}: {len(out_games)} ranked games")
    for s in summary:
        print(f"{s['sport']:20} {s['wins']}-{s['losses']}-{s['ties']:<3} top10 {s['vs_top10']:8} top5 {s['vs_top5']:8} "
              f"RV {s['vs_rv_only']:7} {s['seasons_scanned']}  rank seasons: {','.join(s['seasons_with_rank_data'])}")


if __name__ == "__main__":
    main()
