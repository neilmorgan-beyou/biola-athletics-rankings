#!/bin/sh
# Weekly refresh (run by the scheduled routine after it has added any new polls to polls/*.json).
# 1. re-scrape recent seasons' games, 2. join games to polls, 3. rebuild page parts, 4. validate.
# Exit status is validate.py's: 0 = safe to commit and publish, 1 = stop and report.
set -e
cd "$(dirname "$0")"
Y=$(date +%Y); M=$(date +%m)
# School year that started most recently (July cutover), minus one so winter/spring seasons in progress are covered.
if [ "$M" -ge 7 ]; then FROM=$((Y - 1)); else FROM=$((Y - 2)); fi
(cd games && RECENT_FROM=$FROM python3 scrape_all_games.py)
# Published NCAA DII regional rankings (NPI) from NCAA.com; prints NEEDS-MANUAL lines, never stops the run.
python3 ncaa_regional.py || echo "ncaa_regional.py failed; report it"
python3 join_games_polls.py
python3 build_rankings_page.py data .
set +e
python3 validate.py --baseline "${BASELINE:-HEAD}"
