# Daily refresh routine (mornings)

Runs every morning so each poll lands the day after it is released (AVCA Mon, United Soccer Coaches Tue,
USTFCCCA regional Tue / national Wed, CWPA Wed). Most days nothing changes and the run ends quietly.

You are refreshing the data behind the Biola Athletics "Rankings History" page
(https://athletics.biola.edu/sports/2026/9/30/rankings-history.aspx). The page loads
`docs/rankings-data.json` from GitHub Pages, so committing an updated file to `main` updates the
live page. **Never edit anything outside this repo. Never touch Sidearm.**

Read `SPEC-poll-archive.md` first. The standing rules:
- A ranking counts only if read from the published poll document itself. Never use rank numbers
  from Biola's schedules, box scores or tournament seeds. Never infer or guess a poll or a date.
- Past seasons are frozen. Only polls for seasons currently in progress (or just finished) are added.
- If anything is uncertain, leave it out and report it; do not publish a guess.

## Steps

1. **Find what's new.** For each sport with a poll archive in `polls/`, look at the latest
   `release_date` per division for the current season. Sports in season (by month):
   Aug-Dec: volleyball, men's/women's soccer, men's water polo;
   Nov-Mar: men's/women's basketball; Jan-May: women's water polo;
   Feb-Jun: baseball, softball, men's/women's tennis.
   Official sources, current division only (Biola is NCAA Division II since 2019):
   - Volleyball: AVCA NCAA DII Coaches Top 25 (avca.org)
   - Soccer: United Soccer Coaches NCAA DII national Top 25 (unitedsoccercoaches.org)
   - Basketball: NABC DII Coaches Poll (men), WBCA DII Coaches Poll (women)
   - Baseball: NCBWA NCAA DII poll; Softball: NFCA NCAA DII Top 25 (nfca.org)
   - Tennis: ITA NCAA DII team rankings (wearecollegetennis.com)
   - Water polo: CWPA / ACWPC national varsity poll (collegiatewaterpolo.org)
   Also NAIA polls for the same sports ONLY if a current-season NAIA series already exists in the file.
   **If a source can't be read** (blocked, empty page, script-rendered), never assume no new poll. On the
   first run after that poll's release day (see "When the polls come out" in sid-article-generation's
   recap-context/README.md; USTFCCCA skips some weeks) when the poll is still missing, list
   the sport and the exact poll URL (for AVCA: `https://www.avca.org/polls-awards/polls/?_season=<year>&_divisions=division-ii-women&_weeks=week-<n>`)
   in the email to Neil under "Needs a manual read (paste these links into Claude Code)".

2. **Add each newly released poll** to the right `polls/<sport>.json` exactly per the spec: every
   ranked team, `team_raw` exactly as printed, `receiving_votes`, `release_date` (the date the poll was
   published; if a source gives only a week label, use the date printed in the source and say so in
   `notes`), `source_url`, `confidence: "primary"`, a unique `poll_id` in the file's existing style.
   Append only; never edit or delete an existing poll. After adding, re-open each source and check
   the Biola line (and 3 other random teams) against your entry.

3. **Sports without a poll archive** (cross country, track & field, swimming & diving): check the
   current-season national/regional polls (USTFCCCA, CSCAA) for Biola.
   - **Swimming (CSCAA):** the NCAA Division II polls are a published Google Sheet, one tab per poll
     (tab names like "Preseason 2026", "October 2026"). Read the tab list from
     https://docs.google.com/spreadsheets/d/e/2PACX-1vTVK5j20kOB-fbcWrBDmnIg84VPoD3s0KhNtCIrdM4yxhNWSwT33CKXwK9y7BAXvoN1TLwC-KvL1wXY/pubhtml
     and each tab as CSV via `.../pub?gid=<gid>&single=true&output=csv` (men left, women right;
     "Also receiving votes" rows list points in parentheses). Confirm the sheet's header says
     "Division II" before using it. Source URL for rows: https://cscaa.org/top-25/
   - **Cross country / track (USTFCCCA):** ustfccca.org blocks automated reads (Cloudflare 403),
     but https://www.ustfccca.org/feed lists new polls. Do not guess ranks. If the feed shows a new
     "NCAA DII ... Cross Country (or Track & Field) National Coaches' Poll" or "Regional Rankings"
     post since the last row in data/current-season.json / data/xc-track.json, list its link(s) in the
     email to Neil under "Needs a manual read (paste these links into Claude Code)". For each new appearance, append
   a row to `data/current-season.json` (create it as `{"rows": []}` if missing) with the same fields as
   the rows in `data/xc-track.json` (sport, season, era, poll, scope, region, week, date, rank, points,
   record_at_time, source_url, confidence "primary", notes). Skip if the row already exists.

4. **Run** `sh refresh.sh`. It re-scrapes recent games from athletics.biola.edu, joins games to
   polls, rebuilds the page data and runs `validate.py`.

5. **Review the join report** `polls/join-report.md` for the current season: any "Near misses" or
   "Loose matches" involving an opponent Biola played this season. If a near miss is clearly the same
   school (e.g. "Cal State LA" vs "Cal State L.A."), add an entry to `polls/aliases.json` under that
   sport (Biola's schedule name -> the poll's name) and rerun step 4. If it is not clearly the same
   school, do NOT alias it; list it in the report.

6. **Publish or stop.**
   - If `validate.py` passed (exit 0) and files changed: commit all changes to `main` with a message
     listing the polls added and the new verified games, and push. GitHub Pages republishes within
     minutes.
   - If validation FAILED, or you skipped anything uncertain: do not push. Commit nothing to main.
   - If nothing changed (no new polls or games): do nothing.

7. **QUILL recap-context feed.** Run `python3 recap_context.py`, which writes
   `recap/<academic year>/biola-recap-context-<today>.json`. The second repository in this session,
   `sid-article-generation`, is Eddie's QUILL data repo (pull it first). Compare the new file's facts with
   the newest `recap-context/<academic year>/biola-recap-context-*.json` there, ignoring `generated_at`.
   - **Facts identical:** publish nothing.
   - **Facts changed, no file for today yet:** copy the new file there (same filename), commit ONLY that
     one new file to `main` and push.
   - **A file for today already exists there** (an earlier run or a fix today): do not overwrite it.
     Eddie allows an in-place correction only before any recap has used the file, which this routine
     cannot check, so email Neil what differs instead.
   Rules from Eddie (recap-context/README.md, which is the contract; if the output would break it, stop
   and email Neil instead of pushing):
   - never edit or delete an existing file there except the same-day correction above (done by Neil/Eddie);
   - before pushing, run `git show --stat HEAD` and confirm the commit lists exactly that one added file;
   - no head-to-head series facts until Eddie confirms PR #135 is merged (recap_context.py omits them);
   - poll positions use `category: "poll"` and carry a `poll` name (recap_context.py adds it). QUILL
     retires a poll position on its own when that poll's next release is due, so a missing poll never
     leaves a wrong rank in a recap; it only leaves that sport without a rank until the next file.
   - a poll QUILL has no schedule for (any poll other than AVCA DII women, United Soccer Coaches DII,
     CWPA men's varsity, USTFCCCA DII XC regional/national) gets no `poll` field; list it in the email
     to Neil the first time it appears so Eddie can add its schedule.
   Commit the generated `recap/` file to this repo too (only when it was published).

8. **Email Neil** (neil.morgan@biola.edu) using the Gmail connector ONLY when there is something to
   report: the run could not complete (for example a source or athletics.biola.edu was unreachable),
   new USTFCCCA polls that need a manual read,
   a failed validation, an uncertain item you left out, a possible alias, or a notable new ranking for
   Biola (Biola newly ranked or moving up 5+ spots). Subject starts with
   "[Rankings routine]". Keep it short: what changed, what needs him, links to the commit or report.
   Include `validate-report.md` content on failure. Do not email on quiet days, and do not repeat a manual-read request on later days.
