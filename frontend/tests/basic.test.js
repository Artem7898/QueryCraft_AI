/**
 * @jest-environment jsdom
 */

describe('Basic frontend tests', () => {
  test('should pass basic assertion', () => {
    expect(true).toBe(true);
  });

  test('should handle simple math', () => {
    expect(1 + 1).toBe(2);
  });

  test('should mock localStorage correctly', () => {
    localStorage.setItem('test', 'value');
    expect(localStorage.setItem).toHaveBeenCalledWith('test', 'value');
    expect(localStorage.getItem('test')).toBe('value');
  });

  test('should mock sessionStorage', () => {
    sessionStorage.setItem('session', 'data');
    expect(sessionStorage.setItem).toHaveBeenCalledWith('session', 'data');
  });

  test('should mock clipboard API', async () => {
    await navigator.clipboard.writeText('test');
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('test');
  });
});