#!/usr/bin/env node
/**
 * HFB Design System Compliance Check
 *
 * Recursively scans apps/frontend/src/styles/base, components, pages,
 * views — all CSS and Vue <style> blocks.
 *
 * ONLY styles/tokens/** may contain raw color values.
 *
 * ALL categories are BLOCKING (any violation → non-zero exit):
 *   - hex / rgb / rgba / hsl / hsla colors
 *   - var() fallback hardcoded colors
 *   - bare box-shadow
 *   - bare z-index
 *   - bare spacing px (margin/padding/gap/inset)
 *   - bare border-radius px
 *   - bare transition/animation duration
 *
 * Token allowed-values are PARSED from token CSS.
 *
 * Baseline: check-design-compliance.baseline.json freezes pre-existing
 * violations so new work can enforce fail-closed.  Entries removed from
 * the baseline file become blocking again.
 *
 * Usage: node apps/frontend/scripts/check-design-compliance.mjs
 */

import { readFileSync, readdirSync, statSync, existsSync } from 'fs';
import { resolve, relative, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '..');
const SRC = resolve(ROOT, 'src');
const TOKENS_DIR = resolve(SRC, 'styles', 'tokens');
const BASELINE_PATH = resolve(__dirname, 'check-design-compliance.baseline.json');

const R = '\x1b[31m';
const G = '\x1b[32m';
const B = '\x1b[1m';
const X = '\x1b[0m';

// ─── Parse token values ─────────────────────────────────────────────────

function parseTokenValues() {
  const vals = { spacings: new Set(), radii: new Set() };
  const files = readdirSync(TOKENS_DIR).filter((f) => f.endsWith('.css'));
  for (const f of files) {
    const content = readFileSync(resolve(TOKENS_DIR, f), 'utf-8');
    for (const block of content.matchAll(/(?::root|html\.dark)\s*\{([^}]+)\}/g)) {
      for (const m of block[1].matchAll(/--space-[\w-]+\s*:\s*(\d+)px/g)) {
        vals.spacings.add(Number(m[1]));
      }
      for (const m of block[1].matchAll(/--radius-[\w-]+\s*:\s*(\d+)px/g)) {
        vals.radii.add(Number(m[1]));
      }
    }
  }
  return vals;
}

const TOKEN_VALUES = parseTokenValues();

// ─── Baseline ────────────────────────────────────────────────────────────

function loadBaseline() {
  if (!existsSync(BASELINE_PATH)) return [];
  try {
    const raw = readFileSync(BASELINE_PATH, 'utf-8');
    const data = JSON.parse(raw);
    const block = data.block || '?';
    const frozenAt = data.frozen_at || '?';
    return {
      block,
      frozenAt,
      entries: (data.exempt || []).map((e) => ({
        key: `${e.file}::${e.line}::${e.rule}`,
        ...e,
      })),
    };
  } catch {
    console.warn('Baseline file exists but is not valid JSON — ignoring.');
    return [];
  }
}

function applyBaseline(violations, baseline) {
  if (!baseline.entries?.length) return violations;
  const exemptKeys = new Set(baseline.entries.map((b) => b.key));
  const unexempt = [];
  for (const v of violations) {
    if (!exemptKeys.has(`${v.file}::${v.line}::${v.rule}`)) {
      unexempt.push(v);
    }
  }
  return unexempt;
}

// ─── Walk ───────────────────────────────────────────────────────────────

function walkDir(dir) {
  const results = [];
  try {
    for (const entry of readdirSync(dir)) {
      const full = resolve(dir, entry);
      let st;
      try {
        st = statSync(full);
      } catch {
        continue;
      }
      if (st.isDirectory()) {
        if (entry === 'node_modules' || entry === 'dist' || entry === 'coverage') continue;
        for (const f of walkDir(full)) results.push(f);
      } else if (full.endsWith('.css') || full.endsWith('.vue')) {
        results.push(full);
      }
    }
  } catch {}
  return results;
}

function isTokenFile(fp) {
  return fp.includes('/styles/tokens/');
}

// ─── Collect ────────────────────────────────────────────────────────────

function collectViolations(source, lineOffset) {
  lineOffset = lineOffset || 0;
  const v = [];
  const lines = source.split('\n');

  for (let i = 0; i < lines.length; i++) {
    const raw = lines[i];
    const code = raw.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*/g, '');
    const ln = i + 1 + lineOffset;
    const stripped = code.replace(/var\([^)]+\)/g, '').replace(/url\([^)]+\)/g, '');

    // hex
    for (const m of stripped.matchAll(/(?<![-_a-zA-Z])#[0-9a-fA-F]{3,8}\b/g)) {
      v.push({ line: ln, value: m[0], rule: 'color:hex' });
    }
    // rgb/rgba
    for (const m of stripped.matchAll(/rgba?\s*\(\s*\d+/gi)) {
      v.push({ line: ln, value: m[0].slice(0, 30), rule: 'color:rgb/rgba' });
    }
    // hsl/hsla
    for (const m of stripped.matchAll(/hsla?\s*\(\s*\d+/gi)) {
      v.push({ line: ln, value: m[0].slice(0, 30), rule: 'color:hsl/hsla' });
    }
    // var() fallback
    for (const m of code.matchAll(
      /var\([^)]+,\s*(#[0-9a-fA-F]{3,8}|rgba?\s*\([^)]+\)|hsla?\s*\([^)]+\))\s*\)/gi,
    )) {
      v.push({ line: ln, value: m[1], rule: 'color:var-fallback' });
    }
    // shadow
    const sh = code.match(/box-shadow\s*:\s*([^;]+)/i);
    if (sh && !sh[1].includes('var(--') && sh[1] !== 'none') {
      v.push({ line: ln, value: sh[1].trim().slice(0, 60), rule: 'shadow:bare' });
    }
    // z-index
    const zi = code.match(/z-index\s*:\s*(-?\d+)/);
    if (zi && !code.includes('var(--z-')) {
      v.push({ line: ln, value: zi[0].trim(), rule: 'z-index:bare' });
    }
    // spacing
    const sp = code.match(/(?:margin|padding|gap|inset)\s*:\s*([\d\s]+)px/);
    if (sp && !code.includes('var(--space-')) {
      v.push({ line: ln, value: sp[0].trim(), rule: 'spacing:bare-px' });
    }
    // radius
    const rd = code.match(/border-radius\s*:\s*(\d+)px/);
    if (rd && !code.includes('var(--radius-')) {
      const n = Number(rd[1]);
      if (n !== 50 && n !== 9999) {
        v.push({ line: ln, value: rd[0].trim(), rule: 'radius:bare-px' });
      }
    }
    // transition
    const tr = code.match(/transition\s*:\s*([^;]+)/i);
    if (tr && /\d+\.?\d*s/.test(tr[1]) && !tr[1].includes('var(--transition-')) {
      v.push({ line: ln, value: tr[1].trim().slice(0, 60), rule: 'transition:bare' });
    }
    // animation
    const an = code.match(/animation\s*:\s*([^;]+)/i);
    if (an && /\d+\.?\d*s/.test(an[1]) && !an[1].includes('var(--transition-')) {
      v.push({ line: ln, value: an[1].trim().slice(0, 60), rule: 'animation:bare' });
    }
  }
  return v;
}

// ─── Main ───────────────────────────────────────────────────────────────

const scanDirs = [
  resolve(SRC, 'styles', 'base'),
  resolve(SRC, 'components'),
  resolve(SRC, 'pages'),
  resolve(SRC, 'layouts'),
];
if (existsSync(resolve(SRC, 'views'))) scanDirs.push(resolve(SRC, 'views'));

const all = [];

for (const dir of scanDirs) {
  if (!existsSync(dir)) continue;
  for (const file of walkDir(dir)) {
    if (isTokenFile(file)) continue;
    const content = readFileSync(file, 'utf-8');
    const rel = relative(ROOT, file);

    if (file.endsWith('.vue')) {
      for (const sm of content.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/gi)) {
        const bl = content.substring(0, sm.index).split('\n').length - 1;
        for (const v of collectViolations(sm[1], bl)) all.push({ ...v, file: rel });
      }
    } else {
      for (const v of collectViolations(content)) all.push({ ...v, file: rel });
    }
  }
}

// ─── Apply baseline ─────────────────────────────────────────────────────

const baseline = loadBaseline();
if (baseline.entries?.length) {
  console.log(
    `\n${B}HFB Design System Compliance Check — baseline active (${baseline.entries.length} frozen from ${baseline.block} @ ${baseline.frozenAt})${X}\n`,
  );
}

const violations = applyBaseline(all, baseline);

// ─── Report ─────────────────────────────────────────────────────────────

console.log(
  `Scanned: ${scanDirs
    .filter((d) => existsSync(d))
    .map((d) => relative(ROOT, d))
    .join(', ')}`,
);
console.log(`Allowed spacings: [${[...TOKEN_VALUES.spacings].sort((a, b) => a - b).join(', ')}]`);
console.log(`Allowed radii: [${[...TOKEN_VALUES.radii].sort((a, b) => a - b).join(', ')}]`);

if (all.length - violations.length > 0) {
  console.log(
    `  ${B}${all.length - violations.length} exemption(s)${X} applied (frozen pre-existing)\n`,
  );
}

if (violations.length === 0) {
  console.log(`\n${G}${B}✓ Design System compliance check PASSED — 0 new violations${X}\n`);
  process.exit(0);
}

console.log(`\n${R}${B}BLOCKING VIOLATIONS (${violations.length}):${X}\n`);

const byFile = {};
for (const v of violations) {
  if (!byFile[v.file]) byFile[v.file] = [];
  byFile[v.file].push(v);
}
for (const [file, vs] of Object.entries(byFile).sort()) {
  console.log(`  ${B}${file}${X} (${vs.length}):`);
  for (const v of vs) console.log(`    ${R}L${v.line}:${X} ${v.rule} → "${v.value}"`);
}
console.log(`\n${R}${B}✖ ${violations.length} violation(s) — FAIL${X}\n`);
process.exit(1);
