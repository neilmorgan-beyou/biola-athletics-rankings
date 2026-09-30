# Adversarial review: build_rankings_page.py / rankings.js / rankings.css

Method: rebuilt the page into `review/scratch/out/` (byte-identical to the shipped
`rankings-history-sportfile-body.html` and `rankings-merged.json`), then probed the
real data with the scratch scripts `p_values.py`, `p_dedupe.py` (output in
`dedupe.txt`), `p_alias.py`, `p_summ.py`, `p_final.py`, `p_games.py` and `p_season.py`.
Counts: 1248 raw poll rows, 1248 after dedupe (0 dropped), 338 season-summary rows,
856 games.

Findings are ordered most severe first.

---

## 1. "NR" (not ranked) is printed as "Ranked", which is the opposite of its meaning  [HIGH]

**Defect.** `rank_label()` returns "Ranked" for any value with no digits that does not
start with "RV". Agent summaries use `"NR"` for not ranked.

**Evidence.** Every distinct rank value in the data, and what it prints, is listed in
`p_values.py`. The rendered Ranked seasons table contains these rows:
- Women's Volleyball 2026 AVCA: Preseason **Ranked** (data: `NR`)
- Women's Volleyball 2023 AVCA: Preseason **Ranked**, Peak RV, Final **Ranked** (data: NR / RV / NR)
- Women's Volleyball 2022 and 2021 AVCA: Final **Ranked** (data: `NR`)
- Women's Volleyball 2002 NAIA: Preseason **Ranked** (data: `NR`)
- Women's Volleyball 2001 NAIA: Preseason **Ranked**, Final **Ranked** (data: `NR`)

That is 8 cells in 6 rows. In 2023 the page says the team finished "Ranked" even though
its peak was only RV.

**Fix.** Handle `NR` explicitly: return "NR" or "-", and give it a sort value after RV.
Keep "Ranked" only for the explicit `ranked (position unknown)` value.

## 2. "Final" is the regular-season poll, not the final poll; postseason polls are ignored  [HIGH]

**Defect.** `fin = next(r for r in rs if "final" in week)` takes the first row whose week
label contains "final". Rows are sorted by date, with undated rows first. As a result:
(a) "Postseason", "End of season" and "Post-..." labels are never recognized, and
(b) "Final regular season" beats the real postseason final. The computed value then
**overrides** the agent's summary (see #4).

**Evidence (shown on the page / in the later postseason poll):**
| Season | Page "Final" | Later postseason row in data |
|---|---|---|
| WVB 2011 | No. 9 ("Final" 11-13) | Postseason **5** (agent summary also 5) |
| WVB 2013 | No. 3 | Postseason 12-11 **2** (agent 2) |
| WVB 2014 | No. 4 | Postseason 12-10 **3** (agent 3) |
| WVB 2016 | No. 21 | Postseason 12-07 **14** (agent 14) |
| Softball 2014 | No. 12 ("Apr 29 edition (final regular season)") | "Final (postseason)" 06-04 **15** (agent 15) |
| MSOC 2011 / 2013 / 2015 | 19 / 24 / 7 | Postseason 18 / RV / 10 |
| WSOC 2015 | 13 | Postseason 12 |
| WSOC 2016 | 8 (agent fill) | Postseason 12-07 **16** |
| WS&D 2016-17 | filled from agent | Postseason 3 not detected |
| WGolf 2023-24 | blank | "End of season" 47 |

The meaning of "Final" therefore changes from sport to sport: postseason for volleyball
and softball when the agent's value survives, regular season for soccer.

**Fix.** Rank candidates explicitly: postseason, post-championship, "Final (post...)" or
"End of season" first, then plain "Final", then "final regular season". Among equal
candidates take the latest date. Or decide on "final regular-season poll", rename the
column to match and apply it consistently. Either way, never let the heuristic override an
agent-supplied value without flagging it.

## 3. Season summaries are keyed on `region`, which agent summaries don't have: 45 duplicate rows with blank era/scope  [HIGH]

**Defect.** Computed summaries are keyed `(sport, season, poll, region)`. Agent
`season_summaries` have no `region` field, and several put the region in the poll name
instead ("D2SIDA Media Poll (West Region)"). So 45 of the 270 agent summaries (every
regional one) never match. They are emitted as a second row with `era=""` and
`scope=""`.

**Evidence.** Output of `p_summ.py`. Rendered examples:
- `Men's Cross Country | 2024 | NCAA DII | USTFCCCA NCAA DII Regional Rankings (West) | No. 5 | No. 3 | No. 3 | 8` and again
  `Men's Cross Country | 2024 | (blank era) | USTFCCCA NCAA DII Regional Rankings | No. 5 | No. 3 | No. 3 | 8`
- `Men's Basketball 2021-22`: "D2SIDA Media Poll (West)" with 14 weeks **and** "D2SIDA Media Poll (West Region)" with 13 weeks, contradicting each other.
- The same pattern repeats for Softball 2021/22/23/25/26 regional, all 14 XC regional seasons, MSOC/WSOC regional, and so on.

Effects: the Ranked seasons table has 45 duplicate rows (338 instead of 293). Those rows
also vanish as soon as any Era or Poll-type filter is chosen, because `data-era` and
`data-scope` are empty.

**Fix.** Normalize before keying: parse a trailing "(West Region)" out of the poll name
into `region`, and fall back to matching on `(sport, season, poll)` when the agent
summary has no region and only one computed region exists. When nothing matches, inherit
`scope` and `era` from the rows for that sport, season and poll. Assert that there are
no two summaries per (sport, season, normalized poll).

## 4. Merge precedence is the reverse of what the comment says, and the heuristic beats curated values  [HIGH]

**Defect.** The comment says "take the agent's where given, fill the rest from rows".
The code does the opposite: it computes first, and the agent's value is used only when
the computed one is empty. So hand-checked agent values lose to the substring heuristic.

**Evidence (computed value shown, agent value discarded):**
- WSOC 2014 peak **No. 8** from a biola-news row with week "Peak (week not stated)". That row's own note says: "DISCREPANCY: archived NAIA polls for 2014 show a peak of No. 9 (Oct. 14); no No. 8 found." The agent summary says 9.
- The 5 finals in #2 (WVB 2011/13/14/16, Softball 2014).
- 14 weeks_ranked conflicts (MBB 1999-00 shows 13 vs agent 12, WWP 2024 shows 8 vs 7, MBB 2012-13 shows 1 vs 0, and others); see #5 and #6.

**Fix.** Use the agent value when present, and use the computed value only to fill gaps.
Print a warning for every field where the two disagree so the disagreements can be
reviewed. Exclude rows with `rank` claims that the data itself flags as discrepant from
the peak (or add an `exclude_from_summary` flag).

## 5. Dedupe removes nothing (0 of 1248) and keeps several copies of the same poll week  [MEDIUM-HIGH]

**Defect.** The dedupe key includes `week`, `date` and `rank`. When the same poll is
reported by the poll document and by a Biola story, the week label and date always
differ, and sometimes the rank does too (T23 vs 23). So no pair ever collides. The
dedupe is effectively a no-op.

**Evidence (all rendered as separate poll appearances and counted in Weeks):**
- WWP 2024 CWPA: "Week 3 (per Biola story)" 2024-02-03 **23** (biola-news). Its own note says "corresponds to Week 2 T23 in primary poll". It sits beside Week 2 T23 (01-31) and Week 3 **24** (02-07), so the page shows two different ranks for "Week 3". Weeks: 8 vs the agent's 7.
- WS&D 2024-25 CSCAA: "February" 2025-02-07 RV (primary) and "February (per Biola story)" 2025-02-07 RV. The second row's `confidence` field holds a URL, so its source link reads "Source".
- Derived "Poll before <date>" rows (reconstructed from a later poll's "previous" column) repeat polls that are already present:
  - MBB 1999-00: "Poll before 1999-12-07" 18 repeats Preseason 18, and "Poll before 2000-01-11" 14 repeats undated "Poll 2" 14.
  - MBB 2000-01: "Poll before 2001-01-08" 2 repeats undated "Poll 1" 2.
  - MBB 2016-17: "Poll before 2017-01-03" **1** is very likely the same poll as the biola-news 2016-12-06 No. 1 row, so the No. 1 week is counted twice.
  - WBB 2016-17: "Poll before 2017-02-28" 17 next to "Poll 5" 02-14 T17 (one prints No. 17, the other T-17).
- Softball 2014: biola-news 04-06 "In-season" 13 ("poll prior to Apr 8") next to the secondary "Apr 8 edition" 13. This is likely a duplicate.
- WGolf 2022-23 WGCA: "Current as of 2023-02-06" 24. Its note says "likely carryover of final fall poll", which is the same poll as "Final Fall" 24.

`dedupe.txt` also lists 47 pairs of same-group rows dated within 6 days. Most are
legitimate weekly polls; the ones above are the real duplicates.

**Fix.** Key on the poll edition, not the reporting row. Give each row a canonical
`poll_date` (the release date, not the story date) and dedupe on
`(sport, season, poll, region, poll_date)`. Prefer primary over biola-news. Drop a
derived "Poll before X" row whenever a row for the preceding poll already exists. A
cheap guard: flag any group with two rows within 6 days where one is biola-news or
derived.

## 6. "Weeks" counts preseason and aggregate rows, so the number isn't a week count  [MEDIUM]

**Defect.** `weeks_ranked = len(ranked rows)`. That count includes the preseason poll
(133 of 293 groups), duplicates (#5), and summary-style rows that stand for several weeks
or none.

**Evidence:**
- WVB 2017 NCCAA "All editions (5)" No. 1 counts as **1** week, though it stands for 5.
- MBB 1981-82 "Multiple weeks" No. 1 counts as 1.
- MXC 2013 "Season high" 22 counts as its own week, next to "In-season (as of 10/25/2013)" 23.
- WSOC 2014 "Peak (week not stated)" 8, and WGolf 2024-25 "Season peak" 8, count as weeks.
- MBB 2012-13: the only row is Preseason T13. The page says 1 week ranked; the agent says 0.

**Fix.** Define the column (for example "in-season polls ranked", preseason excluded) and
compute it only from rows that represent one poll edition. Mark aggregate rows with
`aggregate: true` and exclude them from the count. Prefer the agent's `weeks_ranked`.

## 7. "Record vs. ranked opponents" includes games against RV (unranked) opponents  [MEDIUM]

**Defect.** Games with `opponent_rank: null` (receiving votes) are counted in "all". The
games table even labels them "RV". The headline and section copy say "vs. ranked
opponents" and "against opponents shown as ranked".

**Evidence.** There are 57 RV games (18-36-3). The headline "All-time record vs. ranked
opponents: **268-573-15**" should be **250-537-12** against numbered opponents.
Men's Water Polo shows 3-53 "vs. ranked", but all 3 wins came against RV teams. Its
"Highest-ranked win" cell is empty, which contradicts the 3 wins.

**Fix.** Either exclude RV games from `all`, or relabel the stat and headings "vs. ranked
or receiving-votes opponents" and show the RV split. The agent summary already has
`vs_rv_only`.

## 8. "Preseason" matches any week label containing "pre"  [MEDIUM]

**Defect.** `"pre" in week` also matches "Pre-regional" and "Pre-nationals".

**Evidence.** These are rendered as Preseason ranks:
- Baseball 2018 NCCAA: Preseason **No. 3** (really "Pre-regional", May 11)
- WSOC 2017 NCCAA: Preseason **No. 2** ("Pre-regional", Nov 10)
- MS&D 2015-16 NAIA: Preseason **No. 10** ("Pre-nationals")

**Fix.** Use `week.lower().startswith("preseason")` or a regex `^pre-?season`.

## 9. Conference predicted-finish polls look like rankings, and the "National and regional" default includes them  [MEDIUM]

**Defect.** Rows with scope "conference" (PacWest and WWPA preseason coaches' polls,
which predict order of finish, and the PacWest tennis committee rankings) render in both
tables as "No. N". The Poll-type select's empty option is labelled **"National and
regional"** but shows all scopes. The hero text says "every published national and
regional poll ranking".

**Evidence.** 65 conference rows and 61 conference summary rows are visible by default.
Softball 2022, MWP 2023, and WWP 2024 and 2025 show "Preseason No. 1 / Peak No. 1" for
being *picked to win the conference*.

**Fix.** Either exclude scope=conference from these tables, or put it in its own
sub-table labelled "Conference preseason predictions". Relabel the empty option "All poll
types" and give the other options readable labels (see #15).

## 10. `top-5` prints as "T-5" (tied for 5th)  [MEDIUM-LOW]

**Evidence.** MXC 2016 and WXC 2016, "In-season (poll ~10/12/2016)", rank `top-5`. The
note says "exact rank not given", but the page prints **T-5**, and the value sorts and
counts as rank 5.

**Fix.** `rank_label`: when the value matches `^top-?(\d+)`, print "Top 5". Use
`startswith("T")` only when a digit follows (`^T-?\d+$`).

## 11. Rank `None` (ranked, position unknown) prints as an empty cell  [LOW-MEDIUM]

**Evidence.** WS&D 2023-24 CSCAA "March (Final)": rank `null`. Its note says "rank=null
means ranked, number unknown". The Rank cell in the poll table is empty, and the summary
row shows Peak "Ranked" with an empty Final.

**Fix.** Use a distinct sentinel in the data (such as `"ranked"`) or treat `None` on a
poll row as "Ranked".

## 12. Headline counts use different filters from their labels and from each other  [LOW-MEDIUM]

- "Team-seasons ranked nationally or regionally" = **166**. It counts Women's T&F "2014 Indoor" and "2014 Outdoor" as two team-seasons (3 double-counted years; 163 when merged). It also includes 5 NCCAA-only team-seasons (era "other"), while "Highest national ranking" and the No. 1 roll exclude era "other". Excluding "other" gives 161.
- "Highest national ranking: Men's Basketball, 1981-82". The tie-break is the earliest season, so the headline cites a biola-news "Multiple weeks" claim rather than one of the poll-archived No. 1s (2001-02, 2016-17). Three programs share No. 1.

**Fix.** Normalize the season to its academic year for counting (strip Indoor/Outdoor).
Apply one filter (the era regex) to all four stats, or label the NCCAA inclusion. For
the tie-break, prefer primary confidence and then the most recent season.

## 13. Default poll-table order puts undated rows first within each season  [LOW-MEDIUM]

**Defect.** Rows are sorted by `date or ""`, so all 179 undated rows sort above dated
ones.

**Evidence.** In 49 poll groups the first row shown is an undated non-preseason entry.
Examples: XC "Final (post-championship)" appears above Preseason; MBB 1999-00 "Poll 2"
and the "Poll before" rows appear above Preseason. The same ordering also drives the
first-match `pre` / `final` heuristics in #2 and #8.

**Fix.** Sort by `(date is None, date)` plus a week-order key parsed from the label
(preseason = 0, "Week/Poll N" = N, final/postseason = 99).

## 14. Department tables: labels and statuses  [LOW]

- The NCCAA Presidential Award rows (2017-18, 2018-19) render under the **"Directors' Cup"** heading with Division "NCCAA". It is not a Directors' Cup.
- Mixed status strings: "No data found (1st at interim)" (NCCAA) and "Award not held (113th at interim)" (DII 2019-20). "Not held" beside a placing reads as a contradiction; the data note says the standings were never *published* (COVID) and the 113th was fall-only.
- `SRC_TEXT` maps confidence "primary" to "**Poll**" on every table. Directors' Cup PDFs and PacWest releases are labelled "Poll", which the page note defines as "the published poll itself".
- The Academic Achievement GPA 3.448 prints as **3.45**. It sits in a "Score" column whose subhead says "published average per sport".

**Fix.** Move the NCCAA award rows to their own sub-heading or to the conference table.
Use "Standings not published (113th after fall)". Use table-specific source labels
("Standings", "Release"). Don't round GPA values, or give them their own column.

## 15. JS sort and filter issues  [LOW]

- The numeric sort sentinel 999 is shared by RV, blank, NR and "Ranked". A descending sort floats all of them to the top together, with blanks mixed in among real RV values.
- The filter options show raw data values: Era "**other**" and Poll type "conference" / "national" / "regional" in lower case. "other" means NCCAA and isn't explained.
- 45 summary rows have empty `data-era` and `data-scope` (see #3), so the filters silently hide them.
- The t-games Sport filter lists every sport with polls, including 8 that have no games, so those choices show 0 rows.

**Fix.** Use distinct sort values (numbered < ties < RV (900) < ranked-unknown (950) < NR/blank (999)) and keep blanks last in both directions. Give filter options display labels. Build the Sport options for each table from that table's own rows.

## 16. HTML, ASCII and CKEditor  [INFO, no defect found]

- The output is pure ASCII (0 non-ASCII characters, 0 numeric entities). The CSS and JS have no non-ASCII characters, so the `xmlcharrefreplace` pass never touches `<script>` or `<style>`. There are no empty `href`s and no duplicate ids.
- If `fillEmptyBlocks` is on, CKEditor 4 will add `&nbsp;` to the empty `<p class="rk-count">` and to empty `<td>`s. This is harmless: JS `trim()` strips NBSP, and every sortable cell has `data-v`.
- `<button>`, `<select>` and `<input>` survive only if the Sidearm ACF allows them. This could not be verified here; the FAQ page precedent suggests they do.
- One data row has a URL in `confidence` (WS&D 2025-02-07). Its source link reads "Source" instead of "Biola".
