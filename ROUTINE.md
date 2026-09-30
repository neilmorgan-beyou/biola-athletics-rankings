# Weekly refresh routine (Tuesday mornings)

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

2. **Add each newly released poll** to the right `polls/<sport>.json` exactly per the spec: every
   ranked team, `team_raw` exactly as printed, `receiving_votes`, `release_date` (the date the poll was
   published; if a source gives only a week label, use the date printed in the source and say so in
   `notes`), `source_url`, `confidence: "primary"`, a unique `poll_id` in the file's existing style.
   Append only; never edit or delete an existing poll. After adding, re-open each source and check
   the Biola line (and 3 other random teams) against your entry.

3. **Sports without a poll archive** (cross country, track & field, swimming & diving): check the
   current-season national/regional polls (USTFCCCA, CSCAA) for Biola. For each new appearance, append
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

7. **Email Neil** (neil.morgan@biola.edu) using the Gmail connector ONLY when there is something to
   report: the run could not complete (for example a source or athletics.biola.edu was unreachable),
   a failed validation, an uncertain item you left out, a possible alias, or a notable new ranking for
   Biola (Biola newly ranked or moving up 5+ spots). Subject starts with
   "[Rankings routine]". Keep it short: what changed, what needs him, links to the commit or report.
   Include `validate-report.md` content on failure. Do not email on quiet weeks.
