# Biola Athletics Rankings History: project brief for Claude

Read `ROUTINE.md` first. `refresh.sh` rebuilds the page parts; `build_rankings_page.py` writes the SIDEARM sport-file body (pasted by hand), the local preview and `docs/rankings-data.json` (served by GitHub Pages, which carries the live sort styles). `validate.py` must pass before publishing.


## Brand rules

Source of truth: **Neil Morgan, brand owner** (rules of 2026-10-24; the full
text is "BRAND RULES for every build" in Neil's `~/.claude/CLAUDE.md`).

- **Lead mark by background.** On red: Biola Script Solid REV. On blue: Biola
  Script Sticker RGB. On white: the Biola Script + Eagles Solid 1C RGB lockup.
  Any other background: ask Neil. Files come from `Claude Brand Skill/Identity
  Assets/` byte-identical; never recolour, redraw or composite one.
- **Banned as a header, sign-in, page-head or email-head mark:** every
  typographic lockup (Eagles Athletics, Biola Eagles, sport typographic), the
  Eagles Script + Athletics lockup, and the B monogram as the lead. Retired
  marks (BU, the old eagle icon, the all-caps BIOLA wordmark) are never used.
- **Palette:** Biola Red #C8102E, Biola Blue #489FDF, Warm Gray #5E514D, Light
  Gray #D0D3D4, white and light tints of those; red hover #A50D26. Black only
  sparingly for body copy. Green and amber only to mean a state. No navy or dark
  blues, no near-black UI, no cool greys. Never text (or a white glyph) on
  solid Biola Blue: use a blue wash with a blue edge, or red with white text.
  Links are red. A dark-on-purpose surface uses Warm Gray as the dark.
- **Emails:** every email, app mail included, opens with the official 2C
  outlined Eagle mascot (150 x 75) on a white band, then the email's own red
  band. Inks: Warm Gray text, red links, Light Gray lines, a #F3F4F4 wash for
  footer bands.
- **App tiles and tab icons:** a Biola Red tile, a Biola Blue bar along the
  bottom, an all-white glyph.
- **Tagline:** "Faith. Formation. Fierce.", never the retired one.
- **Enforced:** `node scripts/brand-check.mjs` (a verbatim copy of Neil's
  checker) must pass before every PR; `--all` checks every tracked file. The
  only way to keep an exception is `brand-check: allow <reason>` on that line.
