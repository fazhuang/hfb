#!/usr/bin/env node
/**
 * HFB Design System Compliance Check
 *
 * Scans managed styles for hardcoded Design System values.
 *
 * Blocking (hard error — enforced scope only):
 *   - Colors (hex, rgb, rgba, hsl, hsla) — must use var(--color-*)
 *   - var() fallback hardcoded colors
 *   - Box-shadows — must use var(--shadow-*)
 *   - Z-index numeric values — must use var(--z-*)
 *
 * Advisory (reported, non-blocking for base layer):
 *   - Spacing px values not matching tokens
 *   - Border-radius px values not matching tokens
 *   - Transition durations not using var(--transition-*)
 *
 * Token files (styles/tokens/*.css) are exempt — they define the values.
 *
 * Usage: node apps/frontend/scripts/check-design-compliance.mjs
 * Exit code: non-zero on blocking violations.
 */

import { readFileSync, readdirSync, statSync, existsSync } from 'fs';
import { resolve, relative, extname, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '..');
const SRC = resolve(ROOT, 'src');

const RED = '\x1b[31m';
const YELLOW = '\x1b[33m';
const GREEN = '\x1b[32m';
const BOLD = '\x1b[1m';
const RESET = '\x1b[0m';

// ─── Known token values for advisory spacing/radius checking ───────────
const SPACE_TOKENS = [4, 8, 12, 16, 20, 24, 28, 32, 40, 60];
const RADIUS_TOKENS = [4, 6, 8, 10, 12];

// ─── Walk ──────────────────────────────────────────────────────────────

function walkDir(dir, extensions = ['.css', '.vue']) {
  const results = [];
  try {
    for (const entry of readdirSync(dir)) {
      const full = resolve(dir, entry);
      let st;
      try { st = statSync(full); } catch { continue; }
      if (st.isDirectory()) {
        if (entry === 'node_modules' || entry === 'dist' || entry === 'coverage') continue;
        results.push(...walkDir(full, extensions));
      } else if (extensions.includes(extname(full))) {
        results.push(full);
      }
    }
  } catch { /* dir may not exist */ }
  return results;
}

function isTokenFile(filepath) {
  return filepath.includes('/styles/tokens/');
}

// ─── Violation collectors ──────────────────────────────────────────────

/**
 * @param {string} source
 * @param {number} lineOffset
 * @returns {Array<{line: number, value: string, rule: string}>}
 */
function collectViolations(source, lineOffset = 0) {
  const v = [];
  const lines = source.split('\n');

  for (let i = 0; i < lines.length; i++) {
    const raw = lines[i];
    const code = raw.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*/g, '');
    const lineNum = i + 1 + lineOffset;

    // ── Colors: hex (not inside var()) ──
    const hexRe = /(?<![-_a-zA-Z])#[0-9a-fA-F]{3,8}\b/g;
    let m;
    // First, strip var() contents to avoid false positives inside var()
    let stripped = code.replace(/var\([^)]+\)/g, '');
    hexRe.lastIndex = 0;
    while ((m = hexRe.exec(stripped)) !== null) {
      v.push({ line: lineNum, value: m[0], rule: 'color:hex' });
    }

    // ── rgb/rgba (standalone, not inside var()) ──
    const rgbRe = /rgba?\s*\(\s*\d+/gi;
    rgbRe.lastIndex = 0;
    while ((m = rgbRe.exec(stripped)) !== null) {
      v.push({ line: lineNum, value: m[0], rule: 'color:rgb/rgba' });
    }

    // ── hsl/hsla ──
    const hslRe = /hsla?\s*\(\s*\d+/gi;
    hslRe.lastIndex = 0;
    while ((m = hslRe.exec(stripped)) !== null) {
      v.push({ line: lineNum, value: m[0], rule: 'color:hsl/hsla' });
    }

    // ── var() fallback colors ──
    const fbRe = /var\([^)]+,\s*(#[0-9a-fA-F]{3,8}|rgba?\s*\([^)]+\)|hsla?\s*\([^)]+\))\s*\)/gi;
    fbRe.lastIndex = 0;
    while ((m = fbRe.exec(code)) !== null) {
      v.push({ line: lineNum, value: m[1], rule: 'color:var-fallback' });
    }

    // ── Shadow: box-shadow without var() ──
    if (/box-shadow\s*:\s*(?!(none|inherit|unset|initial|var\())/i.test(code)) {
      const shadowMatch = code.match(/box-shadow\s*:\s*([^;]+)/i);
      if (shadowMatch && !shadowMatch[1].includes('var(')) {
        v.push({ line: lineNum, value: shadowMatch[1].trim(), rule: 'shadow:bare' });
      }
    }

    // ── Z-index: bare numeric ──
    const ziRe = /z-index\s*:\s*(-?\d+)/g;
    ziRe.lastIndex = 0;
    while ((m = ziRe.exec(code)) !== null) {
      if (!code.includes('var(--z-')) {
        v.push({ line: lineNum, value: m[0].trim(), rule: 'z-index:bare' });
        break; // one per line is enough
      }
    }

    // ── Spacing: bare px not in token set (advisory only) ──
    const spRe = /(?:margin|padding|gap|inset)\s*:\s*([\d\s]+)px/g;
    spRe.lastIndex = 0;
    while ((m = spRe.exec(code)) !== null) {
      const vals = m[1].trim().split(/\s+/).map(Number);
      if (vals.some(n => !SPACE_TOKENS.includes(n)) || vals.some(n => n <= 1)) {
        v.push({ line: lineNum, value: m[0].trim(), rule: 'spacing:bare-px' });
        break;
      }
    }

    // ── Radius: bare px not in token set (advisory only) ──
    const radRe = /border-radius\s*:\s*([\d]+)px/g;
    radRe.lastIndex = 0;
    while ((m = radRe.exec(code)) !== null) {
      const n = Number(m[1]);
      if (!RADIUS_TOKENS.includes(n) && n !== 9999 && n !== 50) {
        v.push({ line: lineNum, value: m[0].trim(), rule: 'radius:bare-px' });
        break;
      }
    }

    // ── Transition: bare duration (advisory only) ──
    if (/transition\s*:/.test(code) && !code.includes('var(--transition-')) {
      const durMatch = code.match(/transition\s*:\s*([^;]+)/i);
      if (durMatch && /\d+\.?\d*s/.test(durMatch[1])) {
        // Accept if it references a var for the duration
        if (!durMatch[1].includes('var(--transition')) {
          v.push({ line: lineNum, value: durMatch[1].trim().slice(0, 60), rule: 'transition:bare-duration' });
        }
      }
    }
  }
  return v;
}

// ─── Main ──────────────────────────────────────────────────────────────

function main() {
  const blockingViolations = [];
  const advisoryViolations = [];
  const legacyViolations = [];

  // ── Enforced scope: styles/base/ ────────────────────────────────────
  const baseDir = resolve(SRC, 'styles', 'base');
  if (existsSync(baseDir)) {
    const baseFiles = walkDir(baseDir, ['.css']);
    for (const file of baseFiles) {
      if (isTokenFile(file)) continue;
      const content = readFileSync(file, 'utf-8');
      const violations = collectViolations(content);

      for (const v of violations) {
        if (v.rule.startsWith('color:') || v.rule.startsWith('shadow:') || v.rule.startsWith('z-index:')) {
          blockingViolations.push({ ...v, file: relative(ROOT, file) });
        } else {
          advisoryViolations.push({ ...v, file: relative(ROOT, file) });
        }
      }
    }
  }

  // ── Components (legacy debt, not blocking) ──────────────────────────
  const componentsDir = resolve(SRC, 'components');
  if (existsSync(componentsDir)) {
    const compFiles = walkDir(componentsDir, ['.vue', '.css']);
    for (const file of compFiles) {
      if (isTokenFile(file)) continue;
      const content = readFileSync(file, 'utf-8');

      if (file.endsWith('.vue')) {
        // Extract <style> blocks
        const styleRe = /<style[^>]*>([\s\S]*?)<\/style>/gi;
        let sm;
        while ((sm = styleRe.exec(content)) !== null) {
          const beforeBlock = content.substring(0, sm.index);
          const blockStartLine = beforeBlock.split('\n').length - 1;
          const violations = collectViolations(sm[1], blockStartLine);
          for (const v of violations) {
            legacyViolations.push({ ...v, file: relative(ROOT, file) });
          }
        }
      } else {
        const violations = collectViolations(content);
        for (const v of violations) {
          legacyViolations.push({ ...v, file: relative(ROOT, file) });
        }
      }
    }
  }

  // ── Pages/views (legacy debt, not blocking) ─────────────────────────
  const pagesDir = resolve(SRC, 'pages');
  if (existsSync(pagesDir)) {
    for (const file of walkDir(pagesDir, ['.vue'])) {
      if (isTokenFile(file)) continue;
      const content = readFileSync(file, 'utf-8');
      const styleRe = /<style[^>]*>([\s\S]*?)<\/style>/gi;
      let sm;
      while ((sm = styleRe.exec(content)) !== null) {
        const beforeBlock = content.substring(0, sm.index);
        const blockStartLine = beforeBlock.split('\n').length - 1;
        const violations = collectViolations(sm[1], blockStartLine);
        for (const v of violations) {
          legacyViolations.push({ ...v, file: relative(ROOT, file) });
        }
      }
    }
  }

  // ── Report ───────────────────────────────────────────────────────────
  console.log(`\n${BOLD}HFB Design System Compliance Check${RESET}\n`);

  if (blockingViolations.length > 0) {
    console.log(`${RED}${BOLD}BLOCKING VIOLATIONS (${blockingViolations.length}):${RESET}\n  Colors, shadows, and z-index must use var(--*) tokens.\n`);
    const byFile = {};
    for (const v of blockingViolations) {
      if (!byFile[v.file]) byFile[v.file] = [];
      byFile[v.file].push(v);
    }
    for (const [file, violations] of Object.entries(byFile)) {
      console.log(`  ${BOLD}${file}${RESET}:`);
      for (const v of violations) {
        console.log(`    ${RED}L${v.line}:${RESET} ${v.rule} → "${v.value}"`);
      }
    }
    console.log('');
  } else {
    console.log(`${GREEN}${BOLD}✓ Blocking scope (styles/base/): colors, shadows, z-index all tokenized${RESET}\n`);
  }

  if (advisoryViolations.length > 0) {
    console.log(`${YELLOW}Advisory (${advisoryViolations.length} spacing/radius/transition in base CSS — not blocking):${RESET}`);
    const byFile = {};
    for (const v of advisoryViolations) {
      if (!byFile[v.file]) byFile[v.file] = [];
      byFile[v.file].push(v);
    }
    for (const [file, violations] of Object.entries(byFile)) {
      console.log(`  ${file}: ${violations.length} items`);
    }
    console.log('');
  }

  if (legacyViolations.length > 0) {
    console.log(`${YELLOW}Legacy debt (${legacyViolations.length} violations in components/pages — not blocking):${RESET}`);
    const byFile = {};
    for (const v of legacyViolations) {
      if (!byFile[v.file]) byFile[v.file] = [];
      byFile[v.file].push(v);
    }
    for (const [file, violations] of Object.entries(byFile)) {
      console.log(`  ${file}: ${violations.length} violations`);
    }
    console.log('');
  }

  if (blockingViolations.length > 0) {
    console.log(`${RED}${BOLD}✖ ${blockingViolations.length} blocking violation(s) — FAIL${RESET}\n`);
    process.exit(1);
  }

  console.log(`${GREEN}${BOLD}✓ Design System compliance check PASSED${RESET}\n`);
  process.exit(0);
}

main();
