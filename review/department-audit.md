# Department standings audit: Directors' Cup and conference all-sport awards

Audited files: `data/directors-cup.json` and `data/conference-cup.json`, plus the `STATUS_FIXES` and `place_label` code in `build_rankings_page.py`. The builder changed while this audit ran: `award not held` with an interim place now renders as "Not completed (113th at interim)". Audit date: 2026-09-29.

How the checks were done:
- Every NACDA PDF cited as a source was downloaded and its text extracted. For each one I checked Biola's rank, points, ties (every row that shares the rank) and the school count.
- GSAC and PacWest numbers were checked against the conference's own pages: the live site, or web.archive.org captures of gsacsports.org.
- Wayback Machine (web.archive.org) was online during this audit. It was offline during the original research.

## Defects, most severe first

1. **HIGH: all 8 "no data found" NAIA seasons (1998-99 to 2005-06) can be recovered from official NACDA standings.**
   - For 2003-04, 2004-05 and 2005-06, the final-standings PDFs are linked ("Standings in PDF Format") from the very nacda.com release pages the rows already cite as `source_url`.
   - 1998-99 to 2002-03 are on Wayback, as captures of the old NACDA graphics host (graphics.fansonly.com).
   - The recovered finishes tie out exactly with Biola's own milestone counts. See "Recovered data" below.
2. **HIGH: GSAC 2011-12 is marked "no data found". Biola actually finished 2nd, with 7.81, of 10 schools.** Source: the GSAC's own All Sports Award page. That makes 2nd-place finishes in 2011-12, 2015-16 and 2016-17. The open gap note, "earlier 2nd could be 2015-16 or a pre-2012 year", is resolved: it was both.
3. **MEDIUM: the GSAC 2016-17 score of 7.82 is almost certainly a typo in the Biola story.**
   - The same story gives 110 points over 14 sports, which is 7.857, so 7.86.
   - Its other numbers are internally consistent: Westmont 101/12 = 8.42, Vanguard 86/11 = 7.82, The Master's 85/11 = 7.73.
   - Biola's "7.82" matches Vanguard's figure, so it looks copied. The data note about "Vanguard also had 7.82 but is listed 3rd" describes a tie that is an artifact of that typo.
   - No GSAC final for 2016-17 was captured on Wayback; the last capture, 2017-05-14, still shows the fall standings. So this cannot be settled from a primary source. Either use 7.86 with a note, or keep 7.82 and flag the conflict.
4. **MEDIUM: the "Score" column mixes units and scales.**
   - The academic rows are department GPA (3.448, 3.51) and sit in the same sortable column as points-per-sport averages.
   - Even the athletic averages do not share a scale. GSAC changed its formula:
     - 2011-12: 10 points for a title, 9 for 2nd, and so on (no participation point).
     - 2012-13 and 2013-14: 8 points for a title, plus 1 point per sponsored sport (maximum 9).
     - 2014-15 to 2016-17: 9 points for a title, plus 1 point (maximum 10).
   - PacWest averages run on a scale set by the number of schools (Azusa Pacific's record is 13.38).
   - So a GSAC 7.8 and a PacWest 10.2 are not comparable, and sorting by Score is meaningless. The subtitle ("published average per sport") is false for the academic rows.
5. **MEDIUM: PacWest Academic Achievement Award 2025-26 is labeled "did not place". That contradicts the page's own legend.**
   - The legend says "Did not place" means final standings exist and Biola is not in them.
   - The GPA ranking covers every member school, and Biola had a GPA. The release simply names only the top five.
   - Biola was 6th or lower, but was not unplaced. Use "no data found (not in published top 5)" or "6th or lower".
6. **MEDIUM: two academic years can be recovered.**
   - 2020-21: 4th with a 3.45 GPA.
   - 2021-22: in the top 5; 4th or 5th, and probably 5th.
7. **LOW-MEDIUM: `schools_scored` is inconsistent, and the "highest rank printed" rule undercounts when there is a tie at the bottom of the standings.**
   - DII 2023-24: 251 schools scored, not 238 (13 schools are tied at 238).
   - NAIA 2012-13: 204, not 203.
   - DII 2024-25: 260, not 259.
   - Blank cells that can be filled:
     - NAIA 1995-96: 268; all listed schools have points.
     - NAIA 1997-98: 245.
     - NAIA 2006-07: 223.
8. **LOW: the PacWest 2017-18 note says "116.5 points across 14 sports". The numbers imply 15 sports** (116.5 / 7.7667 = 15.00; 2018-19 is 128.2 / 8.5447 = 15.00, and that story says "15 sponsored PacWest sports"). The school count is probably 14: the PacWest 2017-18 academic release says "14 member institutions". That is an inference, not confirmed for the Cup.
9. **LOW: the interim label ignores ties.** The DII 2019-20 fall interim is **T-113th** (Biola and Wayne State (MI), 49 pts each). `tied` is false in the data, and `place_label` never adds "T-" for interim places.
10. **LOW: the Azusa Pacific 18-year GSAC streak is cited to presidiosports.com, but that article does not say it.**
    - The article only says Westmont's previous win was 1993-94.
    - The GSAC's own page does say it: "Westmont College has reclaimed the trophy after the award has resided with Azusa Pacific over the last 18 years" (https://web.archive.org/web/20130718201836/http://www.gsacsports.org/f/GSAC_All_Sports_Award_presented_by_Dukes.php). Cite that instead.
11. **LOW: two statements in the `gaps` notes are wrong.**
    - "A 2009 search snippet says 16th in 2008-09 was Biola's best since 1995-96." The 2010 Biola story says 16th was the "previous best-ever finish". The recovered data agrees: no finish better than 16th before 2008-09.
    - The 2016 story's "eighth top-20" and "16th top-50" are the miscounts; the right counts are 9th and 17th. The 2010, 2011 and 2017 counts are right.
12. **INFO: the NAIA 2015-16 source PDF (`NAIAStandJune14update.pdf`) has a stale header** that reads "2014-15 ... As of June 11, 2015". The body is the 2015-16 final: Biola 7th with 633.50, whereas the real 2014-15 file has Biola 25th with 429. The row is correct, but anyone opening the link will see the wrong year in the header.
13. **INFO: the page legend defines "Did not place", "Not eligible" and "No data found", but not "Award not held" or "Not completed".** Both appear in the Directors' Cup table.
14. **Not a defect: GSAC 1994-95 is present** in `conference-cup.json` (the first GSAC row) and renders on the page as "No data found".

## Directors' Cup: per-row verdicts

| Season | Body | Data | Verdict | Evidence |
|---|---|---|---|---|
| 1995-96 | NAIA | 148th, 89.0, schools null | **Correct.** No tie: Xavier (La.) 93.0 and Green Mountain 92.0 are above; Kansas Newman and Southern Oregon St. 87.0 are below. `schools_scored` can be 268 (every listed school has points). | 9596naiafinal.pdf; 147 schools have more than 89.0 |
| 1996-97 | NAIA | T-114th, 120.5, 263 | **Correct** (tied with South Dakota Tech, 120.5) | 9697NFinal_2_.PDF |
| 1997-98 | NAIA | T-41st, 150 | **Correct** (tied with Oklahoma Christian and Southern-New Orleans). `schools_scored` can be 245 (245 listed; last rank T-220) | 9798NFinal.PDF |
| 1998-99 | NAIA | no data found | **WRONG: T-28th, 180 pts** (tied with California Baptist). 234 scored per the release | Recovered, see below |
| 1999-2000 | NAIA | no data found | **WRONG: 18th, 349.5.** 234 scored | Recovered |
| 2000-01 | NAIA | no data found | **WRONG: 20th, 328.5.** 239 scored | Recovered |
| 2001-02 | NAIA | no data found | **WRONG: 80th, 165.** 245 scored | Recovered |
| 2002-03 | NAIA | no data found | **WRONG: 43rd, 293.** 246 scored per release (244 rows in PDF) | Recovered |
| 2003-04 | NAIA | no data found | **WRONG: 19th, 420.** 236 scored | Recovered |
| 2004-05 | NAIA | no data found | **WRONG: 39th, 339.** PDF lists the top 100 only, so the school count is unknown | Recovered |
| 2005-06 | NAIA | no data found | **WRONG: 60th, 259.5.** Top 100 only | Recovered |
| 2006-07 | NAIA | 41st, 360.5 | **Correct.** No tie. `schools_scored` can be 223 | naiafinalstand.pdf |
| 2007-08 | NAIA | 35th, 439.5, 232 | **Correct.** Season split 140 / 149.5 / 150 verified | naiajune11standings.pdf |
| 2008-09 | NAIA | 16th, 519.25, 192 | **Correct** | NAIAJune19.pdf |
| 2009-10 | NAIA | 12th, 585.08, 196 | **Correct** | naiadcupjune23.pdf |
| 2010-11 | NAIA | 11th, 582.5, 201 | **Correct** | naia2011final.pdf |
| 2011-12 | NAIA | 12th, 581.0, 195 | **Correct** | finalnaia.pdf |
| 2012-13 | NAIA | 29th, 370.5, 203 | **Place and points correct. Schools should be 204** (tie at 203) | 13naiafinalstandings.pdf |
| 2013-14 | NAIA | 18th, 502.5, 189 | **Correct** | June10NAIA.pdf |
| 2014-15 | NAIA | 25th, 429.0, 186 | **Correct per the official PDF.** St. Francis (IL) is 24th with 432.5; the Biola story's "24th" is wrong. 186 schools are listed | 1415NAIAJune11.pdf |
| 2015-16 | NAIA | 7th, 633.5, 190 | **Correct** (the PDF header is mislabeled 2014-15) | NAIAStandJune14update.pdf |
| 2016-17 | NAIA | 18th, 512.0, 199 | **Correct** | June8OverallNAIA.pdf |
| 2016-17 | NCAA DII | not eligible | **Correct** (see status attack below). Biola is absent from the final | June8FinalDIIOverallUpdate.pdf |
| 2017-18 | NCAA DII | not eligible | **Correct.** Biola is absent | June14overallDII.pdf |
| 2018-19 | NCAA DII | not eligible | **Correct.** Biola is absent | DIIJune12Overall.pdf |
| 2019-20 | NCAA DII | award not held / interim 113th | **Status correct. Interim should be T-113th** (tied with Wayne State (MI), 49.00) | Dec19DII.pdf |
| 2020-21 | NCAA DII | award not held | **Correct** | NACDA archive: "2019-20/2020-21 No Standings due to COVID-19" |
| 2021-22 | NCAA DII | 142nd, 138.0, 251 | **Correct.** Season split verified; the PDF column order is Spring, Winter, Fall (87 / 0 / 51) | 22DIIFINAL.pdf |
| 2022-23 | NCAA DII | 104th, 206.0, 251 | **Correct** | DIIFinalStandings22_23_Update2.pdf |
| 2023-24 | NCAA DII | 108th, 187.0, 238 | **Place and points correct. Schools should be 251** (13 schools tied at 238) | 23.24DII_FinalOverallStandings.pdf |
| 2024-25 | NCAA DII | 60th, 321.5, 259 | **Place and points correct. Schools should be 260** (tie at 259) | 24.25DII_FinalOverallStandings.pdf |
| 2025-26 | NCAA DII | 79th, 264.0, 251 | **Correct.** "3rd among PacWest" verified (Point Loma 24th, Azusa Pacific 47th) | 25.26DII_FinalOverallStandings.pdf |
| 2017-18, 2018-19 | NCCAA | no data found (1st at interim) | Not re-verified against primary sources; no final standings were found in this pass either | - |

## Conference all-sport awards: per-row verdicts

| Season | Award | Data | Verdict | Evidence |
|---|---|---|---|---|
| 1994-95 to 2010-11 | GSAC | no data found | **Unresolved.** No GSAC standings page exists on Wayback before the 2011-12 page. The GSAC Year in Review pages for 1998-99 to 2006-07 do not include the award. The award existed and Azusa Pacific won every year (GSAC's own statement), so Biola was never 1st. Per the 2017 "ties best-ever" line, Biola never finished better than 2nd | gsacsports.org captures, 2000-2012 |
| 2011-12 | GSAC | no data found | **WRONG: 2nd, 7.81, of 10 schools.** Azusa Pacific 9.85; Biola 7.81; Westmont 7.42; Concordia 7.38; Fresno Pacific 7.33; Vanguard 7.04; Point Loma 6.96; The Master's 6.00; San Diego Christian 3.93; Hope Intl 3.50. Scale: 10 points for a title | https://web.archive.org/web/20121026151436/http://gsacsports.org/f/All_Sports_Award.php |
| 2012-13 | GSAC | 5th, 5.88, 8 | **Correct.** Primary source: 76.5 points / 13 sports | https://web.archive.org/web/20130718201836/http://www.gsacsports.org/f/GSAC_All_Sports_Award_presented_by_Dukes.php |
| 2013-14 | GSAC | 4th, 6.54, 8 | **Correct.** 85 points / 13 sports | https://web.archive.org/web/20140703051004/http://www.gsacsports.org/f/GSAC_All_Sports_Award_presented_by_Dukes.php |
| 2014-15 | GSAC | 5th, 6.58, 9 | **Correct.** 85.5 points / 13 sports | https://web.archive.org/web/20150818161733/http://www.gsacsports.org/f/GSAC_All_Sports_Award_presented_by_Dukes.php |
| 2015-16 | GSAC | 2nd, points null, schools null | **Place correct. Fill in 8.07 (113 points / 14 sports) and 9 schools.** Westmont 8.71; Vanguard 7.82 is 3rd | https://web.archive.org/web/20160706204501/http://www.gsacsports.org/f/GSAC_All_Sports_Award_presented_by_Dukes.php |
| 2016-17 | GSAC | 2nd, 7.82, 9 | **Place and school count correct. The score is suspect: 110 / 14 = 7.86** (see defect 3) | athletics.biola.edu 2017/5/24 story |
| 2017-18 | PacWest Cup | 8th, 7.7667 | **Place and score correct.** The note should say 15 sports, not 14. Schools are probably 14 (inferred) | athletics.biola.edu 2018/5/23 |
| 2018-19 | PacWest Cup | 4th, 8.54, 12 | **Correct** (8.5447; 128.2 points / 15 sports) | athletics.biola.edu 2019/5/22 |
| 2019-20, 2020-21 | PacWest Cup | award not held | **Correct** ("canceled during the previous two academic years") | thepacwest.com 2022/5/25 and 2023/5/22 |
| 2021-22 | PacWest Cup | 2nd, 10.29, 11 | **Correct** | thepacwest.com 2022/5/25 |
| 2022-23 | PacWest Cup | 4th, 9.93, 11 | **Correct** (Azusa Pacific 12.54, Point Loma 11.59, Concordia 10.08) | thepacwest.com 2023/5/22 |
| 2023-24 | PacWest Cup | 4th, 10.25, 11 | **Correct** (Concordia 10.50 is 3rd) | thepacwest.com 2024/5/28 |
| 2024-25 | PacWest Cup | 3rd, 10.21, 14 | **Correct** (Point Loma 12.36, Azusa Pacific 10.58) | thepacwest.com 2025/5/15 |
| 2025-26 | PacWest Cup | 4th, 10.1, 13 | **Correct** (Point Loma 13.00, Fresno Pacific 10.38, Azusa Pacific 10.27) | thepacwest.com 2026/5/18 |
| 2017-18 | PacWest Academic | no data found | **Still unresolved.** Biola was not in the top 3 (Dominican 3.421, Point Loma 3.395, Chaminade 3.28) and not among the three other schools the release names. 14 members | thepacwest.com 2018/6/25 |
| 2018-19, 2019-20 | PacWest Academic | no data found | Unresolved. The 2020/8/27 Biola story is about D2 ADA awards, not the PacWest GPA ranking | - |
| 2020-21 | PacWest Academic | no data found | **WRONG: 4th, 3.45 GPA** (Dominican 3.623, Point Loma 3.52, Azusa Pacific 3.48, Biola 3.45, Chaminade 3.40) | https://thepacwest.com/news/2021/7/15/academics-dominican-wins-2021-pacwest-academic-achievement-award.aspx |
| 2021-22 | PacWest Academic | no data found | **Partly recoverable: top 5 (4th or 5th).** "Azusa Pacific and Biola round out the top-5" after Dominican 3.505, Point Loma 3.43 and Chaminade 3.42. The Biola GPA is not given | https://thepacwest.com/news/2022/6/29/general-dominican-wins-11th-pacwest-academic-achievement-award.aspx |
| 2022-23 | PacWest Academic | no data found | Correct as unresolved (no ranking in the release) | thepacwest.com 2023/6/21 |
| 2023-24 | PacWest Academic | 4th, 3.448 | **Correct** (Point Loma 3.52, Dominican 3.493, Chaminade 3.47) | thepacwest.com 2024/7/1; Biola 2024/7/3 |
| 2024-25 | PacWest Academic | 3rd, 3.51 | **Correct** (Point Loma and Dominican tied 1st at 3.52) | thepacwest.com 2025/7/22 |
| 2025-26 | PacWest Academic | did not place | **Mislabeled:** 6th or lower (only the top 5 were published) | thepacwest.com 2026/7/14 |

## Status attacks

**"Not eligible" for NCAA DII 2016-17 to 2018-19: holds.**
- Biola is absent from all three final DII PDFs.
- NACDA's DII points come only from NCAA championship finishes, and provisional members cannot enter NCAA championships.
- Control cases in the same PDFs point the same way:
  - Oklahoma Baptist was provisional in 2016-17 and became active on Sept. 1, 2017. It is absent in 2016-17, then 50th in 2017-18 and 39th in 2018-19.
  - Westminster (Utah) was provisional from 2015-16 to 2017-18 and became active in June 2018. It is absent in 2016-17 and 2017-18, then 179th in 2018-19.
- So NACDA did not score provisional members in any of these years.
- Caveat: the membership dates for those two schools come from search-result summaries of NCAA and school releases, not from reading the releases directly.
- Also note that in 2016-17 Biola was an active NAIA member and was scored there (18th), so the DII row for that year adds little.

**No DII final in 2019-20 and 2020-21: confirmed.** The NACDA archive index reads "2019-20/2020-21 No Standings due to COVID-19" for both DII and DIII. The only 2019-20 DII document is the Dec. 19, 2019 fall standings. Note: NACDA did publish DI and NAIA standings for 2020-21, so "COVID year" does not mean "no Cup anywhere". Only DII and DIII had none.

**"2nd ties best-ever GSAC finish": consistent, and now better supported.**
- Biola finished 2nd in 2011-12, 2015-16 and 2016-17.
- Azusa Pacific won every year from 1994-95 to 2011-12, and Westmont won from 2012-13 to 2016-17.
- So Biola never won, and the story's claim that 2nd is the best finish is consistent with everything found.

**Is the conference score column the same metric every year?** No; see defect 4. Every athletic row is an average of points per sport, but the point scales differ: GSAC used three different formulas between 2011-12 and 2016-17, and PacWest uses a larger scale. The academic rows are GPA.

## Recovered data

### NAIA Directors' Cup 1998-99 to 2005-06 (all from official NACDA final standings)

| Season | Finish | Points | Schools scored | Source |
|---|---|---|---|---|
| 1998-99 | T-28th (with California Baptist) | 180 | 234 (per release; PDF revised "As of 4/26/2001") | https://web.archive.org/web/20030213033338/http://graphics.fansonly.com:80/confs/nacda/graphics/9899NFinal.PDF |
| 1999-2000 | 18th | 349.5 | 234 | https://web.archive.org/web/20030109060823/http://graphics.fansonly.com:80/confs/nacda/graphics/9900NFinal.PDF |
| 2000-01 | 20th | 328.5 | 239 | https://web.archive.org/web/20010819025347/http://graphics.fansonly.com:80/confs/nacda/graphics/0001NAIAFinal.PDF |
| 2001-02 | 80th | 165 | 245 | https://web.archive.org/web/20020702180317/http://graphics.fansonly.com:80/confs/nacda/graphics/0102NAIAFinalStandings.PDF |
| 2002-03 | 43rd | 293 | 246 per release (244 rows) | https://web.archive.org/web/20031116212306/http://graphics.fansonly.com:80/confs/nacda/graphics/0203NAIAFinalStandings.pdf |
| 2003-04 | 19th | 420 | 236 | https://nacda.com/documents/2018/8/3/7222__directorscup__NAIAFinalStandings.pdf (linked from the 2004/6/11 release) |
| 2004-05 | 39th | 339 | unknown (top 100 printed) | https://nacda.com/documents/2018/8/3/6627__directorscup__NFinalStand.pdf (linked from the 2005/6/15 release) |
| 2005-06 | 60th | 259.5 | unknown (top 100 printed) | https://nacda.com/documents/2018/8/3/5997__directorscup__0506NFinalStand.pdf (linked from the 2006/6/19 release) |

None of these finishes is tied except 1998-99; I checked the neighboring rows in every PDF.

These results match Biola's own milestone counts exactly:
- **Top-20 finishes:** 1999-2000 (18th), 2000-01 (20th) and 2003-04 (19th) make three before 2008-09, and all three are worse than 16th. That matches the 2010 story: 2009-10 was the "fifth Top-20 finish" and 16th in 2008-09 was the "previous best-ever". Through 2016-17 there are 10 top-20 finishes, which matches the 2017 story's "10th top-20".
- **Top-50 finishes:** 1997-98, 1998-99, 1999-2000, 2000-01, 2002-03, 2003-04, 2004-05, 2006-07 and 2007-08, plus all nine seasons from 2008-09 to 2016-17, make 18. That matches the 2017 story's "18th top-50".
- The GSAC 2001-02 news page ("4 of top 15": Azusa Pacific, Westmont, Point Loma and Cal Baptist) also agrees with Biola's 80th.

Interim standings found along the way (interim only, not finals):
- 1998-99 after winter: T-19th, 140 pts (http://nacda.com:80/sears/current/naia/winter/naia-98winter02.html, Wayback capture 19991023).
- 1999-2000 after fall: T-45th, 70 pts.
- 2000-01 after fall: T-79th, 50 pts.

### GSAC All-Sports Award

- **2011-12: 2nd of 10, average 7.81.** Source: https://web.archive.org/web/20121026151436/http://gsacsports.org/f/All_Sports_Award.php
- **2015-16: 2nd of 9, 113 points / 14 sports = 8.07.** Source: https://web.archive.org/web/20160706204501/http://www.gsacsports.org/f/GSAC_All_Sports_Award_presented_by_Dukes.php
- **1994-95 to 2011-12: Azusa Pacific won all 18 years.** Primary GSAC statement: https://web.archive.org/web/20130718201836/http://www.gsacsports.org/f/GSAC_All_Sports_Award_presented_by_Dukes.php
- **Interim:** Biola led after the fall in 2012-13 (7.20) and in 2013-14 (7.3), and was 2nd after the fall in 2016-17 (8.20).

### PacWest Academic Achievement Award

- **2020-21: 4th, 3.45.** Source: https://thepacwest.com/news/2021/7/15/academics-dominican-wins-2021-pacwest-academic-achievement-award.aspx
- **2021-22: top 5 (4th or 5th), GPA not given.** Source: https://thepacwest.com/news/2022/6/29/general-dominican-wins-11th-pacwest-academic-achievement-award.aspx

## Still open

- GSAC All-Sports standings for 1994-95 to 2010-11. No conference page for these years exists on Wayback, and the GSAC Year in Review pages do not include the award.
- PacWest Academic rank for 2017-18, 2018-19, 2019-20 and 2022-23.
- Final GSAC 2016-17 standings, to settle 7.82 versus 7.86.
- NCCAA Presidential Award finals for 2017-18 and 2018-19. This audit did not pursue them further.
