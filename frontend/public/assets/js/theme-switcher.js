/**
 * Theme Switcher для QueryCraft AI
 * Управление темами приложения
 */

class ThemeSwitcher {
  constructor() {
    this.themes = [
      {
        id: 'light',
        name: 'Светлая',
        description: 'Светлая тема по умолчанию',
        icon: '☀️'
      },
      {
        id: 'dark',
        name: 'Темная',
        description: 'Темная тема для комфортной работы ночью',
        icon: '🌙'
      },
      {
        id: 'transformative-teal',
        name: 'Бирюзовая',
        description: 'Бирюзовая тема для концентрации',
        icon: '🔷'
      },
      {
        id: 'verdant-green',
        name: 'Зеленая',
        description: 'Зеленая тема для расслабления',
        icon: '🌿'
      },
      {
        id: 'deep-forest',
        name: 'Лесная',
        description: 'Темно-зеленая тема для длительной работы',
        icon: '🌲'
      }
    ];

    this.currentTheme = this.getSavedTheme();
    this.init();
  }

  /**
   * Инициализация переключателя тем
   */
  init() {
    // Применяем сохраненную тему при загрузке
    this.applyTheme(this.currentTheme);

    // Создаем UI для выбора темы, если кнопка существует
    this.createThemeSelector();

    // Вешаем обработчики событий
    this.bindEvents();

    console.log(`🎨 ThemeSwitcher инициализирован. Текущая тема: ${this.currentTheme}`);
  }

  /**
   * Получаем сохраненную тему из localStorage
   */
  getSavedTheme() {
    return localStorage.getItem('theme') || 'light';
  }

  /**
   * Сохраняем тему в localStorage
   */
  saveTheme(themeId) {
    localStorage.setItem('theme', themeId);
    this.currentTheme = themeId;
  }

  /**
   * Применяем тему к документу
   */
  applyTheme(themeId) {
    document.documentElement.setAttribute('data-theme', themeId);

    // Обновляем meta-тег theme-color для PWA
    this.updateThemeColor(themeId);

    // Обновляем текст кнопки
    this.updateButtonText(themeId);

    // Отправляем событие о смене темы
    this.dispatchThemeChangeEvent(themeId);
  }

  /**
   * Обновляем цвет темы для PWA
   */
  updateThemeColor(themeId) {
    const themeColors = {
      'light': '#3b82f6',
      'dark': '#1f2937',
      'transformative-teal': '#14b8a6',
      'verdant-green': '#22c55e',
      'deep-forest': '#10b981'
    };

    const metaTheme = document.querySelector('meta[name="theme-color"]');
    if (metaTheme) {
      metaTheme.setAttribute('content', themeColors[themeId] || '#3b82f6');
    }
  }

  /**
   * Обновляем текст кнопки темы
   */
  updateButtonText(themeId) {
    const themeBtn = document.getElementById('themeBtn');
    if (!themeBtn) return;

    const theme = this.themes.find(t => t.id === themeId);
    if (theme) {
      const currentLang = localStorage.getItem('lang') || 'ru';
      if (currentLang === 'ru') {
        themeBtn.innerHTML = `${theme.icon} Тема: ${theme.name}`;
      } else {
        themeBtn.innerHTML = `${theme.icon} Theme: ${theme.id}`;
      }
      themeBtn.title = theme.description;
    }
  }

  /**
   * Переключаем на следующую тему
   */
  nextTheme() {
    const currentIndex = this.themes.findIndex(t => t.id === this.currentTheme);
    const nextIndex = (currentIndex + 1) % this.themes.length;
    const nextTheme = this.themes[nextIndex];

    this.saveTheme(nextTheme.id);
    this.applyTheme(nextTheme.id);

    return nextTheme;
  }

  /**
   * Переключаем на конкретную тему по ID
   */
  switchToTheme(themeId) {
    const theme = this.themes.find(t => t.id === themeId);
    if (!theme) {
      console.warn(`Тема ${themeId} не найдена`);
      return;
    }

    this.saveTheme(themeId);
    this.applyTheme(themeId);
    return theme;
  }

  /**
   * Получаем текущую тему
   */
  getCurrentTheme() {
    return this.themes.find(t => t.id === this.currentTheme);
  }

  /**
   * Получаем все доступные темы
   */
  getAllThemes() {
    return this.themes;
  }

  /**
   * Создаем селектор для выбора темы
   */
  createThemeSelector() {
    // Проверяем, существует ли уже селектор
    if (document.getElementById('themeSelector')) {
      return;
    }

    // Создаем контейнер для селектора
    const selectorContainer = document.createElement('div');
    selectorContainer.id = 'themeSelector';
    selectorContainer.className = 'hidden fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center';

    // Создаем модальное окно
    const modal = document.createElement('div');
    modal.className = 'bg-white dark:bg-gray-800 rounded-xl p-6 max-w-md w-full mx-4 shadow-2xl';

    // Заголовок
    const title = document.createElement('h3');
    title.className = 'text-xl font-bold mb-4 text-gray-800 dark:text-white';
    title.textContent = 'Выберите тему';

    // Контейнер для кнопок тем
    const themesContainer = document.createElement('div');
    themesContainer.className = 'space-y-2';

    // Создаем кнопки для каждой темы
    this.themes.forEach(theme => {
      const button = document.createElement('button');
      button.className = `w-full p-3 rounded-lg flex items-center justify-between transition-all hover:scale-105 ${
        theme.id === this.currentTheme
          ? 'bg-blue-100 dark:bg-blue-900 border-2 border-blue-500'
          : 'bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600'
      }`;
      button.setAttribute('data-theme', theme.id);

      // Левый блок с иконкой и названием
      const leftBlock = document.createElement('div');
      leftBlock.className = 'flex items-center space-x-3';

      const icon = document.createElement('span');
      icon.className = 'text-xl';
      icon.textContent = theme.icon;

      const textBlock = document.createElement('div');
      textBlock.className = 'text-left';

      const themeName = document.createElement('div');
      themeName.className = 'font-medium text-gray-800 dark:text-white';
      themeName.textContent = theme.name;

      const themeDesc = document.createElement('div');
      themeDesc.className = 'text-xs text-gray-600 dark:text-gray-300';
      themeDesc.textContent = theme.description;

      textBlock.appendChild(themeName);
      textBlock.appendChild(themeDesc);

      leftBlock.appendChild(icon);
      leftBlock.appendChild(textBlock);

      // Маркер выбранной темы
      const checkmark = document.createElement('span');
      checkmark.className = 'text-blue-500 text-xl';
      checkmark.textContent = theme.id === this.currentTheme ? '✓' : '';

      button.appendChild(leftBlock);
      button.appendChild(checkmark);

      // Обработчик клика
      button.addEventListener('click', () => {
        this.switchToTheme(theme.id);
        this.closeThemeSelector();
      });

      themesContainer.appendChild(button);
    });

    // Кнопка закрытия
    const closeButton = document.createElement('button');
    closeButton.className = 'w-full mt-4 p-3 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-white rounded-lg font-medium hover:bg-gray-300 dark:hover:bg-gray-600 transition-all';
    closeButton.textContent = 'Закрыть';
    closeButton.addEventListener('click', () => this.closeThemeSelector());

    // Собираем модальное окно
    modal.appendChild(title);
    modal.appendChild(themesContainer);
    modal.appendChild(closeButton);
    selectorContainer.appendChild(modal);

    // Добавляем в документ
    document.body.appendChild(selectorContainer);

    // Закрытие по клику вне модального окна
    selectorContainer.addEventListener('click', (e) => {
      if (e.target === selectorContainer) {
        this.closeThemeSelector();
      }
    });

    // Закрытие по клавише Esc
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !selectorContainer.classList.contains('hidden')) {
        this.closeThemeSelector();
      }
    });
  }

  /**
   * Открываем селектор тем
   */
  openThemeSelector() {
    const selector = document.getElementById('themeSelector');
    if (!selector) {
      this.createThemeSelector();
    }

    const selectorContainer = document.getElementById('themeSelector');
    if (selectorContainer) {
      selectorContainer.classList.remove('hidden');
      setTimeout(() => {
        selectorContainer.classList.add('opacity-100');
      }, 10);
    }
  }

  /**
   * Закрываем селектор тем
   */
  closeThemeSelector() {
    const selectorContainer = document.getElementById('themeSelector');
    if (selectorContainer) {
      selectorContainer.classList.remove('opacity-100');
      setTimeout(() => {
        selectorContainer.classList.add('hidden');
      }, 300);
    }
  }

  /**
   * Привязываем события
   */
  bindEvents() {
    // Обработчик для кнопки темы
    const themeBtn = document.getElementById('themeBtn');
    if (themeBtn) {
      themeBtn.addEventListener('click', () => this.openThemeSelector());
    }

    // Обработчик изменения языка
    document.addEventListener('languageChanged', (e) => {
      this.updateButtonText(this.currentTheme);
    });
  }

  /**
   * Отправляем событие о смене темы
   */
  dispatchThemeChangeEvent(themeId) {
    const event = new CustomEvent('themeChanged', {
      detail: {
        theme: themeId,
        themeData: this.getCurrentTheme()
      }
    });
    document.dispatchEvent(event);
  }

  /**
   * Добавляем CSS для плавных переходов
   */
  addTransitionStyles() {
    const style = document.createElement('style');
    style.textContent = `
      #themeSelector {
        opacity: 0;
        transition: opacity 0.3s ease-in-out;
      }

      #themeSelector.opacity-100 {
        opacity: 1;
      }

      [data-theme] {
        transition: all 0.3s ease;
      }

      body {
        transition: background-color 0.3s ease, color 0.3s ease;
      }
    `;
    document.head.appendChild(style);
  }

  /**
   * Инициализация с дополнительными стилями
   */
  initWithStyles() {
    this.addTransitionStyles();
    this.init();
  }
}

// Создаем глобальный экземпляр ThemeSwitcher
window.themeSwitcher = new ThemeSwitcher();

// Экспортируем для использования в модулях
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ThemeSwitcher;
}