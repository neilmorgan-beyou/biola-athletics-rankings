#!/usr/bin/env node
/* brand-check: Biola Athletics brand guard for every Eagle Shift build.
 *
 * Neil Morgan (brand owner), 2026-10-24. Every app, page, email and print
 * piece leads with the Biola Script and stays on the approved palette. This
 * script catches the regressions agents have made before, so they fail fast
 * instead of shipping:
 *   - the typographic lockups (Eagles Athletics, Biola Eagles, sport
 *     typographic) and the Eagles Script + Athletics lockup, by file name or
 *     alias AND by the exact bytes of an embedded or copied image (sha256);
 *   - navy and other dark blues, near-black UI ink, and cool greys;
 *   - the retired tagline "Faith You Can See".  // brand-check: allow the checker's own pattern list
 * The canonical copy is perch/brand/brand-check.mjs (rules: perch/brand/
 * BRAND-RULES.md). Each repo carries a verbatim copy at scripts/brand-check.mjs,
 * kept in step by perch/scripts/sync-brand-kit.sh; ~/.claude/brand/ holds the
 * copy the Claude Code hook runs on a developer's Mac.
 *
 * Usage:
 *   node scripts/brand-check.mjs              changed lines vs origin/main
 *   node scripts/brand-check.mjs --all        every tracked file
 *   node scripts/brand-check.mjs FILE...      whole files
 *   node scripts/brand-check.mjs --hook       Claude Code PostToolUse hook (JSON on stdin)
 * A line containing "brand-check: allow" is skipped (say why on that line).
 * A repo can list paths in .brandcheck.json: "skip" (never checked, e.g. a
 * download library of every official mark) and "history" (applied
 * migrations and other append-only records: skipped by --all, but new lines
 * in a change are still checked). {"skip": ["prefix/"], "history": ["prefix/"]}
 * The rules themselves: BRAND RULES in ~/.claude/CLAUDE.md and each repo's
 * CLAUDE.md. Palette: Red #C8102E, Blue #489FDF, Warm Gray #5E514D, Light
 * Gray #D0D3D4, white, light tints; black sparingly; green/amber for status. */
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { execSync } from "node:child_process";

const BANNED_SHA256 = new Set(["0812b0176c46dda727dcc677688dd4ac0345bfdee77fd81e3d45e4be083029de","0a006307a480d463eff7ed3aa8c594e77efc7c8b15a79fed118cde658171d2ff","0b557ef64a452de45c3b32e2963675c01af871390db6b11cd09da441ff3ec9df","0c7875057f0947ce4b6396ed746b656736b4d5a36147858015ecdd9645e6fbf0","1288cbc39e6f8cc26d1a7b37ff994ed6f35294403f2a017f916470d2562fc606","16a84ca39029d8c33fa775185dba6ba2d91b05e1343675e22f28d755ff97f8c5","22afd2d4991db80604c2fdf658c43d57b02e34cdeeb197fe42be21a16e86bc62","24eb843faf7638b3813d9ffd43de6c43065eae3fa3c9520850ce069c4ce6154b","305f8fbc0bc08c695b3518be21d8d170d255ba94abebece2837128e006716134","35e46f2ede5435a3f931eed128a87cf20c1edb4aa6d4f7a8ec5dda6e72814374","37e3789cfa94b80e21b8401a1d0c25e4468f19a41c345c507c0c9d62fa120e0e","3a8e6d501c1c10061b90fabab976b2101ab4e245de2dfa8df282b68624dab2cd","494bde4eb6433b1033564df4a7c82a328286da122fe80fc0c339e0c90211d3ec","4bad807bca0088c08d499c4a64607c79c7f3c7f4a42fdc9aa6eb07804c80517b","566ecc03569d88795f2394a75f3efe7b9d04229cc519f13505bece0b15f55738","59796b575a1df964b8294f49d61c17be7f82a569d583df49900698b6a9ee79e5","5a7095bea5360e2c59280b79fa2eefb32c79c204b92ed5c6206961089dedb309","5cef1501481519753c02cc8c1bf651a8a7c55745e4d2c736a8e2346133498975","6088d247bf48b261946d182a5e7b5f952fe7ef1781670a8db719e66d430f6304","68ef75a86a274d8384e25bc56a4654a18abd5fe050c05c52df083eff489c6de4","6aeb16c87665c48966e7a1835a2aefccf808e1f9e9f6ed80fe60be8643bcc5b0","6fd402028b24aa816f29a6fcbbde041328b46aa1d42ecf55cabf1314186356c2","79c516b606bcc37a2855d3a261697458489200b20d42e936da388f13b7a3d76f","7b8e7c51adb8e0d53ebef0b422abf0d517b3d4abec6d4a75de57fcd6a41d985b","823e64fe2b13ff0c527a1f2716fc20ee90d352a74ea79e78c93463991b8f83cf","84c387212759302d80f701e85f989492015b0612932b8ba624d2d6a2c89afd1d","9ce95c8e17a8f80b292c20d9e731944f1e27bf7ef2c14c8abafb98c1ea4c7280","9edac3d63c6b73beb7de7cbe0e80f9a19c6a7d8ba04e69540547c28d4ac25a79","a069d1fe8d015e247a44c48b48282cf07b9d2b3d04fe878aea90248fd0112e81","a26e1fe3ca5aa119fe8a7a5ea2892dbe70d2f548b686e16ab98eff525f1d7f75","a848a4e41d2860abf0c8e6630afc46d285cb7ceee19933bd43bb970559dcbd1d","b9487eefaab00d8911fee13b20a7e85d084402434c0ce1b58cbea107c63fab7d","ccf1339347891ee2f3956b0a706d4367d17664b8e80a40b772edae8f8e485fc7","cf23fd8ab94536672cf5304ca889aebf4c09cd04695909be33d1de250c4e257f","d1f7db05ea3020656f31a8029ca4631dac8288bca58b8c81a43297eb7f2ebae8","d48a2ba778efdd150fc836e8468c8a7b3d25dbefb56accca78c79cf162537555","d600df86045e3c51e2b77f858f0575e022f336894a41c20092824613f355a7e3","d7517b2be9c2803d895c850a51b246eda4b19e3040bb981009572f2667008631","e541056b3a7807bc772dace0ba81e421f901ee9a9bdfa366f3175ea40983e9e7","e9cfa3f45fb9bfd59fd622405438af71f3f10cb4f89040bd4c16f9d49ee702d0","eca02452a8aa65bc4ce44a0fcc0253454a4770692bb8745e5fad1071a440145a","ef51f808a1bea2708d1bc413c5298c4c7c5ec239b7f939061ea738c2d75db315","f48bccc3a9da877d32d43a188f23ecc29ee5d081a8be39c3c0f400af6411e792","fc0053a92d35d14b690fe52dcfc7370ba7d9e5a3c2941d0bc63d81f6afa87a1a"]);
const BANNED_NAME = /Typographic_(Horizontal|Centered|Stacked|Vertical)|eagles-athletics-2c|biola-eagles-2c|Eagles_Script(\+|%2B| \+ )Athletics/i;  // brand-check: allow the checker's own pattern list
const TAGLINE = /faith you can see/i;  // brand-check: allow the checker's own pattern list
const BANNED_HEX = new Set(["14527B","1D6FA5","2C7CB8","1F6FB2","2F7CB8","25689B","2A6FA8","1B5C8A","1E66A0","164C76","256EA5","2565A3","181818","1A1614","1A1A1A","17161A","0B0B0C","0F172A","1E293B","2A2320","1F1A19","1F1A18","2C2B31","4A403D","4A403C","64748B","75757C","3A3A40","4A4A50","B9B7B4","8F8D8A"]);
const PALETTE = new Set(["C8102E","489FDF","5E514D","D0D3D4","FFFFFF","000000","A50D26"]);
const TEXT_EXT = /\.(html?|css|scss|sass|less|styl|m?js|cjs|tsx?|jsx|svg|sql|py|gs|vue|svelte|astro|json|jsonc|hbs|njk|ejs|liquid|mjml|xml)$/i;
// Never checked: generated output and third-party code.
const SKIP_DIR = /(^|\/)(node_modules|dist|\.git|three-brain-out|vendor|coverage|\.next|\.wrangler)\//;
// Also skipped by --all only (they legitimately quote old values or hold
// records); a CHANGE to them is still checked, with allow markers for
// assertions about old values.
const ALL_ONLY_SKIP = /(^|\/)(build|tests?|__tests__|fixtures|data)\/|[._-]test\.[a-z]+$/;
// Warm Gray (#5E514D or a warm/ink token, or a Tailwind bg-ink class) used as
// a background, fill or bgcolor.
const WARM_FILL = /(background(-color)?\s*:[^;"'}]*(#5E514D|var\(--(es-)?(warm|ink|ink-2|muted)\)))|(bgcolor\s*=\s*["']?#5E514D)|(\bfill\s*[:=]\s*["']?#5E514D)|(\bbg-ink-(50|60|70|80|90)\b)/i;
// An exception must say why: "brand-check: allow <reason>".
const ALLOW = /brand-check: allow\s+[A-Za-z]{2,}/;

const lum = (r, g, b) => { const f = x => { x /= 255; return x <= .03928 ? x / 12.92 : ((x + .055) / 1.055) ** 2.4; }; return .2126 * f(r) + .7152 * f(g) + .0722 * f(b); };
function hexProblem(h) {
  h = h.toUpperCase(); if (h.length === 3) h = h.split("").map(c => c + c).join("");
  if (PALETTE.has(h)) return null;
  if (BANNED_HEX.has(h)) return "off-palette (navy, near-black or cool grey)";
  const r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16);
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b), L = lum(r, g, b);
  if (mn >= 0xC8) return null;                                  // a light tint
  if (mx <= 0x48) return "near-black UI ink (use Warm Gray #5E514D; black only sparingly for body copy)";
  if (b > r + 30 && b >= g && L < lum(0x48, 0x9F, 0xDF)) return "navy / dark blue (use Biola Red or Warm Gray for text, Biola Blue for fills)";
  if (mx - mn < 20 && b > r && mx < 0xC8) return "cool grey (use Warm Gray #5E514D or Light Gray #D0D3D4)";
  return null;
}
function checkText(file, lines) {
  const out = [];
  // Custom properties defined as Warm Gray in this text, so a fill through
  // var(--dark) or var(--hero) is caught like a literal one.
  const warmVars = new Set();
  for (const [, l] of lines) for (const m of l.matchAll(/--([\w-]+)\s*:\s*#5E514D\b/gi)) warmVars.add(m[1].toLowerCase());
  for (const [n, line] of lines) {
    if (ALLOW.test(line)) continue;
    if (BANNED_NAME.test(line)) out.push([file, n, "banned lockup (typographic or Eagles Script + Athletics): lead with the Biola Script"]);
    if (TAGLINE.test(line)) out.push([file, n, 'retired tagline: use "Faith. Formation. Fierce."']);
    for (const m of line.matchAll(/data:image\/(?:svg\+xml|png);base64,([A-Za-z0-9+/=]{200,})/g)) {
      const sha = crypto.createHash("sha256").update(Buffer.from(m[1], "base64")).digest("hex");
      if (BANNED_SHA256.has(sha)) out.push([file, n, "embedded image is a banned lockup (matched by sha256)"]);
    }
    // Warm Gray is for copy, not design (Neil 2026-10-25): no warm-grey hero,
    // band, button, badge or tile. Red leads, blue supports, greys sit behind.
    const viaVar = [...line.matchAll(/(?:background(?:-color)?|fill)\s*:[^;"'}]*var\(--([\w-]+)\)/gi)].some(m => warmVars.has(m[1].toLowerCase()));
    if (WARM_FILL.test(line) || viaVar) out.push([file, n, "Warm Gray used as a fill: it is for copy only. Use Biola Red (white text) or Biola Blue for heroes, bands, buttons and badges; Light Gray or white for quiet fills"]);
    const scan = line.replace(/data:image\/[^"')\s]+/g, "");
    for (const m of scan.matchAll(/(?<![\w&])#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-fA-F\w])/g)) {
      // A three-digit "#107" is usually an issue number: only count it as a
      // colour in a styling context.
      if (m[1].length === 3 && !/(color|background|fill|stroke|border|outline|shadow|style|:\s*#)/i.test(scan)) continue;
      const p = hexProblem(m[1]); if (p) out.push([file, n, `#${m[1]} ${p}`]);
    }
  }
  return out;
}
// A data URI's base64 may start on the next line or wrap across lines, which
// the line-by-line pass cannot see. This pass reads the whole text.
function checkDataUris(file, text) {
  const out = [];
  for (const m of text.matchAll(/data:image\/(?:svg\+xml|png);base64,([A-Za-z0-9+/=\s\\]{200,})/g)) {
    const b64 = m[1].replace(/[\s\\]/g, "");
    const sha = crypto.createHash("sha256").update(Buffer.from(b64, "base64")).digest("hex");
    if (!BANNED_SHA256.has(sha)) continue;
    const line = text.slice(0, m.index).split("\n").length;
    const endLine = line + (m[0].match(/\n/g) || []).length;
    const lineText = text.split("\n")[line - 1] || "";
    if (ALLOW.test(lineText)) continue;
    out.push([file, line, "embedded image is a banned lockup (matched by sha256)", endLine]);
  }
  return out;
}
function checkBinary(file) {
  if (!/\.(png|svg|jpe?g|webp)$/i.test(file) || !fs.existsSync(file)) return [];
  const sha = crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
  return BANNED_SHA256.has(sha) ? [[file, 0, "this image file is a banned lockup (sha256)"]] : [];
}
function skipped(rel, cfg) { return SKIP_DIR.test(rel) || (cfg.skip || []).some(p => typeof p === "string" && p.length > 0 && rel.startsWith(p)); }
const inHistory = (rel, cfg) => (cfg.history || []).some(p => typeof p === "string" && p.length > 0 && rel.startsWith(p));
// --config FILE reads the config from elsewhere: CI passes main's copy, so a
// pull request cannot loosen the check that judges it.
function loadCfg(root) {
  const i = process.argv.indexOf("--config");
  const f = i > 0 ? process.argv[i + 1] : path.join(root, ".brandcheck.json");
  try { return JSON.parse(fs.readFileSync(f, "utf8")); } catch { return {}; }
}
const sh = (c, cwd) => execSync(c, { cwd, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"], maxBuffer: 1 << 28 });
function wholeFile(f) { const t = fs.readFileSync(f, "utf8"); return t.split("\n").map((l, i) => [i + 1, l]); }

function report(found, label) {
  found = [...new Map(found.map(x => [x.join("|"), x])).values()];
  if (!found.length) { if (label) console.log(`brand-check: clean (${label})`); return 0; }
  for (const [f, n, why] of found) console.error(`${f}${n ? ":" + n : ""}  ${why}`);
  console.error(`\nbrand-check: ${found.length} problem(s). Rules: BRAND RULES in CLAUDE.md. Mark a deliberate exception with "brand-check: allow <reason>" on the line.`);
  return 1;
}

const args = process.argv.slice(2).filter((a, i, all) => a !== "--config" && all[i - 1] !== "--config");
if (args[0] === "--hook") {
  let input = ""; try { input = fs.readFileSync(0, "utf8"); } catch { /* not available here; keep the default */ }
  let j = {}; try { j = JSON.parse(input); } catch { process.exit(0); }
  const ti = j.tool_input || {}; const file = ti.file_path || ti.notebook_path || "";
  if (!file || /\.md$/i.test(file) || !(TEXT_EXT.test(file) || /\.(png|svg)$/i.test(file)) || SKIP_DIR.test(file) || /\/\.claude\/brand\//.test(file)) process.exit(0);
  const chunks = [ti.content, ti.new_string, ...((ti.edits || []).map(e => e.new_string))].filter(s => typeof s === "string");
  const lines = chunks.join("\n").split("\n").map((l, i) => [i + 1, l]);
  const found = [...checkText(file + " (new text)", lines), ...checkDataUris(file + " (new text)", chunks.join("\n")).map(x => x.slice(0, 3)), ...checkBinary(file)];
  if (found.length) { report(found); process.exit(2); }
  process.exit(0);
}
let root; try { root = sh("git rev-parse --show-toplevel", process.cwd()).trim(); } catch { root = process.cwd(); }
const cfg = loadCfg(root);
const found = [];
if (args[0] === "--all") {
  const files = sh("git ls-files", root).split("\n").filter(Boolean);
  for (const rel of files) {
    if (skipped(rel, cfg) || ALL_ONLY_SKIP.test(rel) || inHistory(rel, cfg)) continue;
    const abs = path.join(root, rel);
    found.push(...checkBinary(abs).map(x => [rel, x[1], x[2]]));
    if (TEXT_EXT.test(rel) && fs.existsSync(abs) && fs.statSync(abs).size < 40e6) { found.push(...checkText(rel, wholeFile(abs))); found.push(...checkDataUris(rel, fs.readFileSync(abs, "utf8")).map(x => x.slice(0, 3))); }
  }
  process.exit(report(found, "all tracked files"));
} else if (args.length) {
  for (const f of args) { found.push(...checkBinary(f)); if (TEXT_EXT.test(f)) { found.push(...checkText(f, wholeFile(f))); found.push(...checkDataUris(f, fs.readFileSync(f, "utf8")).map(x => x.slice(0, 3))); } }
  process.exit(report(found, args.length + " file(s)"));
} else {
  let base = "origin/main"; try { base = sh("git merge-base origin/main HEAD", root).trim(); } catch { /* not available here; keep the default */ }
  const diff = sh(`git -c core.quotePath=false diff -U0 --no-color --no-renames ${base} --`, root);
  let file = null, n = 0, expectHeader = false; const byFile = new Map();
  for (const l of diff.split("\n")) {
    // A "+++ " line is a file header only straight after its "--- " line; an
    // added line that happens to start with "++ " is content. Paths with a
    // space end in a tab, and odd paths come quoted.
    if (l.startsWith("--- ")) { expectHeader = true; continue; }
    if (expectHeader && l.startsWith("+++ ")) {
      expectHeader = false;
      let p = l.slice(4).replace(/\t$/, "");
      if (p.startsWith('"') && p.endsWith('"')) p = JSON.parse(p);
      file = p === "/dev/null" ? null : p.replace(/^b\//, "");
      continue;
    }
    expectHeader = false;
    const h = l.match(/^@@ -\S+ \+(\d+)/); if (h) { n = +h[1]; continue; }
    if (!file || skipped(file, cfg)) continue;
    if (l.startsWith("+")) { if (!byFile.has(file)) byFile.set(file, []); byFile.get(file).push([n, l.slice(1)]); n++; }
  }
  for (const [f, lines] of byFile) if (TEXT_EXT.test(f)) {
    found.push(...checkText(f, lines));
    const abs = path.join(root, f);
    if (fs.existsSync(abs)) { const changedLines = new Set(lines.map(x => x[0])); found.push(...checkDataUris(f, fs.readFileSync(abs, "utf8")).filter(x => [...changedLines].some(c => c >= x[1] && c <= x[3])).map(x => x.slice(0, 3))); }
  }
  const changed = sh(`git diff --name-only ${base} --`, root).split("\n").filter(Boolean);
  const untracked = sh("git ls-files --others --exclude-standard", root).split("\n").filter(Boolean);
  for (const rel of [...changed, ...untracked]) if (!skipped(rel, cfg)) found.push(...checkBinary(path.join(root, rel)).map(x => [rel, x[1], x[2]]));
  for (const rel of untracked) if (!skipped(rel, cfg) && TEXT_EXT.test(rel)) found.push(...checkText(rel, wholeFile(path.join(root, rel))));
  process.exit(report(found, "changes vs origin/main"));
}
