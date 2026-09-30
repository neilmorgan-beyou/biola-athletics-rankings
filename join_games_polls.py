#!/usr/bin/env python3
"""Verify every Biola opponent's ranking against the published poll in effect on game day.

Usage: python3 join_games_polls.py        (run from the rankings-history folder)

Inputs (see SPEC-poll-archive.md):
  games/all-games.json   every Biola game, no rank fields
  polls/<sport>.json     full national polls, every ranked team, with release dates
  polls/aliases.json     {"<name as printed anywhere>": "<canonical school>"}
Outputs:
  data/vs-ranked-verified.json   one row per game vs a team ranked in the poll in effect
  polls/join-report.md           coverage per sport/season, unmatched names, ambiguities

Rules (Neil, 2026-09-29): a rank counts only if read from the poll itself. Schedule rank
markers are never used. Poll in effect = latest poll of any division that lists the
opponent, released on or before game day, same season; a poll released after the national
tournament (postseason_final) is never "in effect" for games before its release.
"""
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent
SLUG = {
    "Women's Volleyball": "womens-volleyball", "Men's Soccer": "mens-soccer", "Women's Soccer": "womens-soccer",
    "Men's Basketball": "mens-basketball", "Women's Basketball": "womens-basketball",
    "Baseball": "baseball", "Softball": "softball",
    "Men's Water Polo": "mens-water-polo", "Women's Water Polo": "womens-water-polo",
    "Men's Tennis": "mens-tennis", "Women's Tennis": "womens-tennis",
}


# Same-day rule: a poll released ON game day counts only if SAME_DAY is True. Default False
# (conservative: the poll must be public before game day). Pending Neil's decision.
SAME_DAY = True  # Neil, 2026-09-30: a poll released on game day counts


def stale_poll(p, gd, series):
    """True when poll p should not stand for game date gd because the archive is missing the
    poll(s) that came after it. Uses the series' own cadence (median gap between in-season
    polls, preseason excluded): a hole is a gap longer than 1.5x cadence, and p is stale once
    the game is more than cadence + 2 days after it. The preseason poll is never stale."""
    # Post-tournament polls are never "in effect", so they do not close a gap either.
    ds = sorted({d(q["release_date"]) for q in series if not q.get("postseason_final")})
    if len(ds) < 2 or d(p["release_date"]) == ds[0]:
        return False
    gaps = sorted((b - a).days for a, b in zip(ds[1:], ds[2:])) or [7]
    cad = gaps[len(gaps) // 2]
    pd_ = d(p["release_date"])
    nxt = [x for x in ds if x > pd_]
    age = (gd - pd_).days
    if age <= cad + 2:
        return False
    if nxt:
        return (nxt[0] - pd_).days > 1.5 * cad
    return age > 45  # last regular poll stands through the postseason


def season_year(season):
    """Seasons are compared by starting year: the COVID fall-2020 season is "2020" in the
    polls but "2020-21" on some Biola pages."""
    m = re.match(r"(\d{4})", str(season or ""))
    return m.group(1) if m else str(season)


def d(s):
    try:
        return date.fromisoformat(str(s)[:10])
    except (TypeError, ValueError):
        return None


STATES = {
    "calif": "ca", "cal": "ca", "ca": "ca", "ariz": "az", "az": "az", "ore": "or", "or": "or", "wash": "wa",
    "wa": "wa", "ky": "ky", "tenn": "tn", "tn": "tn", "ind": "in", "ill": "il", "mich": "mi", "kan": "ks",
    "kans": "ks", "neb": "ne", "okla": "ok", "tex": "tx", "texas": "tx", "fla": "fl", "ga": "ga", "ala": "al",
    "sc": "sc", "nc": "nc", "va": "va", "wva": "wv", "pa": "pa", "ohio": "oh", "iowa": "ia", "mo": "mo",
    "mont": "mt", "idaho": "id", "utah": "ut", "colo": "co", "nm": "nm", "nev": "nv", "sd": "sd", "nd": "nd",
    "minn": "mn", "wis": "wi", "miss": "ms", "la": "la", "ark": "ar", "hawaii": "hi", "bc": "bc", "md": "md",
    "ny": "ny", "nj": "nj", "mass": "ma", "conn": "ct", "vt": "vt", "nh": "nh", "maine": "me", "ri": "ri",
    "del": "de", "dc": "dc", "wyo": "wy", "alaska": "ak", "ont": "on", "mn": "mn", "il": "il", "mi": "mi",
    "tx": "tx", "ok": "ok", "ks": "ks", "ne": "ne", "fl": "fl", "co": "co", "ut": "ut", "id": "id", "mt": "mt",
}
STATES.update({"newyork": "ny", "newjersey": "nj", "newmexico": "nm", "newhampshire": "nh", "northcarolina": "nc",
               "southcarolina": "sc", "northdakota": "nd", "southdakota": "sd", "westvirginia": "wv", "virginia": "va",
               "california": "ca", "arizona": "az", "oregon": "or", "washington": "wa", "kentucky": "ky",
               "tennessee": "tn", "indiana": "in", "illinois": "il", "michigan": "mi", "kansas": "ks", "nebraska": "ne",
               "oklahoma": "ok", "florida": "fl", "georgia": "ga", "alabama": "al", "pennsylvania": "pa",
               "missouri": "mo", "montana": "mt", "colorado": "co", "nevada": "nv", "minnesota": "mn",
               "wisconsin": "wi", "mississippi": "ms", "louisiana": "la", "arkansas": "ar", "maryland": "md",
               "massachusetts": "ma", "connecticut": "ct", "vermont": "vt", "delaware": "de", "wyoming": "wy"})
STATES.update({c: c for c in "ak al ar az ca co ct dc de fl ga hi ia id il in ks ky ma md me mi mn mo ms mt nc nd ne nh nj nm nv ny oh ok or pa ri sc sd tn tx ut va vt wa wi wv wy bc".split()})
COMMON = set("california state pacific saint north south east west new university college of and a".split())
POSTAL = set("bc ak al ar az ca co ct dc de fl ga hi ia id il in ks ky ma md me mi mn mo ms mt nc nd ne nh nj nm nv ny oh ok or pa ri sc sd tn tx ut va vt wa wi wv wy".split())
EXPAND = [  # applied to both sides, in order
    (r"^ucla$", "california los angeles"), (r"^usc$", "southern california"), (r"^ucsb$", "california santa barbara"),
    (r"^csun$", "california state northridge"), (r"^uc ", "california "), (r"^csu ", "california state "),
    (r"^cal state ", "california state "), (r"^cal ", "california "), (r"^st ", "saint "), (r" st$", " state"),
(r"^california st ", "california state "), (r"^pt ", "point "),     (r"^liu$", "long island"), (r"^(california state) (la|l a)$", r"\1 los angeles"), (r"^fiu$", "florida international"),
]
# Base names shared by several schools: never matched without an explicit alias or equal state tags.
AMBIGUOUS = {"concordia", "bethel", "union", "westminster", "saint marys", "trinity", "wesleyan", "columbia",
             "cornerstone", "olivet", "saint francis", "hope", "northwestern", "loyola", "saint thomas", "grace",
             "providence", "georgetown", "william penn", "lincoln", "bethany", "friends", "cumberland",
             "cumberlands", "saint mary", "midland", "dominican", "ottawa", "embry riddle", "anderson", "saint marys", "saint joseph", "saint josephs", "pacific", "california", "benedictine", "biola"}


SYSTEM_NAMES = {"california state", "california state university", "california state poly", "cal poly",
                "california state polytechnic", "california state polytechnic university", "cal state poly",
                "california st polytechnic univ", "california polytechnic", "texas a and m", "university of california"}


def strip_city(name):
    """WBCA prints 'School - City'. Drop the city unless the left side is only a system name
    ('California State University - Bakersfield' keeps Bakersfield)."""
    m = re.match(r"^(.*?)\s+-\s+(.+)$", name or "")
    if not m:
        return name
    left, right = m.group(1), m.group(2).strip()
    if right.startswith("["):
        return left
    rw = set(re.sub(r"[^a-z ]+", " ", right.lower()).split())
    lw = set(re.sub(r"[^a-z ]+", " ", left.lower()).split())
    if re.sub(r"[^a-z]", "", right.lower()) in STATES:
        return "%s (%s)" % (left, right)
    return left if rw and rw <= lw else left + " " + right


def split_tag(name):
    """-> (base key, state code or None)."""
    n = (name or "").lower().replace("\u2019", "'").replace("\u2018", "'").replace("\u02bb", "'").replace("&", " and ")
    tag = None
    n = re.sub(r"\s*\((?:i|ii|iii|iv|v|vi|vii|viii|ix|x|xi|xii)\)\s*$", "", n)  # NAIA region codes
    n = re.sub(r"\s*\((?:m|w)\)\s*$", "", n)  # ITA gender suffix
    n = re.sub(r"\s*\((if necessary|dh|tie)\)", "", n)
    n = re.sub(r"^\s*\(tie\)\s*", "", n)
    m = re.search(r"\(([^)]*)\)\s*$", n)
    if m:
        t = re.sub(r"[^a-z]", "", m.group(1))
        if t in STATES:
            tag = STATES[t]
            n = n[:m.start()]
        else:  # a note, not a state: "(BIOLA WEEKEND)"; but "(Irvine)" on a shared name is a campus
            inner = m.group(1)
            n = n[:m.start()]
            if re.sub(r"[^a-z ]", "", n.replace("university", "").replace("college", "")).strip() in AMBIGUOUS:
                n = n + " " + inner
            m = re.search(r"\(([^)]*)\)\s*$", n)
            if m and re.sub(r"[^a-z]", "", m.group(1)) in STATES:
                tag = STATES[re.sub(r"[^a-z]", "", m.group(1))]
                n = n[:m.start()]
    if not tag:  # "Chico State, Calif.", "Dominican, N.Y."
        m3 = re.search(r",\s*([a-z.' ]{2,10})$", n)
        if m3 and re.sub(r"[^a-z]", "", m3.group(1)) in STATES:
            tag = STATES[re.sub(r"[^a-z]", "", m3.group(1))]
            n = n[:m3.start()]
    if not tag:  # "Doane NE", "Lee TN": bare postal code at the end (not LA: "Cal State LA")
        m2 = re.search(r"\s([A-Za-z]{2})\s*$", name or "")
        if m2 and m2.group(1).isupper() and m2.group(1).lower() in POSTAL and len(n.split()) > 1:
            tag = m2.group(1).lower()
            n = n[:m2.start()]
    n = re.sub(r"\bcollege of\b", "collegeof", n)
    n = re.sub(r"\b(university|universtiy|univ|college|colleges|the|at)\b", " ", n)
    n = re.sub(r"'", "", n)
    n = re.sub(r"[^a-z0-9]+", " ", n).strip()
    n = re.sub(r"^of ", "", n).strip()
    for pat, rep in EXPAND:
        n = re.sub(pat, rep, n)
    return re.sub(r"\s+", " ", n).strip(), tag


def key(name):
    b, t = split_tag(name)
    return b + ("|" + t if t else "")


def main():
    games = json.loads((HERE / "games/all-games.json").read_text())["games"]
    alias_file = json.loads((HERE / "polls/aliases.json").read_text()) if (HERE / "polls/aliases.json").exists() else {}
    loose_log = []
    stale = defaultdict(int)
    near_miss = defaultdict(set)

    def resolver(sport, side="game"):
        """Sport-scoped aliases describe Biola's schedule names only; poll names get global aliases."""
        table, exact = {}, {}
        for k, v in alias_file.get("_global", {}).items():
            table[key(k)] = key(v)
        # Sport-scoped aliases match the name exactly as written (case/space-insensitive),
        # so 'Concordia' does not also catch 'Concordia University' or 'Concordia - MN'.
        for scope in ((sport,) if side == "game" else ("_poll:" + sport,)):
            for k, v in alias_file.get(scope, {}).items():
                exact[" ".join(k.lower().split())] = key(v)
        norm = lambda n: " ".join((n or "").lower().split())
        return lambda n: exact.get(norm(n)) or table.get(key(n), key(n))

    report, out = [], []
    unmatched_poll_names = defaultdict(set)
    for sport, slug in SLUG.items():
        pf = HERE / "polls" / (slug + ".json")
        sg = [g for g in games if g["sport"] == sport and not g.get("exhibition")]
        if not pf.exists():
            report.append(f"## {sport}\nNo poll archive yet; {len(sg)} games unverified.\n")
            continue
        pfile = json.loads(pf.read_text())
        polls = pfile["polls"]
        # Seasons whose full poll schedule is confirmed (NAIA week-by-week PDFs): a gap there is
        # a real break in the schedule, so the older poll stays in effect.
        complete = {(dv, str(se)) for dv, ses in (pfile.get("schedule_complete") or {}).items() for se in ses}
        undated = [p.get("poll_id") or p.get("week") for p in polls if not d(p.get("release_date"))]
        canon = resolver(sport)
        pcanon = resolver(sport, "poll")

        def same(opp_name, team_name, _c=canon, _p=pcanon):
            a, b = _c(opp_name), _p(strip_city(team_name))
            if a == b:
                return a.split("|")[0] not in AMBIGUOUS or "|" in a
            ab, at = (a.split("|") + [None])[:2]
            bb, bt = (b.split("|") + [None])[:2]
            if ab != bb or ab in AMBIGUOUS or (at and bt and at != bt):
                return False
            loose_log.append((sport, opp_name, team_name))
            return True
        by_season = defaultdict(list)
        for p in polls:
            if d(p.get("release_date")):
                by_season[season_year(p["season"])].append(p)
        for ps in by_season.values():
            ps.sort(key=lambda p: p["release_date"])
        seasons_games = defaultdict(list)
        for g in sg:
            seasons_games[season_year(g["season"])].append(g)
        known = {canon(g["opponent_raw"]).split("|")[0] for g in sg}
        lines = [f"## {sport}"]
        for season in sorted(seasons_games):
            gs, ps = seasons_games[season], by_season.get(season, [])
            if not ps:
                lines.append(f"- {season}: no polls archived; {len(gs)} games unverified")
                continue
            hits = 0
            for g in gs:
                gd = d(g.get("date"))
                if not gd:
                    continue
                opp = canon(g["opponent_raw"])
                # Latest poll of each division released on or before game day.
                latest = {}
                for p in ps:
                    if d(p["release_date"]) < gd or (SAME_DAY and d(p["release_date"]) == gd):
                        latest[p["division"]] = p
                # A poll older than its successor's release (a hole in the archive) is not
                # "in effect": drop it unless the game is within a week of it.
                for dv, p in list(latest.items()):
                    if (dv, str(p["season"])) in complete:
                        continue
                    if stale_poll(p, gd, [q for q in ps if q["division"] == dv]):
                        del latest[dv]
                        stale[sport] += 1
                found = [(p, t) for p in latest.values() for t in p.get("teams", []) if same(g["opponent_raw"], t["team_raw"])]
                if not found:
                    ob = set(canon(g["opponent_raw"]).split("|")[0].split()) - COMMON
                    for p in latest.values():
                        for t in p.get("teams", []):
                            tb = set(canon(t["team_raw"]).split("|")[0].split()) - COMMON
                            if ob and tb and len(ob & tb) >= max(1, min(len(ob), len(tb)) - 0):
                                near_miss[sport].add((g["opponent_raw"], t["team_raw"]))
                    continue
                if len(found) > 1:
                    lines.append(f"  - AMBIGUOUS {g.get('game_id')}: {g['opponent_raw']} ranked in "
                                 + ", ".join(f"{p['poll']} #{t['rank']}" for p, t in found) + "; not counted")
                    continue
                p, t = found[0]
                hits += 1
                out.append({**{k: g.get(k) for k in ("game_id", "sport", "season", "date", "opponent_raw",
                                                      "location", "result", "score", "event", "postseason",
                                                      "source_url")},
                            "opponent_rank": t["rank"], "tied": bool(t.get("tied")),
                            "poll": p["poll"], "poll_id": p.get("poll_id"), "poll_team_raw": t["team_raw"],
                            "poll_division": p["division"], "poll_week": p.get("week"),
                            "poll_release_date": p["release_date"], "poll_source_url": p.get("source_url"),
                            "poll_confidence": p.get("confidence")})
            first, last = ps[0]["release_date"], ps[-1]["release_date"]
            incomplete = sum(1 for p in ps if not p.get("complete", True))
            lines.append(f"- {season}: {len(ps)} polls ({first} to {last}{', %d incomplete' % incomplete if incomplete else ''}); "
                         f"{hits} of {len(gs)} games vs ranked")
        for p in polls:
            for t in p.get("teams", []):
                if canon(t["team_raw"]).split("|")[0] not in known and t["team_raw"]:
                    unmatched_poll_names[sport].add(t["team_raw"])
        if undated:
            lines.append(f"- {len(undated)} polls have no release date and were not used: {', '.join(map(str, undated[:12]))}")
        report.append("\n".join(lines) + "\n")
    (HERE / "data/vs-ranked-verified.json").write_text(json.dumps({"games": out}, indent=1, ensure_ascii=False))
    (HERE / "polls/join-report.md").write_text(
        "# Game / poll join report\n\n" + "\n".join(report) +
        "\n## Loose matches (same base name, state tag on one side only) -- check these\n\n" +
        "\n".join(sorted({f"- {sp}: '{o}' = '{t}'" for sp, o, t in loose_log})) +
        "\n\n## Near misses: opponent vs a ranked team with a similar name in the poll in effect (alias needed?)\n\n" +
        "\n".join(f"- {sp}: '{o}' ~ '{t}'" for sp, v in near_miss.items() for o, t in sorted(v)) +
        "\n\n## Poll teams whose name matches NO Biola opponent (a ranked opponent hiding here means a missing alias)\n\n" +
        "\n".join(f"- {sp}: " + "; ".join(sorted(v)) for sp, v in unmatched_poll_names.items()) + "\n")
    print("verified games vs ranked:", len(out))


if __name__ == "__main__":
    main()
