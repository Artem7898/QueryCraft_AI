/**
 * @jest-environment jsdom
 */

describe('Analytics Integration', () => {
  beforeEach(() => {
    jest.resetModules();
    process.env.NODE_ENV = 'test';

    // Мокаем глобальные объекты аналитики
    window.gtag = jest.fn();
    window.ym = jest.fn();
  });

  test('should initialize analytics functions', () => {
    // Проверяем, что файл существует и экспортирует функции
    const analytics = require('../../public/assets/js/analytics');

    expect(typeof analytics.initAnalytics).toBe('function');
    expect(typeof analytics.trackSQLGeneration).toBe('function');

    // Вызываем функции и проверяем, что не падают
    expect(() => analytics.initAnalytics()).not.toThrow();
    expect(() => analytics.trackSQLGeneration('simple', true)).not.toThrow();
  });

  test('should track SQL generation events without errors', () => {
    const analytics = require('../../public/assets/js/analytics');

    // Проверяем вызов функции отслеживания
    analytics.trackSQLGeneration('complex', false);

    // Функция должна выполниться без ошибок
    expect(() => analytics.trackSQLGeneration('medium', true)).not.toThrow();
  });
});
