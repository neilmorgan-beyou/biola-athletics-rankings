# Audit: `data/vs-ranked-verified.json` (ranked-opponent games verified against polls)

Audited 2026-09-30. Adversarial check of the claim that the file lists **every** Biola game against an opponent ranked in the national poll in effect on game day, with correct rank, poll and source URL.

**Snapshot note:** I audited the 04:04 build (1,800 rows). While I worked, another process kept rewriting `join_games_polls.py`, `polls/aliases.json` and the verified file: 04:17 had 1,803 rows, 04:18 had 1,804, and 04:25 had 1,775 with a new `SAME_DAY = False` rule and a stale-gap guard. The last column of section 1 gives each defect's status in the 04:25 build. I modified no file except this one. My scripts are in the scratchpad under `vaudit/`.

## How I checked it
- **False positives:** a seeded random sample (`random.seed(21)`) of 60 verified rows, 4+ per sport, weighted 4x for opponents ranked No. 1-5 and 4x for postseason games. The sample has 36 top-5 rows and 14 postseason rows. For each row:
  - (a) Read the cited poll document: NAIA release pages through Wayback or Chrome (naia-archive.prestosports.com blocks curl with Cloudflare), NAIA week-by-week PDFs mapped by column x-position, NFCA/NCBWA/WBCA/CWPA pages, and the ITA API.
  - (b) Confirmed the release date and that no later poll came out before the game, using the source's own "next poll on ..." text, the index, or the list of publish dates.
  - (c) Matched the game against Biola's cached season page: `og:title` season, date, opponent and result. All 60 pages carry the right season; three were also re-fetched live.
- **Whole-file scans:**
  - Re-derived the poll team behind every row, looking for a different school with a similar name.
  - Ran an independent re-join with a different normalizer.
  - Swept every poll name that matches no Biola opponent, looking for renamed schools and typos.
  - Listed rows that rest on a poll older than the next archived one, and archive gaps that fall inside Biola seasons.
- **False negatives:**
  - A seeded sample of 40 games **not** in the list: 28 conference rivals and 12 national or NCCAA/NCAA tournament games. I checked each against every poll in effect.
  - Targeted source checks on every miss the scans surfaced.

## Bottom line
- **The ranks that are listed are almost always right.** 59 of the 60 sampled rows match the poll document exactly, and the 60th has the right rank with the wrong poll cited. No sampled row has a wrong school or a wrong game. Sampled FP rate is 0/60 (95% upper bound ~5%).
- **The whole-file scan found errors the sample missed:**
  - 5 rows matched the wrong Concordia.
  - 2 rows carry a wrong rank taken from a stale poll.
  - About 10 rows cite a stale poll because the archive is missing weeks.
- **"Every game" is not true.** I confirmed 10 misses (renamed schools, alias gaps, over-strict ambiguity rules) plus unresolved candidates. Whole eras and poll weeks are also missing from the archive.

## 1. Defects, most severe first

| # | Severity | Defect | Evidence | Rows | Status in 04:25 build |
|---|---|---|---|---|---|
| 1 | High (FP) | **Sport-scoped alias `Concordia -> Concordia Irvine` was applied to POLL names.** Any poll entry printed as a bare or non-state-tagged Concordia became Irvine. | `wbb-2004-01-22-1` and `wbb-2004-01-27-1` (#16) are matched to WBCA DII 2004-01-20 "16 Concordia (Saint Paul) 212 15-1"; Irvine does not appear in the 2003-04 WBCA PDF (wbca.org/.../D2-2003-04.pdf). `mten-2019-02-28-1` (#20), `mten-2019-04-04-1` (#35) and `mten-2020-02-13-1` (#17) are matched to "Concordia College (New York)" in the ITA DII polls of 2/20/19, 4/3/19 and 1/15/20 (wearecollegetennis.com); Irvine is not in those national lists. | 5 FP | Fixed: aliases no longer apply to poll names; rows gone |
| 2 | High (FN) | **The same alias caused ambiguity drops.** When both Irvine and Concordia NY were ranked, both mapped to Irvine and the game was discarded as "AMBIGUOUS". | ITA 2/2/21: "14 Concordia University (Irvine)" and "17 Concordia College (New York)". ITA 4/8/21: "16" (Irvine) and "21" (NY). | `mten-2021-02-12-1`, `mten-2021-04-08-1` | Fixed (02-12 is #14; 04-08 is now #17 from the 3/23 poll under the same-day rule) |
| 3 | High (FP rank) | **Stale polls from documented archive gaps are used silently.** The join falls back to the previous poll even when the true in-effect poll is a known gap. | `msoc-2011-10-15-1` Azusa Pacific shows **#5** (Oct 4 poll), but NAIA Poll 6 of Oct 11, 2011 had APU **#12**. Narrative on the Wayback release page 20111011sxab9: "last week's No. 5 team, Azusa Pacific (Calif.), who fell seven positions to 12th". Also NAIA MS week-by-week PDF. | 1 | **Still #5, still wrong** |
| 4 | High (FP rank) | **Missing January polls in NAIA DI men's basketball 2010-11** (archive jumps 12/13 to 1/31). | `mbb-2011-01-14-1` Concordia showed **#5** from 12/13. The poll in effect (Jan 10, 2011) had Concordia **#3**: NAIA MBB week-by-week PDF, row "Concordia (Calif.) 5 6 5 3 3 2 ...", J10 = 3. | 1 | Row dropped by the new gap guard, so it is now a **false negative**. The true rank is #3, and APU was #9 on Jan 10 |
| 5 | Medium (wrong citation) | **Missing Rating #1 (Dec 5, 2000), NAIA DI men's basketball.** | `mbb-2001-01-04-1` APU #8 cites the Oct 31 preseason. The Dec 5 Rating #1 also has "8 Azusa Pacific (Calif.) 7-1 221" (Wayback naia.org/basketball/mdi/ratings/00-01/1.html). The rank is right but the poll is wrong. Same window: `mbb-2000-11-18-1` and 13 other Biola games fall more than 9 days into this gap. The index also dates Rating #2 **Jan 9**, but the archive says 1-08. | 1 cited, 13 games at risk | Unchanged |
| 6 | Medium (wrong citation) | **Missing early-January NAIA basketball polls** after the holiday break. | `wbb-2009-01-06-1`: the Dec 8, 2008 release says the next poll comes "Monday, January 5". That poll is not archived; the Jan 12 poll's last-week column still has APU #5. Rank right, citation wrong. The same pattern (Dec poll, then archive jumps to Jan 9+) covers `mbb-2012-01-03-1`, `mbb-2012-01-07-1`, `wbb-2008-01-08-1`, `wbb-2010-01-05-1` and `wbb-2012-01-03-1`; whether a Jan poll existed is unverified. | 1 confirmed, 5 at risk | wbb-2009-01-06 dropped (now FN); the others unchanged |
| 7 | Medium (FN) | **Renamed school: Christian Heritage College = San Diego Christian** (renamed 2005). No alias exists, and the near-miss report cannot see it. | NAIA WVB ratings PDF: "Christian Heritage (Calif.) 24 25 ..." gives #25 on 9/24/02 (`wvb-2002-09-24-1`). NAIA DI MBB Rating #5 (1/30/01): "11 Christian Heritage (Calif.) 17-3" (`mbb-2001-02-03-1`). Final 2/27/01: "13 ..." (`mbb-2001-03-03-1`). | 3 FN | **Still missing** |
| 8 | Medium (FN) | **Alias gap: "Concordia Portland"** is not keyed to Concordia (Ore.). | NAIA WVB PDF, 2003 preseason (8/13): "Concordia (Ore.) 17". Game `wvb-2003-08-23-1` W. The report even lists it as a near miss. | 1 FN | **Still missing** |
| 9 | Medium (FN) | **"Columbia" held as an open question**, even though the evidence settles it. | NAIA WVB PDF: Columbia (Mo.) #11 on 11/18/03. Fresno Pacific's release puts "Columbia of Missouri" in the Dec 6 NAIA nationals at Point Loma, the same venue and date as Biola's match. | `wvb-2003-12-06-1` (#11), 1 FN | **Still missing** |
| 10 | Medium (FN) | **Over-strict ambiguity or suffix handling.** "Cumberland University" was in the AMBIGUOUS set, and "Seattle Pacific University - Seattle" did not normalize. | NAIA DI final 3/9/04: "5 Cumberland (Tenn.)"; the 2004 national tournament first round was Cumberland (TN) 68, Biola 64 (`mbb-2004-03-24-1`). WBCA DII 11/8/05: "3 Seattle Pacific University - Seattle" (`wbb-2005-11-18-1`). | 2 FN | Fixed |
| 11 | Medium (coverage) | **Whole poll seasons or weeks absent**, so "every game" silently excludes them. | NAIA softball 2005 has only an undated final (Cal Baptist #4, Point Loma #6 and Concordia #14 were all played; about 18 games). NFCA DII 1999-2002 plus the 2010, 2013 and 2015 preseasons, and AVCA DII preseasons 1995-2003, have `release_date: null` and are never used. Also missing: NAIA baseball 1999, NCBWA DII 2006-07, NAIA DI/DII basketball DII-side 2005-07, NAIA soccer before 2006, NAIA WVB before 2000, NAIA softball before 2006. The NAIA MSOC 2011 Poll 2 (9/13) and Poll 6 (10/11) are recoverable from the NAIA week-by-week PDF. | Hundreds of games unverified | Unchanged |
| 12 | Low (scope) | **NCAA Division I opponents are never checked** (no DI poll archived). | 11 games in the poll era vs DI teams, e.g. WVB vs Southern California 1990-09-04 and 1990-10-05 (L 2-3 twice). USC was nationally ranked that year. | about 2-11 | Unchanged |
| 13 | Low (definition) | **Tennis "ranked" goes down to #75**, and polls released on game day were counted. | 34 tennis rows are ranked 26-75 (e.g. `mten-2022-04-21-1` Point Loma #67). The 04:04 build counted same-day polls, and 5 of the 60 sampled rows use a poll released on game day. | 34; same-day rows | Same-day now excluded (`SAME_DAY=False`, pending Neil); rank depth unchanged |
| 14 | Low (unresolved FN candidates) | Open alias questions. | `wvb-2006-09-01-2` "Westminster College" (Westminster (Utah) was #25) and `wvb-2000-09-02-2` "Saint Mary" (College of Saint Mary (Neb.) was #7). Not resolved. | 2 | Open |
| 15 | Low (data hygiene) | Poll-week labels and page dates are sometimes wrong in the source. | NAIA 2006 softball "National Rating #7" is archived as "Poll 5". The 2011 WVB postseason page is stamped "Nov 03". The 2011 MSOC W10 page is stamped Nov 2 but released Nov 8. Ranks are unaffected; the release-date text was used correctly. | - | - |

## 2. Estimated error rates per sport (04:04 build)

FP means a listed row whose opponent was not ranked, or not at that rank, in the poll in effect. FN means a ranked-opponent game missing from the list, within the seasons the archive covers. Sample sizes per sport are small (4-9), so the FP rates rely mainly on the whole-file scans.

| Sport | Rows | Sample (FP) | FP / wrong-rank found by scan | Est. FP rate | FN confirmed | FN sample (40) | Est. FN rate (covered seasons) |
|---|---|---|---|---|---|---|---|
| Women's Volleyball | 303 | 5/5 ok | 0 | <1% | 2 (+2 open) | 0/7 | ~1% |
| Men's Soccer | 68 | 5/5 ok | 1 wrong rank | ~1.5% | 0 (2011 W2/W6 missing) | 0/2 | ~1-2% |
| Women's Soccer | 85 | 4/4 ok | 0 | <1% | 0 | 0/1 | <2% |
| Men's Basketball | 168 | 5/5 ok | 1 wrong rank, 1 wrong poll | ~1% (+stale-poll risk in 2 gap windows) | 3 (Christian Heritage x2, Cumberland) | 0/6 | ~2-3% |
| Women's Basketball | 201 | 9/9 (1 stale citation) | 2 wrong school | ~1% (+5 holiday-gap rows at risk) | 1 (Seattle Pacific) | 0/2 | ~1% |
| Baseball | 298 | 5/5 ok | 0 | <1% | 0 | 0/12 | <1% (NAIA 1999, DII 2006-07 absent) |
| Softball | 271 | 7/7 ok | 0 (bare NFCA "Concordia" = Irvine, verified 2023/2024/2026) | <1% | 0 | 0/6 | <1% in covered years; NAIA 2005 effectively uncovered |
| Men's Water Polo | 46 | 4/4 ok | 0 | <1% | 0 | 0/0 | <1% |
| Women's Water Polo | 54 | 5/5 ok | 0 | <1% | 0 | 0/0 | <1% |
| Men's Tennis | 161 | 6/6 ok | 3 wrong school | ~2% | 2 (Irvine 2021) | 0/1 | ~1-2% |
| Women's Tennis | 145 | 5/5 ok | 0 | <1% | 0 | 0/1 | <1% |
| **All** | **1,800** | **59/60 exact, 60/60 right rank** | **5 wrong school + 2 wrong rank + 2 wrong poll** | **~0.5%** | **10 confirmed (+2 open)** | **0/40** | **~0.5-1% in covered seasons** |

The FN sample of 40 found no misses. Most sampled rivals simply were not ranked, and 5 were receiving votes. The confirmed misses all came from the whole-file scans. That fits the pattern: misses cluster in renamed schools, alias gaps and archive gaps rather than being spread at random.

## 3. False-positive sample: per-game verdicts
Columns: n, game_id, opponent (as on Biola schedule), result, claimed rank and poll team, poll, verdict. Every game was also matched on date, opponent, result and season against Biola's schedule page.

| n | game | opponent | result | rank / poll team | poll (release) | verdict |
|---|---|---|---|---|---|---|
| 1 | bsb-2005-05-27-1 | Cumberland (TN) | L 4-11 | #5 Cumberland (Tenn.) | Week 9 (2005-05-18) | CONFIRMED |
| 2 | bsb-2017-04-13-1 | Menlo College (Calif.) | W 7-4 | #9 Menlo (Calif.) | Week 3 (2017-04-04) | CONFIRMED |
| 3 | bsb-2015-03-28-2 | Concordia University (Calif.) | L 6-7 | #17 Concordia (Calif.) | Week 3 (2015-03-24) | CONFIRMED |
| 4 | bsb-2011-04-09-1 | California Baptist | L 2-3 | #8 California Baptist University | Week 2 (2011-04-05) | CONFIRMED |
| 5 | mbb-2004-11-20-1 | Azusa Pacific | W 66-64 | #3 Azusa Pacific (Calif.) | Preseason (2004-10-26) | CONFIRMED |
| 6 | mbb-2015-12-12-1 | Arizona Christian University | W 75-65 | #4 Arizona Christian | Week 1 (2015-12-08) | CONFIRMED |
| 7 | mbb-2016-02-02-1 | William Jessup University (Calif.) | W 87-60 | #24 William Jessup (Calif.) | Week 6 (2016-02-02) | CONFIRMED (poll released on game day) |
| 8 | mbb-2011-02-19-1 | Concordia CA | W 73-71 | #2 Concordia University (Calif.) | Week 8 (2011-02-14) | CONFIRMED |
| 9 | msoc-2011-11-12-1 | Concordia CA | W 3-2 2 OT | #11 Concordia (Calif.) | Week 10 (2011-11-08) | CONFIRMED (page stamp says Nov 2; text puts release Tue Nov 8) |
| 10 | msoc-2009-10-10-1 | Azusa Pacific | W 1-0 | #2 Azusa Pacific University (Calif.) | Week 5 (2009-10-06) | CONFIRMED |
| 11 | msoc-2006-09-27-1 | Azusa Pacific University | L 2-3 | #3 Azusa Pacific (Calif.) (II) | Week 4 (2006-09-27) | CONFIRMED (poll released on game day; only date is page stamp) |
| 12 | msoc-2010-09-29-1 | California Baptist | L 0-1 | #7 California Baptist University | Week 4 (2010-09-28) | CONFIRMED |
| 13 | mten-2015-04-10-1 | Vanguard University (Calif.) | L 1-8 | #4 Vanguard (Calif.) | Poll 4 (2015-03-31) | CONFIRMED |
| 14 | mten-2009-02-19-1 | Fresno Pacific | L 0-9 | #2 Fresno Pacific (Calif.) | Preseason (2009-02-10) | CONFIRMED |
| 15 | mten-2022-04-21-1 | Point Loma | L 0-4 | #67 Point Loma Nazarene University | Week of Apr 21 (2022-04-21) | CONFIRMED, but rank 67 of a 75-deep ITA list; poll released on game day |
| 16 | mten-2010-04-27-1 | Azusa Pacific | L 0-9 | #5 Azusa Pacific (Calif.) | Poll 5 (2010-04-20) | CONFIRMED |
| 17 | mwp-2021-10-24-2 | San Jose State | L 6-17 | #10 San Jose State University | Week 7 (2021-10-20) | CONFIRMED |
| 18 | mwp-2021-09-04-1 | UCLA | L 2-21 | #1 University of California-Los Angeles | Preseason (2021-09-01) | CONFIRMED |
| 19 | mwp-2026-09-18-1 | Brown | L 7-8 | #18 Brown University | Week 3 (2026-09-16) | CONFIRMED |
| 20 | mwp-2024-09-14-1 | Brown | L 6-12 | #18 Brown University | Week 1 (2024-09-11) | CONFIRMED |
| 21 | sb-2024-03-08-1 | Concordia | L 3-5 (8 Inn.) | #24 Concordia | Week 4 (2024-03-05) | CONFIRMED |
| 22 | sb-2014-04-12-2 | Concordia University (Calif.) | L 0-1 | #1 Concordia (Calif.) | Poll 4 (2014-04-08) | CONFIRMED |
| 23 | sb-2006-04-29-1 | California Baptist | L 1-2 | #1 California Baptist | Poll 5 (2006-04-26) | CONFIRMED (source titles it "National Rating #7", archive says "Poll 5") |
| 24 | sb-2010-03-02-2 | Point Loma Nazarene | L 10-3 | #3 Oklahoma City University/Point Loma Nazarene University (Calif.) | Preseason (2010-02-02) | CONFIRMED (tied No. 3; release says next poll Mar 23) |
| 25 | wbb-2010-03-05-1 | Vanguard | L 68-78 | #3 Vanguard University (Calif.) | Week 10 (2010-03-02) | CONFIRMED |
| 26 | wbb-2004-01-31-1 | Vanguard University, CA | W 85-66 | #4 Vanguard (Calif.) | Week 6 (2004-01-27) | CONFIRMED |
| 27 | wbb-2020-03-06-1 | Hawaii Pacific University | L 65-68 | #3 Hawaii Pacific | Week 14 (2020-03-03) | CONFIRMED |
| 28 | wbb-2009-01-06-1 | Azusa Pacific | W 61-56 | #5 Azusa Pacific (Calif.) | Week 2 (2008-12-08) | STALE POLL: a Jan 5 2009 poll existed (not archived); APU was No. 5 there too, so the rank holds but the citation is wrong |
| 29 | wsoc-2008-10-18-1 | Azusa Pacific | L 0-3 | #3 Azusa Pacific University (Calif.) | Week 6 (2008-10-14) | CONFIRMED |
| 30 | wsoc-2016-11-10-1 | Westmont College | W 1-0 | #10 Westmont (Calif.) | Week 8 (2016-11-08) | CONFIRMED |
| 31 | wsoc-2007-10-13-1 | Azusa Pacific University | L 0-1 | #2 Azusa Pacific (Calif.) (II) | Week 6 (2007-10-10) | CONFIRMED |
| 32 | wsoc-2023-08-31-1 | Western Washington | L 0-2 | #1 Western Washington University | Preseason (2023-08-01) | CONFIRMED |
| 33 | wten-2012-02-28-1 | Concordia CA | L 0-9 | #5 Concordia (Calif.) | Poll 1 (2012-02-21) | CONFIRMED |
| 34 | wten-2013-04-10-1 | Vanguard | L 0-5 | #12 Vanguard (Calif.) | Poll 4 (2013-04-02) | CONFIRMED |
| 35 | wten-2011-03-10-1 | Azusa Pacific | L 0-9 | #5 Azusa Pacific (Calif.) | Poll 2 (2011-03-08) | CONFIRMED |
| 36 | wten-2012-04-02-1 | Fresno Pacific | L 0-9 | #2 Fresno Pacific (Calif.) | Poll 3 (2012-03-20) | CONFIRMED |
| 37 | wvb-2005-09-17-1 | California Baptist | L 0-3 | #3 California Baptist | Week 2 (2005-09-14) | CONFIRMED |
| 38 | wvb-2000-09-08-1 | Lewis-Clark State | L 0-3 | #3 Lewis-Clark State (Idaho) | Preseason (2000-08-15) | CONFIRMED |
| 39 | wvb-2015-12-04-2 | Columbia College (Mo.) | L 2-3 | #4 Columbia (Mo.) | Final Regular Season (2015-11-16) | CONFIRMED |
| 40 | wvb-2006-10-21-1 | California Baptist University | W 3-1 | #3 California Baptist | Week 7 (2006-10-18) | CONFIRMED |
| 41 | wwp-2025-02-21-1 | USC | L 5-30 | #1 Stanford University/University of Southern California | Week 5 (2025-02-19) | CONFIRMED |
| 42 | wwp-2023-02-18-2 | UC Davis | L 7-16 | #17 University of California-Davis | Week 5 (2023-02-15) | CONFIRMED |
| 43 | wwp-2026-02-14-2 | Arizona State | L 10-23 | #6 Arizona State University | Week 4 (2026-02-11) | CONFIRMED |
| 44 | wwp-2026-01-23-1 | UC Santa Barbara | L 7-17 | #18 University of California-Santa Barbara | Week 1 (2026-01-21) | CONFIRMED |
| 45 | sb-2021-04-03-2 | Concordia Irvine | W 3-0 | #8 Concordia Irvine | Week 7 (2021-03-31) | CONFIRMED |
| 46 | sb-2021-05-29-1 | North Georgia | W 5-2 | #2 North Georgia | Week 13 (2021-05-12) | CONFIRMED |
| 47 | bsb-2018-04-27-1 | Azusa Pacific | L 2-18 | #3 Azusa Pacific | April 25 (2018-04-25) | CONFIRMED |
| 48 | sb-2014-04-12-1 | Concordia University (Calif.) | L 6-9 | #1 Concordia (Calif.) | Poll 4 (2014-04-08) | CONFIRMED |
| 49 | wvb-2011-11-30-1 | Freed-Hardeman TN | W 3-1 | #25 Freed-Hardeman (Tenn.) | Final Regular Season (2011-11-13) | CONFIRMED (next-poll page header misdated "Nov 03") |
| 50 | wbb-2017-03-15-1 | Central Methodist University (Mo.) | L 49-52 | #20 Central Methodist (Mo.) | Week 7 (final regular-season poll) (2017-03-08) | CONFIRMED |
| 51 | wwp-2024-03-09-1 | UCLA | L 4-23 | #1 University of California-Los Angeles | Week 7 (2024-03-06) | CONFIRMED |
| 52 | msoc-2006-11-01-1 | Concordia University-Irvine | L 0-1 | #5 Concordia (Calif.) (II) | Final (regular season) (2006-11-01) | CONFIRMED (poll released on game day) |
| 53 | mten-2026-05-20-1 | Catawba College | L 0-4 | #7 Catawba (M) | Week of Apr 29 (2026-04-29) | CONFIRMED |
| 54 | mten-2015-03-28-1 | San Diego Christian College (Calif.) | L 2-7 | #15 San Diego Christian (Calif.) | Poll 3 (2015-03-17) | CONFIRMED |
| 55 | wbb-2008-03-01-1 | Vanguard University | L 75-91 | #4 Vanguard University (Calif.) | Week 10 (2008-02-27) | CONFIRMED |
| 56 | mbb-2017-03-04-1 | The Master's University | L 68-83 | #14 The Master's (Calif.) | Week 6 (2017-02-28) | CONFIRMED |
| 57 | wbb-2013-02-23-1 | Westmont | L 49-55 | #4 Westmont (Calif.) | Week 9 (2013-02-19) | CONFIRMED |
| 58 | wbb-2003-12-02-1 | Vanguard University, CA | L 37-89 | #4 Vanguard (Calif.) | Week 1 (2003-12-02) | CONFIRMED (poll released on game day) |
| 59 | wten-2025-04-19-1 | Point Loma | L 3-4 | #22 Point Loma (W) | Week of Apr 16 (2025-04-16) | CONFIRMED |
| 60 | wbb-2003-12-06-1 | Westmont College, CA | L 47-78 | #23 Westmont (Calif.) | Week 1 (2003-12-02) | CONFIRMED |

Evidence notes (sources read):
- **NAIA release pages:** read via Wayback or Chrome.
  - Examples: 20170404jocpk ("The fourth regular-season edition will release on April 18"), 20151208gvmbp (next "Tuesday, Jan. 5, 2016"), 20140408yvckv ("face No. 13 Biola (Calif.) on Saturday").
- **NAIA week-by-week PDFs** (men's and women's tennis, volleyball, baseball): columns mapped by x-position.
- **NFCA pages:** 3-5-24 "24 Concordia 38 15-4", tagged Concordia Irvine; 5-12-21 "2 North Georgia".
- **NCBWA:** div2poll180425 "3. Azusa Pacific".
- **WBCA:** Mar. 3, 2020 PDF "3 Hawaii Pacific".
- **CWPA** weekly posts.
- **ITA API** publish-date lists: 2026 DII men 04-29 then 05-27; 2025 DII women weekly.

## 4. False-negative sample: per-game verdicts (games NOT in the list)
28 conference-rival games and 12 national-tournament games, drawn with `random.seed(21)` from games in seasons with archived polls. "Poll(s) in effect" lists the latest poll of each division on or before game day.

| n | game | opponent | poll(s) in effect | verdict |
|---|---|---|---|---|
| 1 | msoc-2022-10-12-1 | Point Loma | usc-dii-m-2022-w06, naia-m-2022-w06 |  Not ranked in the poll in effect: correct exclusion |
| 2 | bsb-2000-03-18-2 | Azusa Pacific | naia-bsb-2000-pre |  Not ranked. The only NAIA poll before the game is the Dec 1999 preseason; NAIA weekly polls began Mar 21 |
| 3 | sb-2025-04-04-2 | Hawaii Pacific | naia-sb-2025-w03, nfca-dii-2025-w08 |  Not ranked in the poll in effect: correct exclusion |
| 4 | sb-2014-03-20-2 | Hope International University (Calif.) | naia-sb-2014-w01, nfca-dii-2014-w05 |  Not ranked in the poll in effect: correct exclusion |
| 5 | mbb-2018-12-05-1 | Point Loma | naia-di-2018-19-2018-12-04, naia-dii-2018-19-2018-11-27, nabc-dii-2018-19-2018-12-04 |  Not ranked (receiving votes in NABC 12/4) |
| 6 | bsb-2008-03-12-1 | Westmont | naia-bsb-2008-w01, ncbwa-dii-2008-0311 |  Not ranked in the poll in effect: correct exclusion |
| 7 | mbb-2001-01-02-1 | Westmont | naia-di-2000-01-2000-10-31, naia-dii-2000-01-2000-12-05 |  Not ranked in the archived poll, but that poll is the Oct 31 preseason: the Dec 5, 2000 Rating #1 is missing from the archive. Unresolved |
| 8 | bsb-2007-04-18-1 | Westmont College | naia-bsb-2007-w06 |  Not ranked in the poll in effect: correct exclusion |
| 9 | bsb-2013-03-01-1 | Vanguard | naia-bsb-2013-pre, ncbwa-dii-2013-0225 |  Not ranked in the poll in effect: correct exclusion |
| 10 | wsoc-2013-10-23-1 | Hope International | usc-dii-w-2013-w07, naia-w-2013-w07 |  Not ranked ("American International" is a different school) |
| 11 | bsb-2012-03-03-2 | Westmont | naia-bsb-2012-pre, ncbwa-dii-2012-0228 |  Not ranked in the poll in effect: correct exclusion |
| 12 | bsb-2016-03-22-1 | Hope International University (Calif.) | naia-bsb-2016-w02, ncbwa-dii-2016-0322 |  Not ranked in the poll in effect: correct exclusion |
| 13 | mbb-2005-02-08-1 | The Master's | naia-di-2004-05-2005-02-08, naia-dii-2004-05-2005-02-01, nabc-dii-2004-05-2005-02-01 |  Not ranked in the poll in effect: correct exclusion |
| 14 | wvb-1987-10-01-1 | The Master's | avca-dii-1987-w03 |  Not ranked in the poll in effect: correct exclusion |
| 15 | wvb-1990-09-22-1 | Azusa Pacific | avca-dii-1990-w02 |  Not ranked in the poll in effect: correct exclusion |
| 16 | wbb-2017-02-11-1 | Menlo College (Calif.) | naia-di-2016-17-2017-01-31, naia-dii-2016-17-2017-02-07, wbca-dii-2016-17-2017-02-06 |  Not ranked in the poll in effect: correct exclusion |
| 17 | bsb-2025-05-02-1 | Concordia | naia-bsb-2025-w05, ncbwa-dii-2025-0430 |  Not ranked. Concordia (Neb.) is ranked; Biola's 2025 opponent is Concordia Irvine (PacWest) |
| 18 | bsb-2001-04-10-1 | Westmont | naia-bsb-2001-w04 |  Not ranked in the poll in effect: correct exclusion |
| 19 | wvb-2003-11-08-1 | California Baptist | naia-2003-w09, avca-dii-2003-w10 |  Not ranked (Houston Baptist is a different school) |
| 20 | msoc-2012-09-26-1 | The Master's | usc-dii-m-2012-w04, naia-m-2012-w04 |  Not ranked in the poll in effect: correct exclusion |
| 21 | wten-2016-02-06-1 | San Diego Christian College (Calif.) | naia-wten-2016-preseason |  Not ranked in the poll in effect: correct exclusion |
| 22 | mbb-2004-02-24-1 | Hope International | naia-di-2003-04-2004-02-24, naia-dii-2003-04-2004-02-17 |  Not ranked in the poll in effect: correct exclusion |
| 23 | mbb-2004-03-02-1 | San Diego Christian | naia-di-2003-04-2004-03-02, naia-dii-2003-04-2004-02-17 |  Not ranked in the poll in effect: correct exclusion |
| 24 | sb-2026-03-02-1 | Menlo | naia-sb-2026-pre, nfca-dii-2026-w03 |  Not ranked in the poll in effect: correct exclusion |
| 25 | wvb-1996-12-05-1 | Hawai'I Pacific | avca-dii-1996-final |  Not ranked in the poll in effect: correct exclusion |
| 26 | bsb-2002-04-11-1 | Westmont | naia-bsb-2002-w03 |  Not ranked in the poll in effect: correct exclusion |
| 27 | mten-2025-03-07-1 | Menlo College | ita-dii-m-2025-2025-03-05 |  Not ranked in the poll in effect: correct exclusion |
| 28 | wten-2024-04-12-1 | Westmont | ita-dii-w-2024-2024-04-10 |  Not ranked in the poll in effect: correct exclusion |
| 29 | bsb-2008-05-08-1 | Concordia | naia-bsb-2008-w09, ncbwa-dii-2008-0505 |  Not ranked in the poll in effect: correct exclusion |
| 30 | sb-2019-05-15-2 | Cincinnati Christian University | naia-sb-2019-final, nfca-dii-2019-w12 |  Not ranked in the poll in effect: correct exclusion |
| 31 | bsb-2011-05-14-1 | Saint Francis IL | naia-bsb-2011-w07, ncbwa-dii-2011-0503 |  Not ranked (Univ. of St. Francis (Ill.) receiving votes) |
| 32 | wvb-2016-11-19-1 | La Sierra | naia-2016-final, avca-dii-2016-w11 |  Not ranked in the poll in effect: correct exclusion |
| 33 | mbb-2016-03-05-1 | Westmont | naia-di-2015-16-2016-03-01, naia-dii-2015-16-2016-03-02, nabc-dii-2015-16-2016-03-01 |  Not ranked (receiving votes) |
| 34 | sb-2014-04-26-1 | San Diego Christian College (Calif.) | naia-sb-2014-w06, nfca-dii-2014-w10 |  Not ranked (receiving votes) |
| 35 | bsb-2018-05-24-1 | Bluefield College (Va.) | naia-bsb-2018-w05, ncbwa-dii-2018-0516 |  Not ranked in the poll in effect: correct exclusion |
| 36 | sb-2025-05-09-1 | Saint Martin's | naia-sb-2025-final, nfca-dii-2025-w13 |  Not ranked (Saint Leo / Saint Xavier are different schools) |
| 37 | wvb-2018-11-29-1 | Piedmont International University | avca-dii-2018-w12, naia-2018-final |  Not ranked in the poll in effect: correct exclusion |
| 38 | sb-2021-05-21-1 | Hawaii Hilo | naia-sb-2021-final, nfca-dii-2021-w13 |  Not ranked in the poll in effect: correct exclusion |
| 39 | wbb-2011-03-02-1 | Concordia CA | naia-di-2010-11-2011-02-28, naia-dii-2010-11-2011-03-02, wbca-dii-2010-11-2011-03-01 |  Not ranked (the Concordias listed are Ore./Mich., NAIA DII) |
| 40 | wvb-2012-11-27-1 | Lindsey Wilson KY | naia-2012-final, avca-dii-2012-w11 |  Not ranked (receiving votes; Georgetown (Ky.) is a different school) |

Extra source spot-checks of exclusions:
- `bsb-2022-03-25/26` Azusa Pacific: the NCBWA DII poll of 3/23/22 (archives.sportswriters.net/ncbwa/news/2022/div2poll220323.html) does not list APU. Correctly excluded.
- `wbb-2018-12-15-1` Azusa Pacific: the WBCA DII PDF of Dec. 11, 2018 mentions APU only in the coaches' panel. Correctly excluded.

## 5. Every miss found and its cause (04:04 build)

| game | opponent | poll rank in effect | cause | status 04:25 |
|---|---|---|---|---|
| wvb-2002-09-24-1 | San Diego Christian | #25 Christian Heritage (Calif.), NAIA 9/24/02 | alias gap (renamed school) | missing |
| mbb-2001-02-03-1 | San Diego Christian | #11 Christian Heritage, NAIA DI 1/30/01 | alias gap (renamed school) | missing |
| mbb-2001-03-03-1 | San Diego Christian | #13 Christian Heritage, NAIA DI 2/27/01 | alias gap (renamed school) | missing |
| wvb-2003-08-23-1 | Concordia Portland | #17 Concordia (Ore.), NAIA pre 8/13/03 | alias gap | missing |
| wvb-2003-12-06-1 | Columbia (NAIA nationals) | #11 Columbia (Mo.), NAIA 11/18/03 | alias held as "open question" despite evidence | missing |
| mbb-2004-03-24-1 | Cumberland University | #5 Cumberland (Tenn.), NAIA DI 3/9/04 | over-broad AMBIGUOUS set | fixed |
| wbb-2005-11-18-1 | Seattle Pacific | #3 "Seattle Pacific University - Seattle", WBCA 11/8/05 | name suffix not normalized | fixed |
| mten-2021-02-12-1 | Concordia Irvine | #14, ITA 2/2/21 | poll-side alias made Concordia NY collide (dropped as ambiguous) | fixed |
| mten-2021-04-08-1 | Concordia Irvine | #16, ITA 4/8/21 (same day) / #17 on 3/23 | same as above | fixed (#17, same-day rule) |
| mbb-2011-01-14-1 | Concordia CA | #3, NAIA DI 1/10/11 (missing week) | missing poll week (now dropped by gap guard) | **now missing** (was #5) |
| wbb-2009-01-06-1 | Azusa Pacific | #5, NAIA DI 1/5/09 (missing week) | missing poll week (now dropped by gap guard) | **now missing** (was #5 via stale poll) |
| wvb-2006-09-01-2 | Westminster College | #25 Westminster (Utah)? | open identity question | open |
| wvb-2000-09-02-2 | Saint Mary | #7 College of Saint Mary (Neb.)? | open identity question | open |
| sb-2005 NAIA season (~18 games vs Cal Baptist, Point Loma, Concordia) | - | NAIA 2005 weekly polls not archived | missing poll weeks | unverified |

## 6. Recommendations
1. Add `Christian Heritage (Calif.)` → San Diego Christian (date-bounded before 2005), `Concordia Portland` → Concordia (Ore.), and `Columbia` (WVB only) → Columbia (Mo.).
2. Load the missing weeks from NAIA's official week-by-week PDFs rather than dropping rows. Priority: MSOC 2011 Polls 2 and 6; MBB 2010-11 Jan 10/17/24; MBB 2000-01 Rating #1 (Dec 5); WBB 2008-09 Jan 5. Then fix `msoc-2011-10-15-1` to #12 and restore `mbb-2011-01-14-1` as #3.
3. Confirm the Rating #2 date for 2000-01 NAIA DI MBB: the index says Jan 9, the archive says Jan 8.
4. Decide and document that tennis ranks below 25 count, and settle the same-day rule. That decision changes rows on the published page.
5. State the coverage window on the page. The list is complete only for the seasons and divisions the archive covers, and never for DI opponents.
