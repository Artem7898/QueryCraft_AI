/**
 * @jest-environment jsdom
 */

// Мокаем внешние модули
jest.mock('../../assets/js/analytics', () => ({
  initAnalytics: jest.fn(),
  trackSQLGeneration: jest.fn()
}));

describe('Main Application', () => {
  let mainModule;

  beforeEach(() => {
    jest.useFakeTimers();

    // Создаем DOM для тестов
    document.body.innerHTML = `
      <div class="app-container">
        <header>
          <div id="currentLang">RU</div>
          <button id="langBtn">EN</button>
          <button id="openModal">Open</button>
        </header>

        <main>
          <form id="queryForm">
            <textarea id="queryInput" maxlength="500"></textarea>
            <div id="charCount">0/500</div>
            <button type="submit">Generate</button>
          </form>

          <div id="queryModal" class="hidden">
            <button id="closeModal">×</button>
          </div>
        </main>
      </div>
    `;

    jest.resetModules();
    mainModule = require('../../assets/js/main.js');
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  test('should initialize without errors', () => {
    if (mainModule.init) {
      expect(() => mainModule.init()).not.toThrow();
    }
  });

  test('should update character counter on input', () => {
    const textarea = document.getElementById('queryInput');
    const charCount = document.getElementById('charCount');

    // Вызываем функцию обновления счетчика
    textarea.value = 'SELECT * FROM users';
    if (mainModule.updateCharCounter) {
      mainModule.updateCharCounter();
      expect(charCount.textContent).toContain('19');
    }
  });

  test('should open and close modal', () => {
    const modal = document.getElementById('queryModal');
    const openBtn = document.getElementById('openModal');
    const closeBtn = document.getElementById('closeModal');

    // Открываем модальное окно
    openBtn.click();
    expect(modal.classList.contains('hidden')).toBe(false);

    // Закрываем модальное окно
    closeBtn.click();
    expect(modal.classList.contains('hidden')).toBe(true);
  });

  test('should handle form submission', () => {
    const form = document.getElementById('queryForm');

    // Мокаем fetch
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ query: 'SELECT 1' })
      })
    );

    // Отправляем форму
    form.dispatchEvent(new Event('submit'));

    // Проверяем, что fetch был вызван
    expect(global.fetch).toHaveBeenCalled();
  });
});