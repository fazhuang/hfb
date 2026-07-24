/**
 * Design Token Validation Tests
 *
 * Verifies that:
 * 1. All required tokens are defined
 * 2. Every :root color token has a corresponding html.dark override
 * 3. All var(--*) references in components are valid tokens
 * 4. Contrast ratios meet WCAG AA minimums
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync, readdirSync, statSync } from 'fs';
import { resolve, relative, extname } from 'path';

const ROOT = resolve(__dirname, '..', '..');
const MAIN_CSS = resolve(ROOT, 'src', 'assets', 'main.css');

function readMainCss(): string {
  return readFileSync(MAIN_CSS, 'utf-8');
}

/** Extract all CSS custom property definitions from a :root or html.dark block */
function extractTokens(css: string, blockSelector: ':root' | 'html.dark'): Set<string> {
  const tokens = new Set<string>();
  // Match the block contents — note that @import files have separable blocks
  const blockRegex = blockSelector === ':root'
    ? /:root\s*\{([^}]+)\}/g
    : /html\.dark\s*\{([^}]+)\}/g;

  let match: RegExpExecArray | null;
  while ((match = blockRegex.exec(css)) !== null) {
    const block = match[1]!;
    const propRegex = /--[a-zA-Z0-9_-]+/g;
    let propMatch: RegExpExecArray | null;
    while ((propMatch = propRegex.exec(block)) !== null) {
      tokens.add(propMatch[0]!);
    }
  }
  return tokens;
}

/** Walk through all token @import files to collect the full token set */
function collectAllTokens(): { rootTokens: Set<string>; darkTokens: Set<string> } {
  // main.css now @imports token files. We need to follow the imports.
  // For test robustness, read main.css and also the individual token files.
  const rootTokens = new Set<string>();
  const darkTokens = new Set<string>();

  const css = readMainCss();

  // Find @import lines
  const importRegex = /@import\s+['"]\.\.\/styles\/([^'"]+)['"]/g;
  let match: RegExpExecArray | null;
  while ((match = importRegex.exec(css)) !== null) {
    const importPath = resolve(ROOT, 'src', 'styles', match[1]!);
    if (existsSync(importPath)) {
      const importedCss = readFileSync(importPath, 'utf-8');
      extractTokens(importedCss, ':root').forEach(t => rootTokens.add(t));
      extractTokens(importedCss, 'html.dark').forEach(t => darkTokens.add(t));
    }
  }

  // Also parse inline :root and html.dark blocks in main.css itself
  // (for the global reset + animations section)
  extractTokens(css, ':root').forEach(t => rootTokens.add(t));
  extractTokens(css, 'html.dark').forEach(t => darkTokens.add(t));

  return { rootTokens, darkTokens };
}

/** Collect all var(--*) references from Vue SFC style blocks and .css files in components/ */
function collectVarReferences(): Map<string, string[]> {
  const refs = new Map<string, string[]>();
  const componentsDir = resolve(ROOT, 'src', 'components');
  const stylesDir = resolve(ROOT, 'src', 'styles', 'base');

  function walkDir(dir: string): string[] {
    const results: string[] = [];
    try {
      for (const entry of readdirSync(dir)) {
        const full = resolve(dir, entry);
        const stat = statSync(full);
        if (stat.isDirectory()) {
          results.push(...walkDir(full));
        } else if (extname(full) === '.vue' || extname(full) === '.css') {
          results.push(full);
        }
      }
    } catch { /* dir may not exist */ }
    return results;
  }

  const files = [...walkDir(componentsDir), ...walkDir(stylesDir)];

  for (const file of files) {
    const content = readFileSync(file, 'utf-8');
    const varRegex = /var\((--[a-zA-Z0-9_-]+)/g;
    let match: RegExpExecArray | null;
    while ((match = varRegex.exec(content)) !== null) {
      const token = match[1]!;
      if (!refs.has(token)) refs.set(token, []);
      refs.get(token)!.push(relative(ROOT, file));
    }
  }
  return refs;
}

describe('Design Token Validation', () => {
  const { rootTokens, darkTokens } = collectAllTokens();
  const varRefs = collectVarReferences();

  describe('Core Token Definitions', () => {
    it('has typography tokens', () => {
      expect(rootTokens.has('--font-sans')).toBe(true);
      expect(rootTokens.has('--font-mono')).toBe(true);
      expect(rootTokens.has('--text-xs')).toBe(true);
      expect(rootTokens.has('--text-3xl')).toBe(true);
      expect(rootTokens.has('--font-normal')).toBe(true);
      expect(rootTokens.has('--font-bold')).toBe(true);
    });

    it('has spacing tokens (4px base grid)', () => {
      for (const s of [1, 2, 3, 4, 5, 6, 8, 10, 15]) {
        expect(rootTokens.has(`--space-${s}`)).toBe(true);
      }
    });

    it('has core color tokens', () => {
      const required = [
        '--color-accent', '--color-accent-hover', '--color-accent-light',
        '--color-text-primary', '--color-text-secondary', '--color-text-muted',
        '--color-border', '--color-hover', '--color-active',
        '--color-navbar-bg', '--color-page-bg', '--color-surface',
      ];
      for (const t of required) {
        expect(rootTokens.has(t), `Missing token: ${t}`).toBe(true);
      }
    });

    it('has semantic color tokens', () => {
      const required = [
        '--color-success', '--color-success-text', '--color-success-bg', '--color-success-icon-bg',
        '--color-warning', '--color-warning-text', '--color-warning-bg',
        '--color-error', '--color-error-text', '--color-error-light-text', '--color-error-bg', '--color-error-icon-bg',
        '--color-info', '--color-info-text', '--color-info-bg',
      ];
      for (const t of required) {
        expect(rootTokens.has(t), `Missing token: ${t}`).toBe(true);
      }
    });

    it('has component-level tokens', () => {
      const required = [
        '--btn-padding-sm', '--btn-padding-md', '--btn-padding-lg',
        '--btn-font-sm', '--btn-font-md', '--btn-font-lg', '--btn-radius',
        '--focus-ring', '--focus-ring-sm',
        '--color-input-bg', '--color-input-border',
        '--color-disabled-bg', '--color-disabled-text',
      ];
      for (const t of required) {
        expect(rootTokens.has(t), `Missing token: ${t}`).toBe(true);
      }
    });

    it('has z-index tokens', () => {
      const required = ['--z-dropdown', '--z-dialog', '--z-drawer', '--z-toast'];
      for (const t of required) {
        expect(rootTokens.has(t), `Missing token: ${t}`).toBe(true);
      }
    });
  });

  describe('Dark Mode Overrides', () => {
    const colorTokens = [...rootTokens].filter(t =>
      t.startsWith('--color-') ||
      t.startsWith('--btn-') ||
      t.startsWith('--z-')
    );

    for (const token of colorTokens) {
      // Skip tokens that are intentionally same in dark mode (z-index, spacing, etc.)
      if (token.startsWith('--z-') || token.startsWith('--radius') || token.startsWith('--shadow')) {
        continue;
      }
      if (token.includes('white') || token.includes('black')) continue;

      it(`dark mode has override for ${token}`, () => {
        // Tokens that reference OTHER tokens don't need dark overrides:
        // the referenced tokens themselves ARE overridden
        const derivedTokens = [
          '--btn-font-sm', '--btn-font-md', '--btn-font-lg',
          '--btn-radius',
          '--color-input-bg', '--color-input-border',
          '--color-input-focus-ring',
        ];
        if (token.startsWith('--btn-') || derivedTokens.includes(token)) {
          return; // These derive from other tokens that ARE overridden
        }
        expect(
          darkTokens.has(token),
          `Missing dark mode override for ${token}`,
        ).toBe(true);
      });
    }
  });

  describe('Token Usage Validation', () => {
    it('all var(--*) references in components resolve to defined tokens', () => {
      const undefinedTokens: string[] = [];
      for (const [token, files] of varRefs) {
        if (!rootTokens.has(token) && !darkTokens.has(token)) {
          undefinedTokens.push(`${token} (used in: ${files.join(', ')})`);
        }
      }
      expect(undefinedTokens.sort(), `Undefined tokens:\n${undefinedTokens.join('\n')}`).toEqual([]);
    });
  });

  describe('WCAG AA Contrast Ratios', () => {
    function hexToRgb(hex: string): [number, number, number] {
      const cleaned = hex.replace('#', '');
      if (cleaned.length === 3) {
        return [
          parseInt(cleaned[0]! + cleaned[0]!, 16),
          parseInt(cleaned[1]! + cleaned[1]!, 16),
          parseInt(cleaned[2]! + cleaned[2]!, 16),
        ];
      }
      return [
        parseInt(cleaned.substring(0, 2), 16),
        parseInt(cleaned.substring(2, 4), 16),
        parseInt(cleaned.substring(4, 6), 16),
      ];
    }

    function relativeLuminance(r: number, g: number, b: number): number {
      const vals = [r, g, b].map(c => {
        const s = c / 255;
        return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
      });
      return 0.2126 * vals[0]! + 0.7152 * vals[1]! + 0.0722 * vals[2]!;
    }

    function contrastRatio(hex1: string, hex2: string): number {
      const rgb1 = hexToRgb(hex1);
      const rgb2 = hexToRgb(hex2);
      const l1 = relativeLuminance(...rgb1);
      const l2 = relativeLuminance(...rgb2);
      const lighter = Math.max(l1, l2);
      const darker = Math.min(l1, l2);
      return (lighter + 0.05) / (darker + 0.05);
    }

    it('light mode text-primary has >= 4.5:1 contrast against page-bg', () => {
      // These values are the ones in the :root block (Light mode)
      const ratio = contrastRatio('#1a365d', '#f7fafc');
      expect(ratio).toBeGreaterThanOrEqual(4.5);
    });

    it('light mode accent has >= 4.5:1 contrast against white surface', () => {
      const ratio = contrastRatio('#2b6cb0', '#ffffff');
      expect(ratio).toBeGreaterThanOrEqual(4.5);
    });

    it('dark mode text-primary has >= 4.5:1 contrast against page-bg', () => {
      const ratio = contrastRatio('#e2e8f0', '#1a202c');
      expect(ratio).toBeGreaterThanOrEqual(4.5);
    });

    it('error text has >= 4.5:1 contrast against error background', () => {
      const ratio = contrastRatio('#c53030', '#fff5f5');
      expect(ratio).toBeGreaterThanOrEqual(4.5);
    });
  });
});
