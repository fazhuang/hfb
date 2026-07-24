/**
 * ESLint rule: no-hardcoded-colors
 *
 * Detects standalone hex, rgb, rgba, hsl, hsla color literals in Vue SFC
 * <style> blocks. Requires that colors use `var(--*)` design tokens instead.
 *
 * Allowed values:
 *   - transparent, currentColor, inherit
 *   - url(#...) (SVG references)
 *   - Values inside var(…) fallbacks (already covered by token usage)
 *   - rgba(var(--*) …) — transforming tokens
 *
 * Level: warn (escalate to error after migration)
 */

'use strict';

// Regex patterns for hardcoded color values
const HEX_COLOR = /(?<!var\([^)]{0,200})(?<![-_a-zA-Z])(#[0-9a-fA-F]{3,8})\b/g;
const RGB_COLOR = /(?<!var\()rgb\([^)]+\)/gi;
const RGBA_COLOR = /rgba\([^)]+\)/gi;
const HSL_COLOR = /(?<!var\()hsl\([^)]+\)/gi;
const HSLA_COLOR = /hsla\([^)]+\)/gi;

// Allowed exceptions
const ALLOWED_PATTERNS = [
  /rgba\(var\(--/,           // rgba(var(--*) ...) — token transform
  /rgba\(\d+,\s*\d+,\s*\d+,\s*0\)/,  // transparent rgba
];

/**
 * @param {string} source
 * @returns {{line: number, column: number, value: string}[]}
 */
function findStandaloneColors(source) {
  const lines = source.split('\n');
  const results = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const lineNum = i + 1;

    // Skip comments
    const codeOnly = line.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*/g, '');

    // Check hex colors (only standalone, not inside var())
    let match;
    HEX_COLOR.lastIndex = 0;
    while ((match = HEX_COLOR.exec(codeOnly)) !== null) {
      const value = match[1];
      // Skip #fff, #000 and other common short forms in special contexts
      if (value === '#fff' || value === '#FFF' || value === '#000' || value === '#000000') {
        // Still report — these should use tokens
      }
      results.push({ line: lineNum, column: match.index + 1, value });
    }

    // Check rgb/rgba (standalone, not inside var())
    RGBA_COLOR.lastIndex = 0;
    while ((match = RGBA_COLOR.exec(codeOnly)) !== null) {
      const isAllowed = ALLOWED_PATTERNS.some(p => p.test(match[0]));
      if (!isAllowed) {
        results.push({ line: lineNum, column: match.index + 1, value: match[0] });
      }
    }

    RGB_COLOR.lastIndex = 0;
    while ((match = RGB_COLOR.exec(codeOnly)) !== null) {
      results.push({ line: lineNum, column: match.index + 1, value: match[0] });
    }

    HSL_COLOR.lastIndex = 0;
    while ((match = HSL_COLOR.exec(codeOnly)) !== null) {
      results.push({ line: lineNum, column: match.index + 1, value: match[0] });
    }

    HSLA_COLOR.lastIndex = 0;
    while ((match = HSLA_COLOR.exec(codeOnly)) !== null) {
      results.push({ line: lineNum, column: match.index + 1, value: match[0] });
    }
  }

  return results;
}

/** @type {import('eslint').Rule.RuleModule} */
module.exports = {
  meta: {
    type: 'suggestion',
    docs: {
      description: 'Disallow hardcoded color values in Vue SFC style blocks',
      category: 'Best Practices',
      recommended: false,
    },
    schema: [],
    messages: {
      noHardcodedColor:
        'Hardcoded color "{{value}}" found. Use a design token (var(--color-*)) instead. ' +
        'Allowed exceptions: transparent, currentColor, inherit, var() references.',
    },
  },

  create(context) {
    // Only check .vue files — skip .css files (they define the tokens)
    if (!context.filename || !context.filename.endsWith('.vue')) {
      return {};
    }

    // Exclude token-definition files and base component styles
    if (context.filename.includes('/styles/')) {
      return {};
    }

    return {
      Program(node) {
        const source = context.getSourceCode().getText();

        // Extract <style> blocks from Vue SFC
        const styleRegex = /<style[^>]*>([\s\S]*?)<\/style>/gi;
        let blockMatch;

        while ((blockMatch = styleRegex.exec(source)) !== null) {
          const styleContent = blockMatch[1];
          const blockOffset = blockMatch.index + blockMatch[0].indexOf('>') + 1;

          // Find the line offset for this block
          const beforeBlock = source.substring(0, blockMatch.index);
          const blockStartLine = beforeBlock.split('\n').length;

          const colors = findStandaloneColors(styleContent);
          for (const c of colors) {
            context.report({
              loc: {
                line: blockStartLine + c.line - 1,
                column: c.column,
              },
              messageId: 'noHardcodedColor',
              data: { value: c.value },
            });
          }
        }
      },
    };
  },
};
