const js = require('@eslint/js');
const globals = require('globals');

module.exports = [
  {
    ...js.configs.recommended,
    files: ['public/**/*.js'],
    languageOptions: {
      sourceType: 'script',
      globals: globals.browser
    },
    rules: {
      ...js.configs.recommended.rules,
      'eqeqeq': 'error',
      'no-unused-vars': 'warn',
      'no-var': 'error',
      'prefer-const': 'error'
    }
  },
  {
    files: ['public/assets/js/analytics.js'],
    languageOptions: { sourceType: 'module' }
  },
  {
    files: ['public/assets/js/app-state.js', 'public/assets/js/theme-switcher.js'],
    languageOptions: { globals: { module: 'readonly' } }
  },
  {
    files: ['public/service-worker.js'],
    languageOptions: { globals: globals.serviceworker }
  }
];
