beforeEach(() => {
  jest.useFakeTimers();
  jest.resetModules();
  document.body.innerHTML = '<button id="themeBtn">Switch Theme</button>';
});

afterEach(() => {
  jest.useRealTimers();
});

test('initializes from the saved theme', () => {
  localStorage.setItem('theme', 'verdant-green');
  require('../../public/assets/js/theme-switcher.js');

  expect(document.documentElement).toHaveAttribute('data-theme', 'verdant-green');
  expect(document.getElementById('themeSelector')).toHaveClass('hidden');
});

test('opens the theme selector, applies the selected theme and saves it', () => {
  require('../../public/assets/js/theme-switcher.js');

  const selector = document.getElementById('themeSelector');
  document.getElementById('themeBtn').click();
  expect(selector).not.toHaveClass('hidden');
  selector.querySelector('button[data-theme="dark"]').click();

  expect(document.documentElement).toHaveAttribute('data-theme', 'dark');
  expect(localStorage.getItem('theme')).toBe('dark');
  jest.advanceTimersByTime(300);
  expect(selector).toHaveClass('hidden');
});
