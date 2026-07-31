/**
 * ESLint rule: no-hardcoded-colors
 *
 * Detects standalone hex, rgb, rgba, hsl, hsla color literals in Vue SFC
 * <style> blocks AND standalone .css files. Requires that colors use
 * `var(--*)` design tokens instead.
 *
 * Whitelist (only these files may contain raw color values):
 *   - styles/tokens/*.css     (token definition layer)
 *
 * Allowed values in managed styles:
 *   - transparent, currentColor, inherit
 *   - url(#...) (SVG references)
 *   - rgba(var(--*) …) — transforming tokens
 *
 * Also detects var(--token, #fallback) fallback hardcoded colors.
 *
 * Level: error
 */

'use strict';

// Regex patterns for hardcoded color values
const HEX_COLOR = /(?<!var\([^)]{0,200})(?<![-_a-zA-Z])(#[0-9a-fA-F]{3,8})\b/g;
const RGB_COLOR = /(?<!var\()rgb\([^)]+\)/gi;
const RGBA_COLOR = /rgba\([^)]+\)/gi;
const HSL_COLOR = /(?<!var\()hsl\([^)]+\)/gi;
const HSLA_COLOR = /hsla\([^)]+\)/gi;

// Detect hardcoded fallback in var(--token, #FALLBACK)
const VAR_FALLBACK_COLOR =
  /var\([^)]+,\s*(#[0-9a-fA-F]{3,8}|rgba?\s*\([^)]+\)|hsla?\s*\([^)]+\))\s*\)/gi;

// Allowed exceptions
const ALLOWED_PATTERNS = [
  /rgba\(var\(--/, // rgba(var(--*) ...) — token transform
  /rgba\(\d+,\s*\d+,\s*\d+,\s*0\)/, // transparent rgba
];

/**
 * @param {string} source
 * @returns {Array<{line: number, column: number, value: string, kind: string}>}
 */
function findStandaloneColors(source) {
  const lines = source.split('\n');
  const results = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const lineNum = i + 1;

    // Skip CSS comments
    const codeOnly = line.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*/g, '');

    // Strip var() contents to avoid false positives from token references
    const stripped = codeOnly.replace(/var\([^)]+\)/g, '');
    // Strip url() contents to avoid SVG references
    const sanitized = stripped.replace(/url\([^)]+\)/g, '');

    // Detect fallback hardcoded colors inside var()
    VAR_FALLBACK_COLOR.lastIndex = 0;
    let fm;
    while ((fm = VAR_FALLBACK_COLOR.exec(codeOnly)) !== null) {
      results.push({ line: lineNum, column: fm.index + 1, value: fm[1], kind: 'var-fallback' });
    }

    // Check hex colors (only standalone, not inside var())
    HEX_COLOR.lastIndex = 0;
    let match;
    while ((match = HEX_COLOR.exec(sanitized)) !== null) {
      results.push({ line: lineNum, column: match.index + 1, value: match[1], kind: 'hex' });
    }

    // Check rgb/rgba (standalone, not inside var())
    RGBA_COLOR.lastIndex = 0;
    while ((match = RGBA_COLOR.exec(sanitized)) !== null) {
      const isAllowed = ALLOWED_PATTERNS.some((p) => p.test(match[0]));
      if (!isAllowed) {
        results.push({ line: lineNum, column: match.index + 1, value: match[0], kind: 'rgba' });
      }
    }

    RGB_COLOR.lastIndex = 0;
    while ((match = RGB_COLOR.exec(sanitized)) !== null) {
      const isAllowed = ALLOWED_PATTERNS.some((p) => p.test(match[0]));
      if (!isAllowed) {
        results.push({ line: lineNum, column: match.index + 1, value: match[0], kind: 'rgb' });
      }
    }

    HSL_COLOR.lastIndex = 0;
    while ((match = HSL_COLOR.exec(sanitized)) !== null) {
      results.push({ line: lineNum, column: match.index + 1, value: match[0], kind: 'hsl' });
    }

    HSLA_COLOR.lastIndex = 0;
    while ((match = HSLA_COLOR.exec(sanitized)) !== null) {
      results.push({ line: lineNum, column: match.index + 1, value: match[0], kind: 'hsla' });
    }
  }

  return results;
}

/** @type {import('eslint').Rule.RuleModule} */
module.exports = {
  meta: {
    type: 'problem',
    docs: {
      description: 'Disallow hardcoded color values — use design tokens (var(--*))',
      category: 'Best Practices',
      recommended: true,
    },
    schema: [],
    messages: {
      noHardcodedColor:
        'Hardcoded color "{{value}}" found. Use a design token (var(--color-*)) instead. ' +
        'If you need a new color, define it in styles/tokens/ first.',
      noVarFallback:
        'Hardcoded fallback color "{{value}}" in var() found. Remove the fallback or use a defined token. ' +
        'Fallbacks defeat the purpose of token governance.',
    },
  },

  create(context) {
    const filename = context.filename || context.getFilename?.() || '';

    // Skip node_modules, dist, coverage
    if (
      filename.includes('node_modules') ||
      filename.includes('/dist/') ||
      filename.includes('/coverage/')
    ) {
      return {};
    }

    // WHITELIST: only token definition files may contain raw colors
    if (filename.includes('/styles/tokens/')) {
      return {};
    }

    // Only check .vue and .css files
    if (!filename.endsWith('.vue') && !filename.endsWith('.css')) {
      return {};
    }

    return {
      Program(node) {
        const source = context.getSourceCode().getText();

        if (filename.endsWith('.vue')) {
          // Extract <style> blocks from Vue SFC
          const styleRegex = /<style[^>]*>([\s\S]*?)<\/style>/gi;
          let blockMatch;

          while ((blockMatch = styleRegex.exec(source)) !== null) {
            const styleContent = blockMatch[1];
            const beforeBlock = source.substring(0, blockMatch.index);
            const blockStartLine = beforeBlock.split('\n').length;

            const colors = findStandaloneColors(styleContent);
            for (const c of colors) {
              context.report({
                loc: {
                  line: blockStartLine + c.line - 1,
                  column: c.column,
                },
                messageId: c.kind === 'var-fallback' ? 'noVarFallback' : 'noHardcodedColor',
                data: { value: c.value },
              });
            }
          }
        } else {
          // Standalone .css file
          const colors = findStandaloneColors(source);
          for (const c of colors) {
            context.report({
              loc: {
                line: c.line,
                column: c.column,
              },
              messageId: c.kind === 'var-fallback' ? 'noVarFallback' : 'noHardcodedColor',
              data: { value: c.value },
            });
          }
        }
      },
    };
  },
};
