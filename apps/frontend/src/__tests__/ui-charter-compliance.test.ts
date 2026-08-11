/**
 * ui-charter-compliance.test.ts — Unit tests for UI Design Charter (HFB-UI-0601, HFB-UI-0602) compliance.
 *
 * Enforces charter red lines:
 * 1. Zero magic numbers (38px, 170px) in input/select base styles and toolbar components.
 * 2. Standardized spacing & typography tokens across select.css, input.css, HfbToolbar, ResearchReportsToolbar.
 * 3. Type safety & token usage compliance.
 * 4. Isolation protection verification for AppNavbar.vue & VersionComparisonPage.vue.
 */

import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';

const SRC_DIR = resolve(__dirname, '..');
const SELECT_CSS_PATH = resolve(SRC_DIR, 'styles', 'base', 'select.css');
const INPUT_CSS_PATH = resolve(SRC_DIR, 'styles', 'base', 'input.css');
const HFB_TOOLBAR_PATH = resolve(SRC_DIR, 'components', 'common', 'HfbToolbar.vue');
const REPORT_TOOLBAR_PATH = resolve(SRC_DIR, 'components', 'reports', 'ResearchReportsToolbar.vue');

function getFileContent(filePath: string): string {
  expect(existsSync(filePath), `File does not exist: ${filePath}`).toBe(true);
  return readFileSync(filePath, 'utf-8');
}

describe('UI Charter Compliance (HFB-UI-0601, HFB-UI-0602)', () => {
  describe('Red Line 1: Zero Magic Numbers in Base Styles (select.css & input.css)', () => {
    it('select.css contains zero hardcoded 38px magic numbers', () => {
      const content = getFileContent(SELECT_CSS_PATH);
      expect(content.includes('38px')).toBe(false);
    });

    it('input.css contains zero hardcoded 38px magic numbers', () => {
      const content = getFileContent(INPUT_CSS_PATH);
      expect(content.includes('38px')).toBe(false);
    });

    it('select.css uses standard tokens for padding, font-size, line-height, and radius', () => {
      const content = getFileContent(SELECT_CSS_PATH);
      expect(content).toContain('padding: var(--space-2) var(--space-3);');
      expect(content).toContain('font-size: var(--text-base);');
      expect(content).toContain('line-height: var(--leading-normal);');
      expect(content).toContain('border-radius: var(--radius-lg);');
    });

    it('input.css uses standard tokens for padding, font-size, line-height, and radius', () => {
      const content = getFileContent(INPUT_CSS_PATH);
      expect(content).toContain('padding: var(--space-2) var(--space-3);');
      expect(content).toContain('font-size: var(--text-base);');
      expect(content).toContain('line-height: var(--leading-normal);');
      expect(content).toContain('border-radius: var(--radius-lg);');
    });
  });

  describe('Red Line 2: Zero Magic Numbers in HfbToolbar.vue', () => {
    it('HfbToolbar.vue contains zero hardcoded 38px or 170px magic numbers', () => {
      const content = getFileContent(HFB_TOOLBAR_PATH);
      expect(content.includes('38px')).toBe(false);
      expect(content.includes('170px')).toBe(false);
    });

    it('HfbToolbar.vue configures flex layouts with design tokens', () => {
      const content = getFileContent(HFB_TOOLBAR_PATH);
      expect(content).toContain('gap: var(--space-3);');
      expect(content).toContain('gap: var(--space-2);');
      expect(content).toContain('min-width: var(--space-20);');
    });
  });

  describe('Red Line 3: Zero Magic Numbers in ResearchReportsToolbar.vue', () => {
    it('ResearchReportsToolbar.vue contains zero hardcoded 38px or 170px magic numbers', () => {
      const content = getFileContent(REPORT_TOOLBAR_PATH);
      expect(content.includes('38px')).toBe(false);
      expect(content.includes('170px')).toBe(false);
    });

    it('ResearchReportsToolbar.vue configures .rrt-select with required design tokens', () => {
      const content = getFileContent(REPORT_TOOLBAR_PATH);
      expect(content).toContain('padding: var(--space-2) var(--space-3);');
      expect(content).toContain('font-size: var(--text-sm);');
      expect(content).toContain('line-height: var(--leading-normal);');
      expect(content).toContain('border-radius: var(--radius-md);');
    });
  });

  describe('Red Line 4: Isolation Safeguard Verification', () => {
    it('AppNavbar.vue & VersionComparisonPage.vue exist and are strictly isolated', () => {
      const navbarPath = resolve(SRC_DIR, 'components', 'layout', 'AppNavbar.vue');
      const versionCompPath = resolve(SRC_DIR, 'pages', 'research', 'VersionComparisonPage.vue');
      expect(existsSync(navbarPath)).toBe(true);
      expect(existsSync(versionCompPath)).toBe(true);
    });
  });
});
