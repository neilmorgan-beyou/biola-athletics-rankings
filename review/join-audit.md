# Join audit: join_games_polls.py + polls/aliases.json

Reviewed 2026-09-30. I changed no project files. Probes, frozen copies and sandbox runs are in `review/scratch-join/`.

## Which version I audited

The script and aliases changed on disk **while I was reviewing**:

| Version | Script | Aliases | Output |
|---|---|---|---|
| v0403 (the version I started on) | 04:03 | 04:03 | 1800 rows |
| v0415 | 04:15 (added full state names, `ottawa` in AMBIGUOUS, `strip_city`, sport aliases on the game side only) | 04:15 | 1777 rows |
| **v0417 (current)** | 04:17 (a campus in parentheses on an AMBIGUOUS name, `_poll:<sport>` alias scope) | 04:17:49 | **1804 rows** |

`review/scratch-join/run_version.sh` runs any version in a sandbox, so the real `data/` and `polls/` are never written. The v0417 sandbox run matches the current `data/vs-ranked-verified.json` and `polls/join-report.md` byte for byte (checked at 04:18). `join_v0417_instr.py` is the same code plus two probe fields (`_team_raw`, `_poll_id`) on each row, so every row can be traced to the poll name it matched. With those two fields removed, its rows equal the shipped rows.

A note on the probes. `p_join.py`, `p_fixes.py`, `p_stale.py`, `p_weekgap.py` and `p_prefirst.py` import whichever `join_games_polls.py` is live, and I ran them before 04:15. The poll-in-effect logic has not changed since, and I re-checked the stale rows in #1 against the v0417 output. The probes that start from `cur.py` (`p_drops2.py`, `p_sameday.py`) are pinned to the v0417 snapshot.

### Found in v0403, fixed by v0417 (I checked each in the current output)

| Game | v0403 record | Cause | v0417 |
|---|---|---|---|
| mten-2019-02-28-1, mten-2019-04-04-1 `Concordia` | #20, #35 | ITA `Concordia College (New York)`. `(New York)` was not in STATES, so it was stripped as a note. The name became plain `concordia`, and the sport alias (then applied to both sides) turned it into Concordia Irvine | removed ✔ |
| mten-2020-02-13-1 `Concordia Irvine` | #17 | same | removed ✔ |
| wbb-2004-01-22-1, wbb-2004-01-27-1 `Concordia University, CA` | #16 | WBCA `Concordia (Saint Paul)`: the parenthetical was stripped as a note, and the WBB sport alias `Concordia` gave Concordia Irvine. Irvine was NAIA in 2003-04 | removed ✔ |
| wsoc-2017-11-11-1 `Ottawa` (NCCAA West Regional, home) | #13 | Loose rule matched it to `Ottawa (Kan.)`. Biola's other NCCAA West regional opponent is `Ottawa (Ariz.)` (wvb-2018-11-06-2), and Ottawa (Ariz.) plays in the GSAC | removed ✔ |
| mten-2021-02-12-1, mten-2021-04-08-1 | dropped as AMBIGUOUS | `Concordia University (Irvine)` and `Concordia College (New York)` both became Concordia Irvine in the same poll | now counted ✔ |
| 21 softball 2023-26 `Concordia` games | v0415 dropped them when it removed sport aliases from poll names. The NFCA name `Concordia` in those polls is Irvine: the records line up week to week, and the file notes say the NFCA's live database renamed Irvine | restored by `_poll:Softball` ✔ |

The v0403-era evidence is in `review/scratch-join/p_concordia.py`, `p_fixes.py` (the counterfactual that treats spelled-out states as tags) and `hits.json`.

---

## Open defects in the current version, most severe first

### 1. HIGH: the join fills missing poll weeks with an older poll (breaks the spec rule "a missing week is a gap, not a guess")

**Defect.** The poll in effect is simply the latest archived poll of a division released on or before game day. No check limits how old that poll can be. When the archive is missing weeks, the join quietly uses the last poll it has.

**Evidence** (`p_weekgap.py`, `p_stale.py`). These games were joined across a gap in the week numbers:

| Game | Rank used | Poll used | Next archived poll | Poll age |
|---|---|---|---|---|
| mbb-2011-01-14-1 Concordia CA | #5 | NAIA DI Week 2 (2010-12-13) | Week 6 (2011-01-31) | 32 d |
| wbb-2004-12-29-1 South Dakota Tech | #19 | NAIA DII Week 1 (2004-12-07) | Week 3 | 22 d |
| msoc-2011-10-15-1 Azusa Pacific | #5 | NAIA Week 5 | Week 7 | 11 d |
| wbb-2002-12-14-1 Lewis-Clark State | #20 | NAIA DI Week 1 | Week 3 | 11 d |
| wbb-2003-03-01-1 The Master's | #14 | NAIA DI Week 9 | Week 11 | 11 d |

The archive's own `gaps` list records the MBB 2010-11 hole: "no poll found between 2010-12-13 and 2011-01-31 (49 days) - possible missing poll(s)". The join ignores that list.

Some series simply stop early:
- bsb-2001-05-25, -26, -28 use NAIA Week 7 (2001-05-01), 24 to 27 days before the games.
- bsb-2003-05-23 is 16 days stale.
- In softball 2009, four NFCA DII polls after April 22 are missing, including the final.

`p_stale.py` lists 101 rows older than the normal release interval. Most are the NAIA "Final Regular Season" poll correctly carried into nationals. The rows above are the ones where a newer poll existed but is not archived.

**Effect.** At least 5 rows, and up to about 10, show a rank from a poll that was not in effect. The opponent may have had a different rank or been unranked. Ranked opponents in the missing weeks are dropped silently.

**Fix.**
- A poll stays in effect only until its next expected release: the series' median interval plus a few days' grace.
- It is also cut off at any gap listed in the file's `gaps` for that division and season.
- A game after that point becomes "unverified: poll gap", and the report lists it by season.

### 2. HIGH (22 rows) / needs a decision (229 rows): release dates that are schedules, and games on release day

**Defect.**
- Men's and women's soccer NAIA polls often take `release_date` from the "NAIA published ratings calendar", a preseason schedule, not the actual publish date.
- The rule is `release_date <= game date`, so a poll dated on game day always wins over the previous poll.

**Evidence** (`p_sameday.py`, `sameday.txt`).
- 22 rows use a calendar-dated poll 0 to 3 days before the game. In 14 of them the previous poll gives a different answer:
  - msoc-2013-09-19-1 CSUSM #22 and msoc-2014-10-01-1 Westmont #25 were unranked in the previous poll.
  - wsoc-2014-09-30-1 Westmont is #8 (previous poll #2).
  - wsoc-2014-11-04-1 Concordia is #20 (previous poll #15).
  - …
- Across all sports, 229 rows use a poll released on game day. If the previous poll were the one in effect, 129 would change rank and 23 would disappear.

**Effect.** For calendar-dated polls the order of poll and game is unknown. The same-day rule follows the spec (`<=`), but it decides about 13% of all rows.

**Fix.** For polls whose date basis is a calendar, `approximate`, a Wayback upper bound or "records as of", require `release_date < game date`, or mark the row `poll_timing: uncertain`. Neil should decide the same-day rule explicitly, for example "the poll counts from the day after release".

### 3. MEDIUM: aliases match normalized keys, not the names as written, so they cover more than they say

**Defect.** `resolver` stores `key(alias_name)`. `key()` removes `university`, `college`, `the` and notes that are not states, so one alias catches every name that normalizes the same way.

**Evidence** (probe in the transcript, reproducible with `cur.py`):
- In Women's Soccer the game-side names `Concordia University`, `Concordia College` and `The Concordia` all become `concordia irvine`.
- `_open_questions` says Women's Soccer `Concordia University` (wsoc-2017-12-01-1, NCCAA semifinal) is **not aliased** because it may be a different Concordia. It *is* aliased, through the `Concordia` entry. The only reason no row came out is that Irvine was unranked that week. The NAIA poll in effect had `Concordia (Neb.)` at #21.
- On the poll side, `_poll:Softball` `Concordia` also captures `Concordia University`, `Concordia College`, and (through `strip_city`, see #4) NFCA 2005 `Concordia - MN`, which is Concordia-St. Paul. It becomes Concordia Irvine. The `_notes` evidence covers only the 2018-2026 NFCA polls, but the alias has no season limit. Biola's 2005 Concordia games (March and April) come before that poll (2005-06-13), so no row is wrong today.

**Fix.**
- Match aliases on the exact raw string (after trimming whitespace and quote marks), not on `key()`.
- Let aliases carry an optional season range (`"Concordia": {"to": "Concordia Irvine", "seasons": "2018-2026"}`).
- Fix `_open_questions` and `_notes` to match what the code actually does.

### 4. MEDIUM (latent, added in v0415): `strip_city` merges campuses and drops state tags

**Defect.** For a poll name of the form `X - Y`, `strip_city` keeps `X` unless `X` is in `SYSTEM_NAMES`. Three problems:
- The `SYSTEM_NAMES` check normalizes `&` to a space, so `texas a&m` becomes `texas a m`, which never equals `texas a and m`. Every Texas A&M campus loses its campus name.
- A state after the dash is thrown away: `Concordia - MN` becomes `Concordia`.
- A campus of a university system collapses to the flagship.

**Evidence** (`strip_city` probe in the transcript):

| Poll name | Key after `strip_city` |
|---|---|
| `Texas A&M - Commerce`, `- Kingsville`, `- Victoria`, `- Texarkana` | `texas a and m` |
| `Colorado - Colorado Springs`, `University of Colorado - Colorado Springs` | `colorado`, which equals Biola's `Colorado College` |
| `Colorado State - Pueblo` | `colorado state` |
| `Missouri - St. Louis` | `missouri` |
| `Nebraska - Kearney` | `nebraska` |
| `Texas - Tyler` | `texas` |
| `University of Alaska - Anchorage` | `alaska` |
| `Montana State University - Billings` | `montana state` |
| `Minnesota State University - Mankato` | `minnesota state` |
| `Hawai'i - Hila` | `hawaii` |
| `University of South Carolina - Beaufort` / `- Aiken` | `south carolina` |
| `Houston - Victoria (TX)` | `houston` |
| `California State Poly University - Pomona` | `california state poly` |

Biola has played `Texas A&M` (bsb 1988), `Colorado College` (wbb 1980, sb 1996), `Alaska Anchorage`, `Montana State-Billings` and `Nebraska-Kearney`. None of those games falls in a season where the collapsed poll name appears, so **no current row is wrong**. The next season that lines up will produce a wrong match or a silent miss.

**Fix.**
- Normalize the left side with `split_tag`/`key` before comparing it to `SYSTEM_NAMES`.
- Treat a right side that is a state (`MN`, `(Kan.)`) as a tag.
- Only strip a city when the name has no system prefix (`University of <state>`, `<state> State`, `<state> -`). Otherwise keep it: the dash is the campus.

### 5. MEDIUM (latent): AMBIGUOUS blocks only the loose rule; two identical untagged keys still match

**Defect.** `same()` returns True whenever `a == b`, before the AMBIGUOUS check runs. The comment "never matched without an explicit alias or equal state tags" is therefore false for plain names.

**Evidence** (`p_collide.py`, `collide.txt`). These pairs exist today and differ only in date:
- Men's Soccer game `Westminster` vs the NCAA DII poll's plain `Westminster College`
- Women's Basketball `St. Mary's` vs DII `St. Mary’s` (Saint Mary's, Texas)
- Softball DII `St. Mary's`
- Women's Volleyball `Georgetown` vs NAIA plain `Georgetown`
- Women's Basketball DII plain `Union`

**Fix.** If the base is in AMBIGUOUS and neither side has a tag or an alias, return False even when the keys are equal.

### 6. MEDIUM (latent): other normalization collisions, and loose-rule risks outside California

**Evidence** (`p_collide.py`, `p_notes.py`):

`key()` collisions between different schools:

| Names | Shared key | Why |
|---|---|---|
| `College of Idaho` / `Idaho` (University of Idaho) | `idaho` | "college" and a leading "of" are stripped. Biola played `Idaho` in WBB 1981-82 |
| `Southern California College` (Vanguard before 1999) / `USC` | `southern california` | |
| `Colorado College` / `Colorado` | `colorado` | |
| `Charleston (West Virginia)` / `Charleston` | `charleston` | |

A plain Biola name with a non-AMBIGUOUS base loose-matches a tagged poll team from another state:
- `Embry-Riddle` and `Embry Riddle University` (Women's Volleyball; probably Prescott, Ariz., a GSAC school) vs `Embry-Riddle (Fla.)`
- `Anderson College, IN` vs DII plain `Anderson` (South Carolina)
- `Augustana` (softball) vs `Augustana (South Dakota)`
- `Wayne State`, `Queens`, `Wilmington`, `Emmanuel`, `Lee`

That is the same failure as Ottawa, which was only fixed by adding `ottawa` to the list.

In the current output all ~30 loose matches outside California look right (Lubbock Christian, Madonna, Walsh, Houston Baptist, MidAmerica Nazarene, Hastings, Reinhardt, and so on). The risk is in future joins.

**Fix.** Invert the rule. Allow a loose match only when the tagged side is `ca` (Biola's regional opponents) or the opponent is on an allow-list. Everything else needs an explicit alias. Add `idaho`, `colorado`, `southern california`, `embry riddle`, `anderson`, `augustana` and `charleston` to AMBIGUOUS in the meantime.

### 7. LOW-MEDIUM: 30 polls with a null `release_date` are dropped without a word

**Evidence** (`p_stale.py` section c):
- AVCA DII preseason 1995-99 and 2001-03, plus the 1999 and 2005 postseason polls
- NFCA DII 1999-2003 (13 polls, all weeks), plus the 2010, 2013 and 2015 preseason polls
- NAIA softball 2005 final

None is mentioned in `join-report.md`.

**Effect.** Opponents ranked only in those polls are silently unranked. The softball 2010, 2013 and 2015 NFCA preseason polls would have been in effect for early-February games.

**Fix.** Report every poll skipped for a missing date, by sport and season. Give preseason polls a bounded window: in effect from the first game until Week 1, flagged `poll_timing: undated`.

### 8. LOW-MEDIUM: the coverage line counts games with no poll in effect as "checked, not ranked"

**Evidence** (`p_prefirst.py`):
- 149 games in seasons that have polls fall before every division's first poll: WVB 43, WBB 42, MBB 31, SB 25, MSOC 3, WSOC 2, MTEN 3.
- Another 235 games have at least one division not yet polled.
- All of these count toward "N of M games vs ranked".

**Fix.** Report three counts: ranked, checked and unranked, and not checkable (no poll in effect, or no poll yet for the opponent's division).

### 9. LOW: `Midland College` alias is not verified (1 row)

wvb-2014-08-22-1 `Midland College` (Biola Summer Slam) is aliased to `Midland (Neb.)`, NAIA #7 in the preseason poll. Midland College is also the name of a Texas junior college, and the Nebraska school was already "Midland University" in 2014. The file records no evidence for the alias. Confirm it from the box score or delete the alias.

### 10. LOW: smaller gaps in normalization and output

- **`(tie)` prefix.** 14 NABC DII rows are printed `(tie) Azusa Pacific (Calif.)`, `(tie) Cal Poly Pomona`, … `split_tag` only strips trailing parentheses, so these rows can never match. Today no Biola game falls in their windows (checked with `p_fixes.py`), but #25 APU on 2019-12-31 and #25 CPP on 2024-12-31 are Biola conference opponents.
- **State code before a note.** The bare-postal check reads the raw name, so `Menlo CA (DH)` keys to `menlo ca`. No effect today.
- **AMBIGUOUS-append rule (v0417).** It appends *any* note to an AMBIGUOUS base, so `Concordia (BIOLA WEEKEND)` becomes `concordia biola weekend`. No such game name exists today.
- **Output traceability.**
  - Output rows carry neither the matched `team_raw` nor `poll_id`.
  - Poll name plus release date cannot tell the men's ITA ranking from the women's, which share name and date.
  - Add both fields so every row can be audited without re-running the join.
- **Report.** The report's "unmatched poll names" and "near miss" sections run poll names through the game-side `canon` (sport aliases). They should use the poll-side resolver.
- **ITA poll sizes.** ITA DII polls are 25, 50 or 75 deep depending on the year. 34 rows have a rank above 25. The page leaves these out of its Top-25 column (per `review/explorer-audit.md`), so this is a note, not a defect.

## Checked and found sound

- **Season keys.** Game and poll `season` labels agree in every sport: `YYYY-YY` for basketball, `YYYY` elsewhere. The COVID 2020 fall seasons played in spring 2021 are labeled `2020` on both sides, and no spring-2021 poll is labeled otherwise.
- **November preseason polls.** NAIA baseball and softball preseason polls come out in November and are correctly in effect only until Week 1.
- **One poll per division.** No division-season mixes two poll series; the WBB NCAA DII USA Today/WBCA and WBCA series never overlap. No two dated polls share a division and date.
- **Postseason finals.** No row uses a `postseason_final` poll.
- **AMBIGUOUS drops.** The current version drops 0 games for ambiguity. The only games the AMBIGUOUS guard blocks (`p_drops_ambig.py`) are the four in `_open_questions`, plus Ottawa (Women's Soccer).
- **No recall gaps.** A forgiving re-match of every unmatched game against the polls in effect (`p_drops2.py`) finds no other silent drops in the current version.
