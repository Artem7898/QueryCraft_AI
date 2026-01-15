module.exports = {
  env: {
    browser: true,
    es2021: true,
    node: true,
    jest: true
  },
  extends: [
    'eslint:recommended'
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module'
  },
  rules: {
    // Правила JavaScript
    'indent': ['error', 2],
    'linebreak-style': ['error', 'unix'],
    'quotes': ['error', 'single'],
    'semi': ['error', 'always'],
    'no-console': 'warn',
    'no-unused-vars': 'warn',
    'no-var': 'error',
    'prefer-const': 'error',
    'arrow-spacing': ['error', { 'before': true, 'after': true }],
    'comma-dangle': ['error', 'never'],
    'eqeqeq': ['error', 'always'],
    'no-trailing-spaces': 'error',
    'object-curly-spacing': ['error', 'always'],
    'space-before-blocks': 'error',
    'space-before-function-paren': ['error', 'never'],
    'space-in-parens': ['error', 'never']
  },
  ignorePatterns: [
    'node_modules/',
    'dist/',
    'build/',
    'coverage/',
    '*.min.js'
  ]
};