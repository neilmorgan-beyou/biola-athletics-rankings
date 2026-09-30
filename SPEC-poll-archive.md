# Poll archive + game join: shared spec (2026-09-29)

Neil's rule: an opponent's ranking counts ONLY if it is verified against the published poll
itself. Rank numbers printed on Biola's schedules are never used (postseason ones are often
tournament seeds). Every Biola game is joined to the poll IN EFFECT on game day.

## 1. Poll archive files: `polls/<sport-slug>.json`

One file per sport. Full polls, every ranked team, not just Biola.

```json
{
  "sport": "Women's Volleyball",
  "polls": [
    {
      "poll_id": "avca-dii-2016-w03",
      "poll": "AVCA NCAA DII Coaches Top 25",
      "division": "NCAA DII",          // NAIA | NCAA DII | NCAA DI | NCAA DIII | mixed (water polo)
      "season": "2016",                  // "2016-17" for winter sports
      "week": "Week 3",                  // Preseason | Week N | Final (post-season) ...
      "release_date": "2016-09-12",      // REQUIRED. Date the poll was published.
      "postseason_final": false,         // true for a poll released after the national tournament
      "size": 25,                        // how many numbered spots the poll has
      "complete": true,                  // false if some ranked teams could not be read
      "source_url": "https://...",       // the poll document you read (Wayback URL fine)
      "confidence": "primary",           // primary = the poll itself; secondary = a faithful reprint
      "teams": [
        {"rank": 1, "tied": false, "team_raw": "Concordia (Calif.)", "points": 1250}
      ],
      "receiving_votes": [{"team_raw": "Biola (Calif.)", "points": 12}]
    }
  ],
  "gaps": ["season/poll weeks you could not find, and why"],
  "sources_tried": ["..."]
}
```

Rules:
- Copy team names EXACTLY as printed (`team_raw`). Do not normalize; the join does that.
- One primary poll per division per sport (listed in each agent's brief). Do not mix polls.
- Never infer a poll you did not read. A missing week is a gap, not a guess.
- A Biola story is NOT a poll document; do not build poll tables from stories.
- Include EVERY week you can find, preseason through the postseason final.

## 2. Games file: `games/all-games.json` (every Biola game, every season)

```json
{"games": [{"game_id": "wvb-2016-09-10-1", "sport": "Women's Volleyball", "season": "2016",
  "date": "2016-09-10", "opponent_raw": "Azusa Pacific", "location": "Home|Away|Neutral",
  "result": "W|L|T", "score": "3-1", "event": "tournament/round text or null",
  "postseason": true, "exhibition": false, "source_url": "season schedule page"}]}
```
No rank fields at all.

## 3. Join (done by the page builder, not by research agents)

rank in effect = latest poll of the opponent's division with release_date <= game date, same season,
excluding postseason_final polls released after the game. Opponent names matched through
`polls/aliases.json` ({"<raw name>": "<canonical school>"}), unmatched names reported, never guessed.
