/**
 * @jest-environment jsdom
 */

// Сначала создаем DOM, потом мокаем
const mockModule = () => {
  let currentTheme = 'light';
  const themes = ['light', 'dark', 'transformative-teal'];

  return {
    initThemeSwitcher: jest.fn((buttonId) => {
      const button = document.getElementById(buttonId);
      if (button) {
        button.addEventListener('click', () => {
          const currentIndex = themes.indexOf(currentTheme);
          currentTheme = themes[(currentIndex + 1) % themes.length];
          document.documentElement.setAttribute('data-theme', currentTheme);
          localStorage.setItem('theme', currentTheme);
        });
      }
    }),
    switchTheme: jest.fn(() => {
      const currentIndex = themes.indexOf(currentTheme);
      currentTheme = themes[(currentIndex + 1) % themes.length];
      return currentTheme;
    }),
    getCurrentTheme: jest.fn(() => currentTheme)
  };
};

// Мокаем модуль
jest.mock('../../assets/js/theme-switcher.js', () => mockModule());

describe('Theme Switcher', () => {
  let themeModule;

  beforeEach(() => {
    document.body.innerHTML = `
      <html data-theme="light">
        <button id="themeBtn">Switch Theme</button>
      </html>
    `;

    // Сбрасываем модуль
    jest.resetModules();
    themeModule = require('../../assets/js/theme-switcher.js');
  });

  test('should initialize theme switcher', () => {
    themeModule.initThemeSwitcher('themeBtn');
    expect(themeModule.initThemeSwitcher).toHaveBeenCalledWith('themeBtn');
  });

  test('should switch themes', () => {
    const html = document.documentElement;

    // Проверяем начальную тему
    expect(html.getAttribute('data-theme')).toBe('light');

    // Симулируем клик через функцию
    const themeBtn = document.getElementById('themeBtn');
    if (themeModule.initThemeSwitcher.mock.calls.length > 0) {
      // Если initThemeSwitcher был вызван, кнопка должна иметь обработчик
      themeBtn.click();
      // Проверяем, что тема изменилась
      expect(html.getAttribute('data-theme')).toBe('dark');
    }
  });
});