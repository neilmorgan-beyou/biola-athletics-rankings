# Audit: record vs. ranked opponents (`data/vs-ranked.json`)

Reviewed 2026-09-29. Adversarial review of `data/vs-ranked.json` (856 games, 268-573-15) and `scrape_vs_ranked.py`.

**How I checked it:** I re-downloaded all 465 season schedule pages listed in the 11 sports' season selectors on athletics.biola.edu. Every page's `og:title` starts with its own season label, so none of them fell back to the current season. I then parsed the pages with a separate parser that does not rely on the scraper's span logic. It flags any `#N`, `No. N`, `RV`, `NAIA #`, or `NCCAA` text anywhere in the opponent block, and I diffed the result against the dataset game by game. I also pulled text feeds for the random sample and for 12 pre-2009 seasons. Where the site cannot settle a question, I checked outside sources (NFCA, Biola and Campbellsville news).

## Bottom line

The scraper **copies the site faithfully**: 855 of 856 rows match the live page on rank marker, result, score, date and home/away. The one row my detector missed, a bare `15` in the rank field, also matches. The problems are **what the site's markers mean** and **what the headline claims**:

| # | Severity | Defect | Effect on 268-573-15 |
|---|---|---|---|
| 1 | High | Tournament seeds replace national ranks exactly in the biggest postseason games. The 2021 softball NCAA DII run beat the country's No. 1 and No. 2 teams, and none of it is counted. | Undercounts. At least +5-3 verified (+1 W vs RV) |
| 2 | High | Baseball 2018 NCCAA World Series: `#3/#4/#5/#8/#9` are **NCCAA seeds**, not rankings | Overcounts by 4-1, all of it in top-10 |
| 3 | High | "All-time" is really "games the SID marked, 2008-09 onward". Marking is patchy: whole seasons have none, and the same ranked opponent is often unmarked in rematches | Unknown. 177 candidate games (51-125-1) |
| 4 | Medium | RV (receiving votes) teams are counted as "ranked" | 57 games, 18-36-3 inside the headline |
| 5 | Medium | Mixed polls: NAIA and NCAA-DII cross-division ranks, D3 poll treated inconsistently, tennis ranks down to #50 | 6 cross-poll games. 20 tennis games ranked 26-50 (8-12) |
| 6 | Low | Opponent-name normalization produces wrong school names on the published page | Display only |
| 7 | Low | Latent scraper issues: no exhibition/scrimmage filter, a forfeit W, dual polls, score order, output path | Currently ~0 |

**Corrected W-L-T (only the corrections I verified):**
- Same definition as the page (RV counted): 268-573-15 → **270-575-15** (−4-1 baseball 2018 NCCAA seeds; +5-3 softball 2021 ranked and +1-0 RV NNU from the NCAA postseason)
- Strict numeric national ranks only (RV removed): **251-539-12**
- Baseball: 32-63 → **28-62**, top-10 15-30 → **11-29**, top-5 7-19 → **5-18**
- Softball: 27-91 → **33-94** (RV incl.), top-10 10-47 → **13-47**, top-5 2-30 → **5-30**

These figures are still a floor, not the true record. See defect 3.

---

## 1. Seeded postseason games drop ranked opponents (HIGH)

The scraper ignores any rank-field value containing "seed", which is correct for the number itself. But in the NCAA DII era the SID often typed **only** the seed into the rank field in the postseason. The opponent's real poll rank then disappears, and so does the game. There are 55 seed-only postseason games with results (23-32) outside the dataset.

**Verified example: Softball 2021.** The NFCA DII Top 25 of 5/12/21 (https://nfca.org/divnews/ncaa2/nfca-dii-top-25-coaches-poll-5-12-21) was the last poll before the regional. It lists No. 1 Augustana, No. 2 North Georgia, No. 11 Concordia Irvine, No. 12 West Texas A&M, and Northwest Nazarene receiving votes (Biola was No. 24). Biola's 2021 page shows those games only as seeds:

| Date | Page shows | Result | Poll rank (5/12/21) |
|---|---|---|---|
| May 20 | #3 seed Northwest Nazarene | W 4-3 | RV |
| May 21 | #5 seed Hawaii Hilo | W 9-0 | unranked |
| May 22 | #1 seed Concordia Irvine | L 2-3 | No. 11 |
| May 22 | #1 seed Concordia Irvine | W 2-1 | No. 11 |
| May 27 | #4 seed North Georgia | W 4-0 | **No. 2** |
| May 28 | #1 seed Augustana | W 3-0 | **No. 1** |
| May 29 | #4 seed North Georgia | W 5-2 | **No. 2** |
| May 31 | #6 Seed West Texas A&M (G1) | W 5-0 | No. 12 |
| May 31 | #6 Seed West Texas A&M (G2) | L 4-7 | No. 12 |
| Jun 1 | #6 Seed West Texas A&M (G3) | L 1-4 | No. 12 |

Three wins over top-2 teams are missing, which leaves softball's published "vs top 5" at 2-30. The rest of the 2021 softball season is marked only for the four Concordia regular-season games in March. The four April Concordia games (2-2) are unmarked.

Other seed-only games against opponents the SID marked as ranked elsewhere in the same season:
- Softball 2026: #1 seed Cal State San Marcos ×3 (1-2; marked #3 earlier) and #2 seed CSU East Bay (W; marked #17)
- Softball 2025: #3 seed Cal State San Marcos (L)
- Baseball 2025: #1 Seed Westmont (L; marked #4)
- MBB 2024-25: #5 seed CSU San Bernardino (L; marked #11)
- MWP 2021: #1 seed UC Davis (L; marked #8)
- MTEN 2026: #3 seed Hawaii Pacific (W)
- WTEN 2025: #1 seed Azusa Pacific (L)

**Fix:** keep seed-only games as "rank unknown" and look up the poll for each postseason date. Do not treat them as unranked.

## 2. Baseball 2018: NCCAA seeds counted as national ranks (HIGH)

The rank field reads `#8 Ottawa (Ariz.)`, `#5 Concordia University (Mich.)`, `#9 Bluefield College (Va.)`, `#4 Southwestern Christian`, `#3 Campbellsville (Ky.)`. All are NCCAA World Series games in Easley, SC, May 23-25, 2018. Those numbers are exactly the World Series seeds (Biola was the No. 1 seed; Pool A was SWC 4, Concordia 5, Ottawa 8, Bluefield 9; Campbellsville was 3). Sources: https://athletics.biola.edu/news/2018/5/17/nccaa-baseball-world-series-preview.aspx and https://campbellsvilletigers.com/news/2018/5/20/baseball-gears-up-for-final-stretch-of-2018-at-nccaa-world-series-in-easley-south-carolina.aspx.

The values have no "seed" text, so the filter passed them. All five sit in the top-10 bucket, and three of them in the top-5. **Remove: 4-1.** This is the only whole season of NCCAA-scale numbers in the data. The softball 2019, WSOC 2017 and WVB 2017-18 NCCAA games carry no numbers and are correctly absent.

## 3. "All-time" is overstated; coverage is patchy (HIGH, unquantifiable)

- **Pre-2008 claim: I could not falsify it, but that proves little.** No opponent in any of the 465 pages carries a rank marker before 2008-09 (fall/spring 2009). The text feeds I pulled show none either (MBB 2006-07 and 2007-08, WVB 2007 and 2008, baseball 2007 and 2008, softball 2008, WSOC/MSOC 2008, WBB 2007-08, tennis 2008). But Biola's NAIA/GSAC opponents (Azusa Pacific, Concordia, Point Loma, Cal Baptist, Vanguard) were routinely ranked before 2008. The site's markers simply start then. The heading "All-time record vs. ranked opponents" should read something like "since 2008-09, as marked on Biola schedules".
- **Seasons with no markers after marking began:** baseball 2011, 2013, 2016, 2017, 2019, 2020. Softball 2013, 2016, 2017. WVB 2017. WSOC 2015-2018. MBB 2017-18, 2021-22, 2023-24. WBB 2015-16, 2017-18, 2018-19, 2023-24. MTEN/WTEN 2009, 2011-13, 2015-19. In those seasons Biola played opponents that were marked ranked the season before or after. Examples: baseball 2013 had 30 such games (12-18), softball 2013 had 13 (1-12), tennis 2013 and 2015 had 8 each (0-8).
- **Same-season rematches left unmarked:** 177 completed games (**51-125-1**) are against an opponent the SID marked ranked in another game that same season. WVB 2015 is typical: #16 Westmont (Sep) but Westmont (Oct 30, L 1-3) unmarked; #9 Vanguard, but Nov 10 (W 3-0) unmarked; #14 Park, but the NAIA tournament rematch Dec 3 (W 3-1) unmarked. The whole 2015 NAIA national tournament, including a loss to Columbia (Mo.) (#1 in 2016), is unmarked. By sport: softball 39, baseball 37, MBB 25, WBB 22, WVB 17, MTEN 15, WTEN 10, MWP 6, MSOC 3, WSOC 2, WWP 1. Ranks do move week to week, so these are candidates, not proven misses. But they come close to the dataset's own win rate, and they show that marking depended on the SID and the week.
- **Six requested seasons, every game read:**
  - WVB 2015: 35 games, 9 marked, 9 in dataset. Rematch misses as above.
  - MBB 2016-17: 32 games, 10 marked, 10 in dataset. William Jessup (Dec 10, L) and Vanguard (Feb 14, W) unmarked while marked elsewhere.
  - Softball 2021: 45 games, 18 marked, 8 in dataset. The other 10 are the seed-only NCAA games in §1.
  - Baseball 2020: 54 listed, 14 played (COVID), 0 marked, 0 in dataset.
  - WSOC 2016: 22 games, 0 marked, 0 in dataset.
  - MWP 2024: 40 games, 14 marked, 10 in dataset. Excluded: Harvard (scrimmage, no result) and three NCAA DII-style regional seeds (#3 East McKendree W, #1 East Salem L, #2 East Gannon W). Those exclusions are correct.
- **Missed-marker check over all 465 pages:** apart from seeds, games with no result (PPD, Canceled, future), and NCCAA-label games, the dataset contains **every** marked game. There are no parser misses.

## 4. RV counted as "ranked" (MEDIUM)

57 games (18-36-3) are against teams only receiving votes. That includes two `RV/#1 (D3)` Pomona-Pitzer women's water polo games. The page calls the whole figure "record vs. ranked opponents". Either exclude RV (strict: 251-539-12 after the verified fixes) or say "ranked or receiving votes" in the heading.

## 5. The rank is not always a national rank in Biola's division (MEDIUM)

- **Cross-division/association polls counted as ranks:** `NAIA #9 Hope International` (softball 2019, 0-2, counted in top-10 while Biola was NCAA DII); `NAIA DII No. 5 Black Hills State` (WBB 2009-10, W, counted in top-5 from the NAIA Division II poll while Biola was NAIA DI); `NCAA DII No. 14 UC San Diego` (WBB 2009-10, L, while Biola was NAIA).
- **Inconsistent treatment:** the NAIA #9 counts as a No. 9 rank, but Pomona-Pitzer's `RV/#1 (D3)` counts only as RV.
- **Tennis:** ITA DII rankings run to about 50. 20 games against teams ranked 26-50 (8-12; MTEN 13, WTEN 7) count as "ranked", but no other sport goes past 25. The tennis ranked-game totals are therefore not comparable across sports.
- **Water polo:** the CWPA polls are all-division national polls (fine). Regional seeds such as `#2 East` are correctly excluded.
- **Not systematic elsewhere:** I did not see conference or regional ranks masquerading as national ones, apart from the NCCAA baseball seeds. Two spot checks agree with the national polls: Baseball 2021 `#6 Northwest Nazarene` (NNU was 8th in mid-May and finished 6th in the final NCBWA poll, https://nnusports.com/news/2021/6/22/baseball-finishes-sixth-in-final-ncbwa-poll.aspx), and MBB 2011-12 Concordia at #1, #16 and #4 (NAIA poll movement; Concordia dipped to 18th in January).
- **Timing:** the NNU #6 on May 6-7, 2021 may be the end-of-season number written in afterwards, since NNU was 8th in the May 13 poll. The page caption "as listed at game time" is unverified.

## 6. Normalization errors shown on the published page (LOW, display)

`normalize()` removes " - …" suffixes and parentheticals:
- `Louisiana State - Shreveport` → **"Louisiana State"** (MBB 2011 NAIA tournament W 71-70, shown as a win over "No. 4 Louisiana State")
- `Montana State - Northern` → **"Montana State"** (W 59-48)
- `Midland College` (2014) and `Midland University` (2016) → "Midland". The 2014 recap ("Eagles Whack the Warriors") shows the opponent was Midland University (Neb.). Sidearm's opponent record wrongly points to Midland College (Texas JUCO, gochaps.com), so the merge is right by accident.
- Ambiguous display names: `Ottawa (Ariz.)` → "Ottawa"; `Northwestern IA` → "Northwestern"; `Columbia MO` → "Columbia"; `Bethel IN` → "Bethel"; `Westminster UT` → "Westminster"; `Embry-Riddle FL` → "Embry-Riddle", kept separate from `Embry-Riddle Aeronautical (Ariz.)` (different campuses; correct but confusing).
- The pairs you asked about are fine. Concordia (Mich.) and Concordia (Ore.) stay separate from Concordia Irvine. San Diego State, UC San Diego and San Diego Christian stay distinct. Cal State LA, CSU San Marcos, CSU San Bernardino, CSU Dominguez Hills, CSU East Bay and CSU Northridge are all distinct, and their aliases merge correctly.

## 7. Scraper logic: other findings (LOW)

- **Exhibitions/scrimmages:** there is no filter. The only ranked scrimmage (`#15 Harvard (scrimmage)`, MWP 2024) was dropped only because it has no result. There is no current impact, but it would break if a scrimmage score were entered.
- **Forfeit:** MBB 2012-11-14 `#20 Cal State San Marcos W 78-85 "CSUSM Forfeits Post-Season"`. Biola lost on the court and the win is by forfeit. It is counted as a W and is the only W with a losing score. It should be footnoted.
- **Dual polls `#9/#14`, `#12/#18`, `#6/#9`** (MBB 2020-21): the scraper keeps the first number. The two `#9/#14` Point Loma games (1-1) fall into top-10 on one poll only.
- **Ties decided on PKs** (MSOC 2009 UT-Brownsville "Biola advances on PKs", 2011 Hannibal-LaGrange) are counted as T. That is correct under NCAA scoring but worth a note.
- **Score order:** MSOC 2010 `L 2-0` vs Vanguard is reversed from the site. It displays as a loss with a winning score.
- **No-result games** (PPD, Canceled, future) are excluded correctly. The "Baseball 2010 Point Loma" note appears twice because it is a doubleheader, not a duplicate. The dataset has no duplicate rows. Doubleheaders are separate `<li>`s with separate results, and all sampled doubleheaders check out.
- **Home/Away/Neutral** comes from Sidearm's home/away/neutral CSS class. For all 856 rows it matches the live page. Biola-hosted tournaments show as Home, as the site does.
- **Dates** match the box-score date labels. The only fall game out of its year is WVB 2020 on 2021-03-31, a real COVID spring game.
- **Live data:** the file includes in-progress 2026 fall games (MWP through 9/3). The headline will drift, so the page should give an as-of date.
- **Reproducibility:** the script writes `vs-ranked.json` next to itself and caches into `./cache/`, but the data lives in `data/` and no `cache/` directory exists. The published file was moved by hand after it was produced.
- **Page quirk to know about:** WBB 2009-10 lists a non-Biola game ("Black Hills State vs. Hope International"). It is harmless here because it has no W/L.

## Random sample (random.seed(11), 3 per sport + fill to 40)

Method: `random.seed(11)`; for each sport in sorted order, `random.sample(indices, 3)`; then 7 more drawn from the rest. Each game was checked against a fresh download of its `source_url`, confirming the page title and season, and against its text feed. **40/40 correct.** The 3 rows marked DH are doubleheaders where my matcher grabbed game 1. Game 2 on both the page and the feed equals the dataset (2014-04-12 softball L 0-1; 2011-04-01 softball L 2-13; 2014-04-12 baseball L 3-7).

| idx | Sport | Page title | Date | Dataset | Live page | Verdict |
|---|---|---|---|---|---|---|
| 57 | Baseball | 2022 Baseball Schedule | 2022-04-15 | #4 Point Loma L 3-13 Home | Apr 15 (Fri) / #4 Point Loma / L, 3-13 | match |
| 71 | Baseball | 2024 Baseball Schedule | 2024-04-19 | #15 Westmont L 1-4 Home | Apr 19 (Fri) / #15 Westmont (DH) / L, 1-4 | match |
| 59 | Baseball | 2022 Baseball Schedule | 2022-04-16 | #4 Point Loma L 1-18 Away | Apr 16 (Sat) / #4 Point Loma / L, 1-18 | match |
| 152 | Men's Basketball | 2015-16 Men's Basketball Schedule | 2016-03-05 | RV Westmont (SEMIFINALS) W 75-66 OT Neutral | Mar 5 (Sat) / RV Westmont (SEMIFINALS) / W, 75-66 OT | match |
| 160 | Men's Basketball | 2016-17 Men's Basketball Schedule | 2017-02-04 | #23 The Master's University (Calif.) L 76-91 Away | Feb 4 (Sat) / #23 The Master's University (Calif.) / L, 76-91 | match |
| 170 | Men's Basketball | 2019-20 Men's Basketball Schedule | 2020-02-01 | #9 Azusa Pacific L 79-90 Home | Feb 1 (Sat) / #9 Azusa Pacific / L, 79-90 | match |
| 193 | Men's Soccer | 2011 Men's Soccer Schedule | 2011-10-15 | #12 Azusa Pacific (BIOLA WEEKEND) L 1-2 OT Home | Oct 15 (Sat) / #12 Azusa Pacific (BIOLA WEEKEND) / L, 1-2 OT | match |
| 192 | Men's Soccer | 2011 Men's Soccer Schedule | 2011-09-15 | #24 La Sierra CA W 2-0 Away | Sep 15 (Thu) / #24 La Sierra CA / W, 2-0 | match |
| 213 | Men's Soccer | 2019 Men's Soccer Schedule | 2019-09-21 | #7 CSU Los Angeles L 2-3 (2OT) Away | Sep 21 (Sat) / #7 CSU Los Angeles / L, 2-3 (2OT) | match |
| 257 | Men's Tennis | 2024 Men's Tennis Schedule | 2024-03-07 | #20 Azusa Pacific L 1-4 Home | Mar 7 (Thu) / #20 Azusa Pacific / L, 1-4 | match |
| 267 | Men's Tennis | 2025 Men's Tennis Schedule | 2025-03-19 | #45 Hawaii Hilo W 6-1 Home | Mar 19 (Wed) / #45 Hawaii Hilo / W, 6-1 | match |
| 266 | Men's Tennis | 2025 Men's Tennis Schedule | 2025-03-15 | #29 Colorado Mesa University W 7-0 Home | Mar 15 (Sat) / #29 Colorado Mesa University / W, 7-0 | match |
| 328 | Men's Water Polo | 2026 Men's Water Polo Schedule | 2026-08-28 | RV George Washington L 13-16 Neutral | Aug 28 (Fri) / RV George Washington / L, 13-16 | match |
| 289 | Men's Water Polo | 2022 Men's Water Polo Schedule | 2022-09-03 | RV Navy L 7-12 Away | Sep 3 (Sat) / RV Navy / L, 7-12 | match |
| 284 | Men's Water Polo | 2021 Men's Water Polo Schedule | 2021-10-01 | RV NAVY L 3-14 Neutral | Oct 1 (Fri) / RV NAVY / L, 3-14 | match |
| 391 | Softball | 2018 Softball Schedule | 2018-04-20 | #13 Dixie State L 1-3 Home | Apr 20 (Fri) / #13 Dixie State / L, 1-3 | match |
| 372 | Softball | 2014 Softball Schedule | 2014-04-12 | #1 Concordia University (Calif.) L 0-1 Home | Apr 12 (Sat) / #1 Concordia University (Calif.) / L, 6-9 | match (DH game 2; confirmed in page + feed) |
| 352 | Softball | 2011 Softball Schedule | 2011-04-01 | #1 California Baptist L 2-13 (5 inn.) Home | Apr 1 (Fri) / #1 California Baptist (DH) / L, 0-8 (6 inn.) | match (DH game 2; confirmed in page + feed) |
| 463 | Women's Basketball | 2008-09 Women's Basketball Schedule | 2009-03-04 | No. 19 Azusa Pacific L 56-61 Away | Mar 4 (Wed) / No. 19 Azusa Pacific / L, 56-61 | match |
| 520 | Women's Basketball | 2016-17 Women's Basketball Schedule | 2017-01-03 | #17 The Master's University (Calif.) W 74-63 Home | Jan 3 (Tue) / #17 The Master's University (Calif.) / W, 74-63 | match |
| 540 | Women's Basketball | 2022-23 Women's Basketball Schedule | 2023-01-25 | #18 Azusa Pacific L 69-73 Away | Jan 25 (Wed) / #18 Azusa Pacific / L, 69-73 | match |
| 585 | Women's Soccer | 2014 Women's Soccer Schedule | 2014-10-25 | #11 Westmont College (Calif.) L 1-3 Away | Oct 25 (Sat) / #11 Westmont College (Calif.) / L, 1-3 | match |
| 547 | Women's Soccer | 2009 Women's Soccer Schedule | 2009-10-10 | No. 4 Azusa Pacific (Parent's Weekend) L 1-3 Home | Oct 10 (Sat) / No. 4 Azusa Pacific (Parent's Weekend) / L, 1-3 | match |
| 583 | Women's Soccer | 2014 Women's Soccer Schedule | 2014-10-14 | #5 Concordia University (Calif.) L 1-4 Away | Oct 14 (Tue) / #5 Concordia University (Calif.) / L, 1-4 | match |
| 627 | Women's Tennis | 2023 Women's Tennis Schedule | 2023-04-11 | #50 Concordia L 2-5 Away | Apr 11 (Tue) / #50 Concordia / L, 2-5 | match |
| 630 | Women's Tennis | 2024 Women's Tennis Schedule | 2024-03-28 | #41 Concordia L 0-7 Away | Mar 28 (Thu) / #41 Concordia / L, 0-7 | match |
| 643 | Women's Tennis | 2026 Women's Tennis Schedule | 2026-04-15 | #33 2nd-Seed Point Loma L 3-4 Neutral | Apr 15 (Wed) / #33 2nd-Seed Point Loma / L, 3-4 | match |
| 801 | Women's Volleyball | 2024 Volleyball Schedule | 2024-11-09 | #7 Chaminade L 1-3 Home | Nov 9 (Sat) / #7 Chaminade / L, 1-3 | match |
| 684 | Women's Volleyball | 2011 Volleyball Schedule | 2011-08-26 | #16 Bellevue NE W 3-0 Home | Aug 26 (Fri) / #16 Bellevue NE / W, 3-0 | match |
| 803 | Women's Volleyball | 2025 Volleyball Schedule | 2025-11-05 | #4 Point Loma L 1-3 Home | Nov 5 (Wed) / #4 Point Loma / L, 1-3 | match |
| 806 | Women's Water Polo | 2022 Women's Water Polo Schedule | 2022-02-18 | #8 Fresno State L 7-15 Away | Feb 18 (Fri) / #8 Fresno State / L, 7-15 | match |
| 839 | Women's Water Polo | 2025 Women's Water Polo Schedule | 2025-01-25 | #10 Loyola Marymount L 8-18 Neutral | Jan 25 (Sat) / #10 Loyola Marymount / L, 8-18 | match |
| 810 | Women's Water Polo | 2022 Women's Water Polo Schedule | 2022-03-11 | RV CSU East Bay L 5-15 Neutral | Mar 11 (Fri) / RV CSU East Bay / L, 5-15 | match |
| 62 | Baseball | 2023 Baseball Schedule | 2023-03-02 | #23 Hawaii Hilo L 1-7 Away | Mar 2 (Thu) / #23 Hawaii Hilo (DH) / L, 1-7 | match |
| 36 | Baseball | 2014 Baseball Schedule | 2014-04-12 | #18 Concordia University (Calif.) L 3-7 Away | Apr 12 (Sat) / #18 Concordia University (Calif.) / W, 5-2 | match (DH game 2; confirmed in page + feed) |
| 202 | Men's Soccer | 2013 Men's Soccer Schedule | 2013-11-16 | #13 Concordia University (Calif.) L 2-3 Away | Nov 16 (Sat) / #13 Concordia University (Calif.) / L, 2-3 | match |
| 256 | Men's Tennis | 2023 Men's Tennis Schedule | 2023-04-08 | #24 Point Loma W 4-3 Home | Apr 8 (Sat) / #24 Point Loma / W, 4-3 | match |
| 640 | Women's Tennis | 2026 Women's Tennis Schedule | 2026-02-21 | #20 Point Loma L 2-5 Home | Feb 21 (Sat) / #20 Point Loma / L, 2-5 | match |
| 30 | Baseball | 2014 Baseball Schedule | 2014-03-12 | #16 California State University-San Marcos L 3-9 Home | Mar 12 (Wed) / #16 California State University-San Marcos / L, 3-9 | match |
| 828 | Women's Water Polo | 2024 Women's Water Polo Schedule | 2024-02-24 | #13 UC San Diego L 7-10 Neutral | Feb 24 (Sat) / #13 UC San Diego / L, 7-10 | match |
