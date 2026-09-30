#!/usr/bin/env python3
"""Every Biola game (all results, every season) from athletics.biola.edu -> games/all-games.json.

Adapted from ../scrape_vs_ranked.py (which kept only games with a rank marker). This keeps every game with a
W/L/T result and carries NO rank fields (spec SPEC-poll-archive.md section 2).

Pipeline per sport:
  1. GET /sports/<slug>/schedule (fresh) and read the season-selector <option> values. Only those seasons are
     used: a nonexistent season URL silently serves the current season.
  2. Season page: parsed-page cache from the vs-ranked run is reused for past seasons; current seasons
     (start year >= 2026) and anything missing are fetched fresh. The page's og:title must state the season.
  3. Text feed (schedule_txt.ashx) joined game-by-game: supplies the tournament column and the season record
     header ("Overall W-L-T") used for the audit. Its title must state the same season.
Validation: per sport/season, counted W-L-T (non-exhibition) vs the record the site displays -> audit.md.
"""
import concurrent.futures as cf
import html as htmlmod
import json
import os
import re
import time
import urllib.request
from collections import Counter, defaultdict

BASE = "https://athletics.biola.edu"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
OLD_CACHE = ("/private/tmp/claude-502/-Users-neil-morgan/6ca11ac2-0cfd-488e-9532-44728f70a317/scratchpad/"
             "rankings/cache")            # vs-ranked run's cache: reused read-only
CACHE = os.path.join(OUT_DIR, "cache")   # fresh fetches land here
os.makedirs(CACHE, exist_ok=True)
CURRENT_START_YEAR = 2026                # seasons starting 2026+ are always fetched fresh

SPORTS = [  # slug, display name, season type, game_id prefix
    ("womens-volleyball", "Women's Volleyball", "fall", "wvb"),
    ("mens-soccer", "Men's Soccer", "fall", "msoc"),
    ("womens-soccer", "Women's Soccer", "fall", "wsoc"),
    ("mens-basketball", "Men's Basketball", "winter", "mbb"),
    ("womens-basketball", "Women's Basketball", "winter", "wbb"),
    ("baseball", "Baseball", "spring", "bsb"),
    ("softball", "Softball", "spring", "sb"),
    ("mens-water-polo", "Men's Water Polo", "fall", "mwp"),
    ("womens-water-polo", "Women's Water Polo", "spring", "wwp"),
    ("mens-tennis", "Men's Tennis", "spring", "mten"),
    ("womens-tennis", "Women's Tennis", "spring", "wten"),
]
MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
LONG_MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
     "November", "December"], 1)}


def fetch(url, cache_name=None, fresh=False, tries=4):
    if cache_name and not fresh:
        for d in (CACHE, OLD_CACHE):
            p = os.path.join(d, cache_name)
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
    rm = re.search(r"Season Record\s*</?[^>]*>.*?Overall\s*(?:<[^>]+>\s*)*([0-9]+-[0-9]+(?:-[0-9]+)?)",
                   h, re.S)
    page_record = rm.group(1) if rm else None
    tourneys = []
    for t in re.finditer(r'<div class="sidearm-schedule-tournament"[^>]*>', h):
        ul = h.find("<ul", t.end())
        if ul < 0:
            continue
        tname = clean(h[t.end():ul])[:200]
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
        rmm = re.search(r'sidearm-schedule-game-result[^"]*">(.*?)</div>', b, re.S)
        res_spans = [clean(x) for x in re.findall(r"<span[^>]*>(.*?)</span>", rmm.group(1), re.S)] if rmm else []
        res_spans = [x for x in res_spans if x]
        loc = re.search(r'sidearm-schedule-game-location">(.*?)</div>', b, re.S)
        locs = [clean(x) for x in re.findall(r"<span[^>]*>(.*?)</span>", loc.group(1), re.S)] if loc else []
        full = re.search(r"on ([A-Z][a-z]+) (\d{1,2}), (\d{4})", b)
        promo = [clean(x) for x in re.findall(r'sidearm-schedule-game-promotion-name">(.*?)</span>', b, re.S)]
        tname = None
        for off, end, tn in tourneys:
            if off < s < end:
                tname = tn
        games.append({"date_text": clean(dm.group(1)) if dm else "", "at": at, "name": name,
                      "rank_spans": spans, "result_spans": res_spans, "venue": ", ".join(x for x in locs if x) or None,
                      "full_date": (full.group(1), full.group(2), full.group(3)) if full else None,
                      "tournament": tname, "promotion": [x for x in promo if x] or None,
                      "cls": cls, "game_id": re.search(r'data-game-id="(\d+)"', b).group(1)
                      if 'data-game-id="' in b else None})
    return {"title": title, "txt_ids": ids, "games": games, "page_record": page_record}


def season_page(slug, season, fresh):
    """Raw season HTML. The vs-ranked run cached only a parsed subset of each page (no promotion labels such as
    'Scrimmage', no displayed season record), so raw pages are fetched once into games/cache and reused;
    current seasons are always refetched."""
    raw = os.path.join(CACHE, f"raw_{slug}_{season}.html")
    if os.path.exists(raw) and not fresh:
        h = open(raw, encoding="utf-8", newline="").read()
        src = "cache"
    else:
        h = fetch(f"{BASE}/sports/{slug}/schedule/{season}", f"raw_{slug}_{season}.html", fresh=True)
        src = "fresh"
    info = parse_page(h)
    info["_from"] = src
    return info


# ---------------------------------------------------------------- text feed
LINE_RE = re.compile(r"^([A-Z][a-z]{2}) (\d{1,2}) \((\w{3})\)\s+(?:(.*?)\s{2,})?(Home|Away|Neutral)\s{2,}(.*)$")
RESULT_RE = re.compile(r"^([WLT])\b[ ,]*(\d+\s*-\s*\d+)?\s*(.*)$")


def parse_feed(text):
    lines = [l for l in text.replace("\r", "").split("\n") if l.strip()]
    title = lines[1].strip() if len(lines) > 1 else ""
    om = re.search(r"^Overall\s+(\d+-\d+(?:-\d+)?)", text.replace("\r", ""), re.M)
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
        result = tail.pop() if tail and re.match(r"^[WLT]\b", tail[-1]) else None
        merged = []
        for t in tail:
            if merged and t.startswith("("):
                merged[-1] += " " + t
            else:
                merged.append(t)
        games.append({"mon": mon, "day": day, "at": at, "opponent_raw": opp,
                      "location": merged[0] if merged else None,
                      "tournament": " ".join(merged[1:]) or None, "result_raw": result})
    return title, games, (om.group(1) if om else None)


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


# ---------------------------------------------------------------- opponent text
RANK_PREFIX_RE = re.compile(r"^(?:No\.?\s*\d{1,3}|#\s?\d{1,3}|\(?RV\)?)\s+(?=\S)", re.I)
SEED_PREFIX_RE = re.compile(r"^(\(?(?:No\.\s?|#)?\d{1,2}(?:st|nd|rd|th)?[- ]?[Ss]eed\)?)\s+")
# words that make a " - xxx" suffix or a "(xxx)" parenthetical an event annotation rather than part of a school name
EVENT_WORDS = re.compile(
    r"\b(round|rd\.?|final|finals|semi|semifinals?|quarter|quarterfinals?|champ|championships?|tournament|tourney|"
    r"tourn|classic|invitational|invite|shootout|showcase|playoffs?|play-in|regional|regionals|national|nationals|"
    r"naia|ncaa|nccaa|pacwest|gsac|ccaa|wcc|golden\s*state|conference|conf\.?|bracket|pool|seed|game\s*\d|"
    r"day\s*\d|match\s*\d|match|place|elite|sweet|opening|opener|consolation|3rd\s*place|third\s*place|5th|7th|placement|"
    r"exhibition|exh\.?|scrimmage|alumni|senior|homecoming|doubleheader|dh|twin\s*bill|"
    r"forfeit|fft|suspended|completion|continued|resumed|makeup|make-up|rescheduled|postponed|"
    r"cancel+ed|ot|2ot|overtime|innings?|inn|pks?|penalt\w*|shootout|sudden|"
    r"festival|cup|kickoff|tip-off|tipoff|thanksgiving|christmas|holiday|hall\s*of\s*fame|hof|"
    r"game|games|g1|g2|gm\.?\s*\d|hosted)\b", re.I)
STATE_PAREN = re.compile(r"^(?:[A-Z][a-z]{1,5}\.|[A-Z]\.[A-Z]\.|[A-Z]{2}|Iowa|Idaho|Ohio|Utah|Texas|Maine|Calif|"
                         r"Alaska|Hawaii|Guam|Canada|B\.C\.|BC|Alta\.|Ont\.|Mexico|Japan|Korea|China|Taiwan)$")


def split_opponent(name):
    """-> (opponent_raw, [annotations moved to event], rank_prefix_stripped?)"""
    s = name.strip()
    notes = []
    s2 = RANK_PREFIX_RE.sub("", s)
    stripped_rank = s2 != s
    s = s2
    s = re.sub(r"^Biola\s+(?:vs\.?|at)\s+", "", s, flags=re.I)
    um = re.match(r"^(.*?)\s*\(([^()]*)$", s)            # unclosed '(NCCAA West Regional Championship'
    if um and EVENT_WORDS.search(um.group(2)):
        notes.append(um.group(2).strip())
        s = um.group(1)
    sm = SEED_PREFIX_RE.match(s)
    if sm:
        notes.append(sm.group(1).strip("()"))
        s = s[sm.end():]
    # trailing " - Round name" suffix(es)
    while True:
        m = re.match(r"^(.*\S)\s+[-–—]+\s+(.+)$", s)
        if m and EVENT_WORDS.search(m.group(2)):
            notes.insert(0, m.group(2).strip())
            s = m.group(1)
        else:
            break
    # event parentheticals (keep state/school disambiguators like '(Mont.)', '(Calif.)', '(Ore.)')
    def paren(mm):
        inner = mm.group(1).strip()
        if re.match(r"^(?:at|hosted by)\s", inner, re.I):
            notes.append(inner)
            return ""
        if STATE_PAREN.match(inner) or not EVENT_WORDS.search(inner):
            return mm.group(0)
        notes.append(inner)
        return ""
    s = re.sub(r"\s*\(([^()]*)\)", paren, s).strip()
    s = re.sub(r"\s*\*+$", "", s).strip()          # conference-game asterisk
    s = re.sub(r"\s{2,}", " ", s).strip(" -")
    return s, notes, stripped_rank


# ---------------------------------------------------------------- classification
EXHIBITION_RE = re.compile(r"exhibition|scrimmage|\bexh\b|\bexh\.|non-?count|does not count|"
                           r"not count toward", re.I)
# regular-season events whose names contain conference/NAIA/NCAA words
NOT_POSTSEASON_RE = re.compile(r"crossover|challenge|socal classic|forfeits post-season", re.I)
# feed 'Tournament' column sometimes carries spill-over (a location, a state, a result echo, a bare number)
FEED_TOURN_JUNK_RE = re.compile(r"^(?:\d+|[A-Z]{2}|BIOLA|RAIN|[WLT] \d+-\d+.*|\d+ inn\.?,?|.*,\s*[A-Z]{2})$")
ALUMNI_OPP_RE = re.compile(r"^(?:biola\s+)?alumni\b|\balumni game\b", re.I)
# promotion labels worth carrying into event (marketing labels like 'CANNED FOOD DRIVE' are not)
PROMO_EVENT_RE = re.compile(r"scrimmage|exhibition|semifinal|quarterfinal|championship match|consolation|"
                            r"place match|playoff|forfeit|^day \d|round", re.I)
SCORE_QUAL_RE = re.compile(r"^\(?\s*(?:\d?OT|\d+\s*OT|OT\s*\(SD\)|SD|SO|PKs?|PK\s*\d+-\d+|\d+\s*inn\.?(?:ings)?|"
                           r"\d+\s*innings|F/\d+|\d+|overtime|double overtime|walk-?off|shootout|"
                           r"(?:\d+-\d+\s*)?(?:PKs?|penalt\w*|SO)|\d?OT\s*\(\s*SD\s*\)|suspended)\s*\)?$", re.I)


def split_score(t):
    """'77-66 OT' -> ('77-66 OT', []); '0-1 NAIA Region II Quarterfinals' -> ('0-1', ['NAIA Region II ...'])"""
    t = (t or "").strip().strip(",").strip()
    m = re.match(r"^(\d+)\s*-\s*(\d+)\s*(.*)$", t)
    if not m:
        rest = t.strip("- ").strip()
        return None, ([rest] if rest and not re.fullmatch(r"[\d\s,.-]+", rest) else [])
    score, rest = f"{m.group(1)}-{m.group(2)}", m.group(3).strip().strip(",").strip()
    quals, extra = [], []
    for part in [x for x in re.split(r"\s*[;,]\s*|\s+(?=\()", rest) if x.strip()] if rest else []:
        (quals if SCORE_QUAL_RE.match(part.strip()) else extra).append(part.strip())
    if quals:
        score += " " + " ".join(quals)
    return score, extra


def parse_result(spans):
    """Sidearm result block: [prefix-note] 'W,' score [post-note]. -> (result, score, extra notes, raw text)"""
    spans = [x.strip() for x in spans if x and x.strip()]
    rtext = " ".join(spans)
    for i, sp in enumerate(spans):
        m = re.match(r"^([WLT])\b\s*,?\s*(.*)$", sp)
        if m and (not m.group(2) or re.match(r"^\d", m.group(2)) or re.match(r"^-", m.group(2))):
            rest = m.group(2) or " ".join(spans[i + 1:i + 2])
            others = spans[:i] + (spans[i + 2:] if not m.group(2) else spans[i + 1:])
            others = [x.strip(" ,") for x in others if x.strip(" ,") and not re.fullmatch(r"[\d\s,.-]+", x)]
            score, extra = split_score(rest)
            quals = [x for x in others if SCORE_QUAL_RE.match(x)]
            extra += [x for x in others if not SCORE_QUAL_RE.match(x)]
            if quals and score:
                score += " " + " ".join(quals)
            return m.group(1), score, extra, rtext
    return None, None, [], rtext
POSTSEASON_RE = re.compile(
    r"\bnaia\b|\bncaa\b|\bnccaa\b|\bnational championships?\b|\bnational tournament\b|\bnationals\b|"
    r"\bregional(s)?\b|\bsuper regional\b|\bopening round\b|\bsectional\b|"
    r"(pacwest|pac west|pacific west|gsac|golden state|ccaa|calpac|wwpa|western water polo|socal|"
    r"\bconference\b).*(tournament|championships?|playoffs?|semifinals?|quarterfinals?|finals?)|"
    r"(tournament|championships?|playoffs?).*(pacwest|pac west|pacific west|gsac|golden state|ccaa|wwpa|conference)|"
    r"\bnational collegiate\b|\bplayoffs?\b|\bplay-in\b|\bsweet (16|sixteen)\b|\belite (8|eight)\b|\bfinal four\b|"
    r"\bfirst round\b|\bsecond round\b|\bround of (16|32|64)\b", re.I)


def main():
    sweep = json.load(open(os.path.join(OLD_CACHE, "id_sweep.json")))
    all_games, audit_rows, notes, strip_log, dropped = [], [], [], [], []
    seasons_covered = {}
    fresh_pages = 0
    for slug, sport, stype, abbr in SPORTS:
        sel = fetch(f"{BASE}/sports/{slug}/schedule", f"selector_{slug}.html", fresh=True)
        seasons = sorted(set(re.findall(rf'value="/sports/{slug}/schedule/([0-9]{{4}}(?:-[0-9]{{2}})?)"', sel)))
        if not seasons:
            notes.append(f"{sport}: no season selector found")
            continue

        def is_current(s):
            return int(s[:4]) >= CURRENT_START_YEAR

        with cf.ThreadPoolExecutor(6) as ex:
            pages = dict(zip(seasons, ex.map(lambda s: season_page(slug, s, is_current(s)), seasons)))
        covered, sport_games = [], []
        for season in seasons:
            pg = pages[season]
            fresh_pages += pg.get("_from") == "fresh"
            pts = title_season(pg["title"])
            page_url = f"{BASE}/sports/{slug}/schedule/{season}"
            if not pts or not (years(pts) & years(season)):
                notes.append(f"{sport} {season}: page title '{pg['title']}' is not that season; skipped")
                audit_rows.append((sport, season, None, None, None, None, "SKIPPED: page title wrong season"))
                continue
            # ---- text feed
            feed, feed_record, sid, ftitle = [], None, None, None
            sid = pg["txt_ids"][0] if pg["txt_ids"] else None
            if len(pg["txt_ids"]) > 1:
                notes.append(f"{sport} {season}: page links txt feed ids {pg['txt_ids']}; first used")
            label = pts
            if sid:
                ftitle, feed, feed_record = parse_feed(
                    fetch(f"{BASE}/services/schedule_txt.ashx?schedule={sid}", f"feed_{sid}.txt",
                          fresh=is_current(season)))
                fts = title_season(ftitle)
                if not fts or not (years(fts) & years(season)):
                    notes.append(f"{sport} {season}: feed {sid} title '{ftitle}' wrong season; feed ignored")
                    feed, feed_record = [], None
                elif not feed:
                    alts = [k for k, v in sweep.items() if v["title"] == ftitle and v["games"] and k != sid]
                    if alts:
                        notes.append(f"{sport} {season}: page links empty feed {sid}; duplicate feed {alts[0]} "
                                     f"('{ftitle}') used")
                        sid = alts[0]
                        ftitle, feed, feed_record = parse_feed(
                            fetch(f"{BASE}/services/schedule_txt.ashx?schedule={sid}", f"feed_{sid}.txt"))
                if fts and "-" in fts:
                    label = fts
            hgames = pg["games"]
            for f in feed:
                if "unparsed" in f:
                    notes.append(f"{sport} {season}: unparsed feed line '{f['unparsed'].strip()}'")
            feed = [f for f in feed if "unparsed" not in f]
            joined = len(hgames) == len(feed)
            rows = []
            if not hgames and feed:
                rows = [(None, f) for f in feed]
                notes.append(f"{sport} {season}: page renders no games; {len(feed)} feed games used")
            else:
                if hgames and feed and not joined:
                    notes.append(f"{sport} {season}: page has {len(hgames)} games, feed {len(feed)}; "
                                 f"joined by date+name")
                used = set()
                for i, g in enumerate(hgames):
                    f = feed[i] if joined else None
                    if not joined and feed:
                        mon_day = " ".join(g["date_text"].split()[:2])
                        cands = [j for j, x in enumerate(feed) if j not in used and f"{x['mon']} {x['day']}" == mon_day
                                 and (x["opponent_raw"].split(" (")[0] in g["name"] or g["name"].split(" (")[0]
                                      in x["opponent_raw"])]
                        if cands:
                            used.add(cands[0])
                            f = feed[cands[0]]
                    rows.append((g, f))
            season_games = []
            for g, f in rows:
                listed = g["name"] if g else f["opponent_raw"]
                # ---------- result
                result, score, extra, rtext = parse_result(g["result_spans"]) if g else (None, None, [], "")
                if result is None and g and g["result_spans"]:
                    bw = re.match(r"^(?:Biola|Current Team)\s+wins?\s+(\d+\s*-\s*\d+)(.*)$", rtext, re.I)
                    if bw:   # scrimmage / alumni game scored as 'Biola wins 13-12'
                        result, score, extra = "W", *split_score(bw.group(1) + bw.group(2))
                        extra = extra + [f"result listed as '{rtext}'"]
                if result is None and f and f.get("result_raw"):
                    result, score, extra, rtext = parse_result([f["result_raw"]])
                if f and f.get("result_raw") and result and g and g["result_spans"]:
                    fr, fs, _, _ = parse_result([f["result_raw"]])
                    if fr and (fr != result or (fs and score and fs.split()[0] != score.split()[0])):
                        notes.append(f"{sport} {season} {listed}: page result '{result} {score}' vs feed "
                                     f"'{f['result_raw']}' (page used)")
                if g:
                    cm = re.search(r"\bupcoming-game ([A-Z])\b", g.get("cls", ""))
                    if cm and result and cm.group(1) in "WLT" and cm.group(1) != result:
                        notes.append(f"{sport} {season} {listed}: result '{result}' but page CSS class says "
                                     f"'{cm.group(1)}'")
                if result is None:
                    if g and g["result_spans"]:
                        dropped.append(f"{sport} {season} {g['date_text']} '{listed}': result text "
                                       f"'{rtext}' is not a Biola W/L/T result; excluded")
                    continue
                if not score and re.search(r"invitational|tournament|championships|playoffs", listed, re.I) \
                        and not re.search(r"\bvs\.?\s", listed):
                    dropped.append(f"{sport} {season} {g['date_text'] if g else ''} '{listed}': listed as "
                                   f"'{result}' with no score and an event (not an opponent) in the opponent slot; "
                                   f"not a head-to-head game, excluded")
                    continue
                # ---------- date
                if g:
                    dparts = g["date_text"].split()
                    date = game_date(label, dparts[0][:3], dparts[1], stype, g["full_date"]) \
                        if len(dparts) > 1 and dparts[0][:3] in MONTHS else None
                    if date is None and f:
                        date = game_date(label, f["mon"], f["day"], stype)
                else:
                    date = game_date(label, f["mon"], f["day"], stype)
                if date is None:
                    notes.append(f"{sport} {season}: game vs '{listed}' has no parseable date "
                                 f"('{g['date_text'] if g else ''}'); kept with date null")
                # ---------- opponent / event
                opp, ann, rank_stripped = split_opponent(listed)
                if ann or rank_stripped:
                    strip_log.append((sport, listed, opp, ann))
                promo = (g.get("promotion") or []) if g else []
                promo_ev = [x for x in promo if PROMO_EVENT_RE.search(x)]
                ftourn = f.get("tournament") if f else None
                if ftourn and FEED_TOURN_JUNK_RE.match(ftourn.strip()):
                    notes.append(f"{sport} {season} {listed}: feed tournament column '{ftourn}' looks like "
                                 f"spill-over, not an event; ignored")
                    ftourn = None
                ev = [x for x in [g["tournament"] if g else None, ftourn]
                      + ann + promo_ev + extra if x]
                if re.search(r"forfeit|\bfft\b", " ".join([rtext, listed] + ev), re.I) and \
                        not any(re.search(r"forfeit", x, re.I) for x in ev):
                    ev.append("Forfeit")
                ev = list(dict.fromkeys(x.strip() for x in ev if x.strip()))
                event = "; ".join(ev) or None
                blob = " ".join([listed, event or "", rtext] + promo)
                exhibition = bool(EXHIBITION_RE.search(blob)) or bool(ALUMNI_OPP_RE.search(opp))
                postseason = bool(POSTSEASON_RE.search(event or "")) and not exhibition \
                    and not NOT_POSTSEASON_RE.search(event or "")
                season_games.append({
                    "game_id": None, "sport": sport, "season": season, "date": date,
                    "opponent_raw": opp, "opponent_as_listed": listed,
                    "location": (g["at"] if g else None) or (f["at"] if f else None),
                    "result": result, "score": score, "event": event,
                    "postseason": postseason, "exhibition": exhibition, "source_url": page_url,
                })
            # ---------- audit vs displayed record
            counted = Counter(x["result"] for x in season_games if not x["exhibition"])
            mine = f"{counted['W']}-{counted['L']}" + (f"-{counted['T']}" if counted["T"] else "")
            allc = Counter(x["result"] for x in season_games)
            mine_all = f"{allc['W']}-{allc['L']}" + (f"-{allc['T']}" if allc["T"] else "")
            page_rec = pg.get("page_record") if pg["games"] else None
            shown = page_rec or feed_record

            def norm(r):
                if not r:
                    return None
                p = [int(x) for x in r.split("-")] + [0]
                return tuple(p[:3])
            status = "no record shown" if not shown else ("OK" if norm(shown) == norm(mine) else "MISMATCH")
            if page_rec and feed_record and norm(page_rec) != norm(feed_record):
                notes.append(f"{sport} {season}: page shows {pg['page_record']}, feed header {feed_record}")
            audit_rows.append((sport, season, len(season_games), mine, mine_all, shown,
                               status + ("" if not shown else f" (source: {'page' if page_rec else 'feed header'})")))
            if season_games:
                covered.append(season)
            sport_games.extend(season_games)
        # ---------- game ids (doubleheaders get -1, -2 in page order)
        seq = defaultdict(int)
        for x in sport_games:
            key = x["date"] or f"{x['season']}-nodate"
            seq[key] += 1
            x["game_id"] = f"{abbr}-{key}-{seq[key]}"
        seasons_covered[sport] = covered
        all_games.extend(sport_games)

    ids = Counter(g["game_id"] for g in all_games)
    assert all(v == 1 for v in ids.values()), [k for k, v in ids.items() if v > 1]
    json.dump({"games": all_games}, open(os.path.join(OUT_DIR, "all-games.json"), "w"), indent=1,
              ensure_ascii=False)
    # opponents.json
    opp = defaultdict(Counter)
    for g in all_games:
        opp[g["sport"]][g["opponent_raw"]] += 1
    json.dump({s: [{"opponent_raw": k, "games": v} for k, v in sorted(c.items(), key=lambda kv: kv[0].lower())]
               for s, c in opp.items()}, open(os.path.join(OUT_DIR, "opponents.json"), "w"), indent=1,
              ensure_ascii=False)
    json.dump({"audit": audit_rows, "notes": notes, "dropped": dropped, "strip_log": strip_log, "seasons": seasons_covered,
               "fresh_pages": fresh_pages},
              open(os.path.join(CACHE, "_run.json"), "w"), indent=1, ensure_ascii=False)
    write_audit(all_games, audit_rows, notes, dropped, strip_log, seasons_covered)
    tot = Counter(g["sport"] for g in all_games)
    for s in tot:
        print(s, tot[s], seasons_covered[s][0], seasons_covered[s][-1], len(seasons_covered[s]))
    print("mismatches:", sum(1 for r in audit_rows if r[6].startswith("MISMATCH")), "fresh pages", fresh_pages)


# Diagnoses for the seasons whose counted record differs from the site's displayed record. Each was checked
# against the feed header's Home/Away/Neutral split, which pins down the location of the uncounted game(s).
DIAGNOSIS = {
    ("Women's Volleyball", "2003"): "Site Neutral record 11-5 vs 13-5 counted: the two 12/05/2003 NAIA-nationals rows "
        "listed 'W, 1-0' vs Houston Baptist and Saint Mary's NE (both teams Biola had already lost to 0-3 on 12/04) "
        "are not counted by the site. They look like pool-standing entries, not matches. Kept as listed.",
    ("Men's Soccer", "2006"): "Site Home record 5-2-1 vs 5-3-1: the 8/16/2006 home 'L, -' vs Cal Poly Pomona (no score, "
        "preseason, NCAA DII opponent) is not counted by the site, most likely an unlabeled exhibition. Kept as listed "
        "with exhibition=false because no text says exhibition.",
    ("Men's Soccer", "2014"): "Site Home record 4-2-1 vs 5-2-1: one home win is not counted by the site. Candidates: "
        "8/20 University of the Fraser Valley (Canadian, preseason) or 9/9 Antelope Valley (junior college; the only "
        "home win with no opponent-history link). No label on the page, so nothing is flagged.",
    ("Women's Basketball", "2014-15"): "Site Home record 11-8 vs 12-8: one home win is not counted by the site; the page "
        "gives no label that identifies it (candidates are the non-conference home wins: Simpson, Northwest, "
        "Azusa Pacific, La Sierra, Pomona-Pitzer, Bethesda, Evangel). Nothing flagged.",
    ("Women's Basketball", "2022-23"): "Site Away record 5-7 vs 6-7: the 12/19/2022 'W, - ART U Forfeit' at Academy of "
        "Art is a forfeit win the site does not count. Kept as the official result W, event 'Forfeit'.",
}


def write_audit(all_games, audit_rows, notes, dropped, strip_log, seasons_covered):
    L = ["# All-games audit", "",
         "Generated by `scrape_all_games.py`. Source: athletics.biola.edu season schedule pages (season list taken "
         "only from each sport's season selector; every page's own og:title confirmed to state that season) joined "
         "game-by-game with the page's schedule_txt text feed.", "",
         "Check: for every sport/season, W-L-T counted from `all-games.json` (exhibition=false) vs the season record "
         "the site displays (the page's 'Season Record / Overall' box; the text feed's 'Overall' header when the "
         "page renders no games). Game count = rows kept for that season.", ""]
    mism = [r for r in audit_rows if r[6].startswith("MISMATCH")]
    ok = [r for r in audit_rows if r[6].startswith("OK")]
    other = [r for r in audit_rows if not r[6].startswith(("OK", "MISMATCH"))]
    L += [f"**{len(audit_rows)} sport-seasons checked: {len(ok)} match, {len(mism)} mismatch, {len(other)} other.**", ""]
    L += ["## Mismatches", "", "| Sport | Season | Games kept | Counted W-L-T (non-exh.) | Site shows | Diagnosis |",
          "|---|---|---|---|---|---|"]
    for r in mism:
        L.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[5]} | {DIAGNOSIS.get((r[0], r[1]), 'not diagnosed')} |")
    if other:
        L += ["", "## Other", ""] + [f"- {r[0]} {r[1]}: {r[6]}" for r in other]
    L += ["", "## Totals and coverage", "", "| Sport | Games | W-L-T (all rows) | Exhibitions | Postseason | Seasons with games |",
          "|---|---|---|---|---|---|"]
    for sport in dict.fromkeys(g["sport"] for g in all_games):
        gs = [g for g in all_games if g["sport"] == sport]
        c = Counter(g["result"] for g in gs)
        cov = seasons_covered[sport]
        L.append(f"| {sport} | {len(gs)} | {c['W']}-{c['L']}-{c['T']} | {sum(g['exhibition'] for g in gs)} | "
                 f"{sum(g['postseason'] for g in gs)} | {cov[0]} to {cov[-1]} ({len(cov)}) |")
    L += ["", f"Total games: {len(all_games)}.", "",
          "Seasons in the selector with no completed game (future / not started) contribute nothing: "
          + ", ".join(f"{r[0]} {r[1]}" for r in audit_rows if r[2] == 0) + ".", "",
          "Seasons missing from a selector are not on the site as schedule pages (e.g. gaps in early years); none "
          "were guessed, because a nonexistent season URL silently serves the current season.", ""]
    cats = Counter()
    for d in dropped:
        k = ("canceled/postponed/rained out" if re.search(r"cancel|postpon|ppd|rain", d, re.I) else
             "tournament placing row (e.g. '4th Place')" if re.search(r"Place'", d) else
             "event name in opponent slot, no score" if "not a head-to-head" in d else
             "game between two other teams listed on Biola's page (tournament)")
        cats[k] += 1
    L += ["## Rows on the pages that were NOT kept", "",
          "Games with no W/L/T result (future, canceled, postponed) are omitted. Among rows that had some text in "
          "the result slot:", ""] + [f"- {k}: {v}" for k, v in cats.most_common()]
    L += ["", "<details><summary>Full list</summary>", ""] + [f"- {d}" for d in dropped] + ["", "</details>", ""]
    L += ["## Field rules", "",
          "- `opponent_as_listed`: the opponent-name text exactly as on the page (the feed's text for feed-only "
          "seasons). The site's separate opponent-ranking field (rendered '#15' before the name) is NOT included; "
          "a rank typed into the name itself ('#9 Alaska Anchorage') is, since that is the listed text.",
          "- `opponent_raw`: `opponent_as_listed` with a typed rank prefix ('#15', 'No. 15', 'RV') removed, a "
          "'Nth-Seed' prefix removed, a leading 'Biola vs.' removed, a trailing ' - <round/event>' suffix removed "
          "only when the suffix contains event words (round, final, NAIA, GSAC, exhibition, ...), and event "
          "parentheticals such as '(Semifinals)', '(Exhibition)', '(SENIOR NIGHT)', '(hosted by CUI)' removed. "
          "Everything removed goes into `event`. School words are kept: 'Louisiana State - Shreveport', "
          "'Texas at Brownsville', 'Benedictine University at Mesa', state tags like '(Mont.)' / 'CA'. No other "
          "normalization (that is the alias step's job). The site lists a few opponents as 'Unknown' (Baseball "
          "1969, 1979); kept.",
          "- `event`: tournament wrapper name on the page, the feed's Tournament column, the stripped annotations, "
          "relevant promotion labels ('Scrimmage', 'SEMIFINAL', ...), and non-score text from the result slot "
          "(e.g. 'Biola Advances on PKs, 4-3'). Marketing promotions ('CANNED FOOD DRIVE') are not carried.",
          "- `exhibition`: true when the name, event, result text or the page's promotion label says exhibition/"
          "scrimmage, or the opponent is an alumni team. Exhibitions are kept and excluded from the record check.",
          "- `postseason`: true when event text names a conference tournament/championship/playoffs (GSAC, PacWest, "
          "WWPA, CCAA, ...), NAIA / NCAA / NCCAA / National Collegiate tournaments, regionals, nationals or "
          "tournament rounds. Regular-season events that carry those words are excluded: crossovers, 'Challenge' "
          "events, 'NAIA SoCal Classic', 'CSUSM Forfeits Post-Season'. Postseason games with no event text on the "
          "page cannot be detected.",
          "- Forfeits: official result kept, 'Forfeit' (or the site's forfeit wording) in `event`, `score` as listed "
          "(may be null or an on-court score such as the 1999 volleyball 'W 0-3').",
          "- `score`: the listed score with qualifiers the site shows (OT, 2OT, OT (SD), 9 inn., ...). Null when "
          "the site lists a result without a score.",
          "- `game_id`: `<sport>-<date>-<n>`, n = order on the page within that date, so doubleheaders are -1/-2.",
          "- `date`: from the page's box-score/recap aria labels when present, else month/day + season year.",
          "- Seasons 2020 (fall sports) and 2020-21 were played in 2021; dates reflect that.", ""]
    L += ["## Stripped opponent names", "", "| As listed | opponent_raw | moved to event |", "|---|---|---|"]
    for (a, b, c), n in sorted(Counter((x[1], x[2], tuple(x[3])) for x in strip_log).items()):
        L.append(f"| {a} | {b} | {'; '.join(c) or '(rank prefix only)'} |")
    L += ["", "## Scrape notes", ""] + [f"- {n}" for n in notes] + [
        "- Past-season feeds were reused from the vs-ranked run's cache. Its page cache held only a parsed subset "
        "(no promotion labels, no displayed record), so every season page was fetched once as raw HTML into "
        "games/cache; 2026 / 2026-27 / 2027 pages and feeds are always fetched fresh."]
    open(os.path.join(OUT_DIR, "audit.md"), "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
