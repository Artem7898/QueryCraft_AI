module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/tests/setup.js'],
  collectCoverageFrom: [
    'assets/js/**/*.js',
    '!assets/js/vendor/**',
    '!**/node_modules/**'
  ],
  coverageThreshold: {
    global: {
      branches: 50,
      functions: 50,
      lines: 50,
      statements: 50
    }
  },
  transform: {
    '^.+\\.js$': 'babel-jest'
  },
  moduleNameMapper: {
    '^@sentry/react$': '<rootDir>/__mocks__/sentry.js'
  },
  transformIgnorePatterns: [
    '/node_modules/(?!@sentry)/'
  ]
};