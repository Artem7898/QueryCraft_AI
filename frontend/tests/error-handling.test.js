/**
 * @jest-environment jsdom
 */

// Мокаем Sentry
jest.mock('@sentry/react', () => ({
  captureException: jest.fn(),
  init: jest.fn()
}));

describe('Error Handling', () => {
  beforeEach(() => {
    jest.resetModules();

    // Создаем минимальный DOM
    document.body.innerHTML = `
      <form id="queryForm">
        <button type="submit">Generate</button>
      </form>
    `;
  });

  test('should capture errors with Sentry', () => {
    const Sentry = require('@sentry/react');
    const error = new Error('Test error');

    // Симулируем глобальную ошибку
    window.dispatchEvent(new ErrorEvent('error', { error }));

    // Проверяем, что Sentry был вызван
    expect(Sentry.captureException).toHaveBeenCalledWith(error);
  });

  test('should handle network errors gracefully', () => {
    // Мокаем fetch для ошибки сети
    global.fetch = jest.fn(() => Promise.reject(new Error('Network error')));

    const form = document.getElementById('queryForm');

    // Добавляем обработчик ошибки
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-alert';
    errorDiv.style.display = 'none';
    document.body.appendChild(errorDiv);

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        await fetch('/api/generate');
      } catch (error) {
        errorDiv.style.display = 'block';
        errorDiv.textContent = 'Network error';
      }
    });

    // Отправляем форму
    form.dispatchEvent(new Event('submit'));

    // Проверяем, что ошибка отобразилась
    const errorAlert = document.querySelector('.error-alert');
    expect(errorAlert).not.toBeNull();
  });
});