/** @type {import('eslint').Linter.Config} */
const eslintConfig = [
  {
    ignores: [
      '**/node_modules/**',
      '**/.venv/**',
      '**/.pytest_cache/**',
      '**/dist/**',
      '**/.output/**',
      '**/coverage/**',
      '**/pnpm-lock.yaml',
      '**/*.d.ts',
    ],
  },
  // Base TypeScript config (exclude .vue — Vue uses its own parser)
  {
    files: ['**/*.{ts,tsx,mjs,cjs}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      parser: await import('@typescript-eslint/parser'),
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
      globals: {
        ...(await import('globals')).browser,
        ...(await import('globals')).node,
      },
    },
    plugins: {
      '@typescript-eslint': (await import('@typescript-eslint/eslint-plugin')).default,
    },
    rules: {
      // TypeScript
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/explicit-function-return-type': 'off',
      '@typescript-eslint/consistent-type-imports': ['error', { prefer: 'type-imports' }],
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/array-type': ['error', { default: 'generic' }],

      // General
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      'no-debugger': 'error',
      'prefer-const': 'error',
      'no-var': 'error',
    },
  },
  // Vue files — vue-eslint-parser is the main parser;
  // @typescript-eslint/parser is the script-block sub-parser.
  {
    files: ['**/*.vue'],
    languageOptions: {
      parser: await import('vue-eslint-parser'),
      parserOptions: {
        parser: await import('@typescript-eslint/parser'),
        ecmaFeatures: { jsx: true },
        extraFileExtensions: ['.vue'],
      },
      globals: {
        ...(await import('globals')).browser,
        ...(await import('globals')).node,
      },
    },
    plugins: {
      vue: (await import('eslint-plugin-vue')).default,
      '@typescript-eslint': (await import('@typescript-eslint/eslint-plugin')).default,
    },
    rules: {
      // TypeScript rules (same as base, applied inside <script> blocks)
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/consistent-type-imports': ['error', { prefer: 'type-imports' }],
      '@typescript-eslint/no-explicit-any': 'warn',

      // Vue rules
      'vue/multi-word-component-names': 'off',
      'vue/require-default-prop': 'off',
      'vue/no-v-html': 'warn',
    },
  },
  // Test files
  {
    files: ['**/*.{test,spec}.{ts,js}'],
    rules: {
      'no-console': 'off',
      '@typescript-eslint/no-explicit-any': 'off',
    },
  },
  // Prettier compatibility
  (await import('eslint-config-prettier')).default,
];

export default eslintConfig;
