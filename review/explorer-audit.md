# Audit: "Vs. ranked opponents" tab (rankings-history-preview.html)

Reviewed 2026-09-30. I recomputed the numbers independently from `data/vs-ranked-verified.json` + `polls/*.json`
(`review/scratch-explorer/recompute.py`), diffed them against the rendered tables
(`review/scratch-explorer/parse_html.py`), and exercised the filters in headless Chrome
(`review/scratch-explorer/filtertest.html`, output in `dom.html`). No project files were modified.

## Bottom line

- **The arithmetic is right.** All 235 record rows × 4 columns match my recompute (0 diffs). The 224 covered
  sport-seasons match, All-seasons rows equal the sum of their season rows, and the 1,781 Games rows match game for game.
  Ties (18) reconcile, and ranks > 25 (35 tennis games) are correctly left out of the Top 25 column.
- **The inputs are not what the tab claims.** Every bug below comes from the join, the coverage gate, or the labels,
  not from the counting. Most severe first.

---

## 1. Ranked opponents silently dropped by name matching (HIGH, confirmed)

`join_games_polls.py` drops a game when the opponent's name doesn't resolve to the poll's name, or when it resolves
to two teams in one poll (AMBIGUOUS). Neither case shows up on the page. Confirmed misses in covered seasons:

| Game | Result | Poll in effect | Rendered row, should be |
|---|---|---|---|
| wbb-2005-11-18-1 Seattle Pacific | L 68-77 | NCAA DII 2005-11-08, **No. 3** "Seattle Pacific University - Seattle" | WBB 2005-06 Top5/10/25 `0-2 / 0-4 / 2-7` → `0-3 / 0-5 / 2-8` |
| mbb-2004-03-24-1 Cumberland University | L 64-68 | NAIA DI 2004-03-09, **No. 5** "Cumberland (Tenn.)" (the same school; `cumberland` is on the AMBIGUOUS list) | MBB 2003-04 `0-3 / 0-3 / 1-4` → `0-4 / 0-4 / 1-5` |
| mbb-2005-03-18-1 Southern Poly | **W** 65-63 | NAIA DI 2005-03-01, **No. 2** "Southern Polytechnic (Ga.)" | MBB 2004-05 `1-0 / 2-0 / 4-3` → `2-0 / 3-0 / 5-3` (a missing upset of No. 2) |
| wsoc-2015-08-27-1 University of Northwestern (Ohio) | T 2-2 | NAIA 2015-08-18, **No. 2** "Northwestern Ohio" | WSO 2015 is missing a tie in every column but No. 1 |
| wvb-2006-08-26-2 Savannah College of Arts and Design | L 2-3 | NAIA 2006-08-16, **No. 12** "Savannah Art & Design (Ga.)" | WVB 2006 Top 25 short one loss |
| mten-2021-02-12-1, mten-2021-04-08-1 Concordia Irvine | L 1-4, L 1-4 | ITA DII, **No. 14 / No. 16** "Concordia University (Irvine)" | Dropped as AMBIGUOUS because "Concordia College (New York)" also matched. MTEN 2021 Top 25 short 0-2 (Top 10 unaffected) |

Likely misses (same pattern, need a human check):

- wvb-2003-12-04-1 L 0-3 and wvb-2003-12-05-3 W "1-0": "Saint Mary's NE" vs No. 3 "St. Mary (Neb.)".
- wvb-2003-12-06-1 L 0-3: "Columbia" vs No. 11 "Columbia (Mo.)" at NAIA nationals.
- wvb-2006-09-01-2 L 2-3: "Westminster College" vs No. 25 "Westminster (Utah)".
- wvb-2000-09-02-2 L 0-3: "Saint Mary" vs No. 7 "St. Mary (Neb.)". The least certain of these.

The join's own report (`polls/join-report.md`, "Near misses") already lists Seattle Pacific, Cumberland and Northwestern
Ohio, and it lists the two AMBIGUOUS tennis games. They were never resolved.

## 2. Probable false positive: wrong Ottawa (MEDIUM)

wsoc-2017-11-11-1 "Ottawa", W 3-0, at the **NCCAA West Regional Championship**, is credited as a win over **No. 13
Ottawa (Kan.)**. This came through a loose match (`'Ottawa' = 'Ottawa (Kan.)'`). The NCCAA West regional is Ottawa
**(Ariz.)**'s event: Biola played "Ottawa (Ariz.)" in the same event in 2018. Also, No. 13 Ottawa (Kan.) would have been
in the NAIA national tournament that week. As rendered, WSO 2017 and WSO All-seasons are probably one win too high in
the Top 25 column.

## 3. Coverage gate counts seasons that are only partly archived (HIGH for WBB 1998-99, MEDIUM otherwise)

`build_vs()` treats a season as covered if **any one** poll of Biola's division has a `release_date`. Games before the
first archived poll, or inside a gap in the archive, are then counted as "not ranked." The tab still presents these
seasons as fully checked:

- **Women's Basketball 1998-99**: only **1** poll (Week 1 = final regular season, 1999-03-02). 32 of 33 games were
  played before it. The row shows `– – – –` (no ranked opponents), and the season is advertised in "Women's Basketball
  1998-25." This row should not exist.
- **Men's Basketball 2010-11**: NAIA DI Weeks 3-5 are missing. There is a 49-day gap (2010-12-13 to 2011-01-31), so
  13 games were matched to a poll more than 21 days old.
- **Men's Tennis 2018**: 5 polls. The Apr 4 through May 16 ITA lists are missing (see `gaps`), so 11 games used the
  2018-03-28 list or a staler one.
- **No preseason poll archived**: WBB 2000-01 (9 games before the first poll), MBB 1999-00 (7), WBB 2020-21 (5), and
  **the current season, WSO 2026**. The NCAA DII women's preseason poll isn't archived, even though the men's 2026 preseason
  is. Biola lost 8/29 to Cal Poly Pomona, No. 2 in the first poll three days later, and the 2026 WSO row reads `– – – –`.
  MSO 2025 has the same problem: L 9/6 to CSU San Bernardino, No. 8 in the first poll.
- The poll files carry `complete:false` flags and a `gaps` list. The builder reads neither one.

## 4. Cross-division opponents are counted inconsistently (MEDIUM)

The coverage gate only checks Biola's **own** division. The join, however, counts an opponent ranked in **any**
archived division poll (45 counted games use another division's poll). So a ranked opponent from the other
division counts only in years when that other poll happens to be archived:

- MBB NCAA DII polls are missing 1999-00 to 2003-04, and NAIA DII polls are missing 2005-06 to 2007-08.
- Baseball NCAA DII polls are missing 1998, 2000-02, 2006 and 2007.
- WBB NCAA DII polls are missing 1998-99 and 1999-00.
- Tennis has no NCAA DII polls at all for 2007-17 and no NAIA polls at all for 2018-26.
- Basketball has no NAIA polls after 2018-19.

As a result, the same kind of game (for example, NAIA-era Biola against a ranked DII school) is counted in some seasons
and silently uncounted in others. The tab's text doesn't disclose this.

## 5. Season labels wrong for basketball seasons with no ranked games, which breaks the season filter (MEDIUM, confirmed in Chrome)

`label.setdefault(...)` takes each row's label from the first game. If a season had no ranked games, the label falls
back to `str(season_start)`. The rendered rows:

- `Men's Basketball | 2021` should be **2021-22**.
- `Women's Basketball | 2020` should be **2020-21**.
- `Women's Basketball | 1998` should be **1998-99**.

Headless Chrome confirms the effect:
- Season = **2021-22** shows only WBB. MBB 2021-22 is missing.
- Season = **2021** shows MBB mixed in with nine fall and spring programs.
- Season = **1998** shows Baseball 1998 plus WBB "1998".
- There is **no "1998-99" option**.

## 6. Forfeits and scores displayed misleadingly (LOW to MEDIUM)

- These games are counted as **wins vs. ranked** with no forfeit marker in the Games table:
  - mbb-2012-11-14-1: renders "W 78-85" vs No. 20 CSUSM. Biola lost on the court; CSUSM later forfeited.
  - bsb-2013-04-02-1 vs No. 11 CSUSM, same "CSUSM Forfeits Post-Season" note.
  - mten-2016-03-19-1: "SDC FORFEIT", W 9-0 vs No. 11.

  Counting official results is defensible, but a reader can't tell these apart from real wins, and "W 78-85" looks
  like a typo.
- **All of MBB 1999-00** has scores stored opponent-first, for example "W 53-61" vs No. 23 Westmont and "L 118-108" vs
  No. 5 Georgetown (KY). The source cache shows other old pages list winner-first, for example softball 2010-03-02
  "L, 6-1". The results are right; the displayed scores contradict them. 14 rendered games have a result/score conflict.
- wvb-2003-12-05-2 "W 1-0" vs No. 7 Houston Baptist is a volleyball score of 1-0. All four NAIA-nationals matches are
  dated 12-05, so the "poll in effect" date may be wrong too.

## 7. Minor

- **Coverage sentence**: "Men's Basketball 1999-25" / "Women's Basketball 1998-25" reads as ending in 2025. It actually
  runs through 2025-26, and the WBB start includes the 1-poll 1998-99.
- **Season dropdown order is unstable**: ties on `season_start` come out in set order ("2025-26, 2025", then "2024,
  2024-25"). A "2026" pick mixes spring 2026 (2025-26 school year) with fall 2026. The school-year rule is used for
  coverage but not for labels or the filter.
- **Games table lists 35 games vs No. 26-67** (ITA Top 50/75 lists). No record column counts these games. Defensible,
  but not explained on the page.
- **216 games fall on their poll's release day** and use the new poll. A game played before the poll came out that day
  is attributed to it.
- **Possible duplicate**: sb-2016-04-09-1 and -2 vs No. 18 Arizona Christian are both "W 5-4". The source page lists it
  twice, so this is probably real, but check it.
- **Public page JSON-LD**: the WebPage `description` in `rankings-history-sportfile-body.html` still says "…and each
  program's record against ranked opponents". The public page has no such section.

## Checks that passed

- Recompute vs. render: 0 cell diffs, 0 missing or extra rows, 0 game diffs. All-seasons = Σ seasons for every
  program and category.
- Division rule: basketball uses NAIA DI through 2016-17. Spring sports shift one year (Baseball/Softball/Tennis 2017 are
  NAIA, 2018 are DII). Water polo "mixed" always passes.
- Poll in effect: every verified game's poll is the latest poll of that division released on or before game day
  (0 violations). Season labels are consistent with game dates. There are no exhibitions in the verified set (the join
  filters `exhibition`), and no duplicate game_ids.
- Ties: the `tied` flag matches the poll in all 1,800 games. T-n counts as n: T-1 USC counts as No. 1, T-5 as Top 5,
  T-25 as Top 25. That is a consistent choice.
- Default view (Chrome): the Record table shows exactly the 11 All-seasons rows ("11 of 235 rows"), and Games shows
  1,781 of 1,781. Program/season/result filters on Games work (Softball + 2026 + W = 7 rows, all correct; T = 18). The
  2026 current season appears for the 9 programs with a 2026 row.
- Public body `rankings-history-sportfile-body.html` has no `rk-vs` panel, no vs tab and no vs data. The only
  references are the shared CSS selector `#t-vsgames` and the JS string `'t-vsrec'`, which are inert.
