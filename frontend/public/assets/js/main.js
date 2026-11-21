// Инициализация при загрузке
document.addEventListener('DOMContentLoaded', function() {
  console.log('✅ QueryCraft AI loaded');

  // Язык
  let currentLang = localStorage.getItem('lang') === 'en' ? 'en' : 'ru';
  document.getElementById('currentLang').textContent = currentLang.toUpperCase();

  // Применяем язык при загрузке
  if (typeof window.changeLanguage === 'function') {
    window.changeLanguage(currentLang);
  }

  // Базовый URL API
  const API_BASE_URL = 'http://localhost:8000/api/v1';
  const providerNames = new Map([
    ['bytez', 'Bytez'],
    ['openai', 'OpenAI'],
    ['ollama', 'Ollama']
  ]);

  // Проверяем соединение при загрузке
  checkBackendConnection();

  // Инициализация ThemeSwitcher (он уже создан при загрузке скрипта)
  if (window.themeSwitcher) {
    window.themeSwitcher.initWithStyles();
  }

  // Модальное окно
  const modal = document.getElementById('queryModal');
  const openBtn = document.getElementById('openModal');
  const closeBtn = document.getElementById('closeModal');
  const resultSection = document.getElementById('result');
  const generationUnavailable = document.getElementById('generationUnavailable');

  // Открытие модального окна
  openBtn.addEventListener('click', function() {
    modal.classList.remove('hidden', 'opacity-0', 'pointer-events-none');
    modal.classList.add('opacity-100', 'pointer-events-auto');
    setTimeout(() => {
      document.getElementById('queryInput').focus();
    }, 100);
  });

  // Закрытие модального окна
  closeBtn.addEventListener('click', function() {
    modal.classList.add('opacity-0', 'pointer-events-none');
    setTimeout(() => {
      modal.classList.add('hidden');
      resultSection.classList.add('hidden');
      generationUnavailable.classList.add('hidden');
    }, 300);
  });

  // Закрытие по клику вне окна
  modal.addEventListener('click', function(e) {
    if (e.target === modal) {
      closeBtn.click();
    }
  });

  // Закрытие по ESC
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
      closeBtn.click();
    }
  });

  // Кнопка языка
  document.getElementById('langBtn').addEventListener('click', function() {
    currentLang = currentLang === 'ru' ? 'en' : 'ru';
    localStorage.setItem('lang', currentLang);
    document.getElementById('currentLang').textContent = currentLang.toUpperCase();

    if (typeof window.changeLanguage === 'function') {
      window.changeLanguage(currentLang);
    }

    // Отправляем событие о смене языка
    const event = new CustomEvent('languageChanged', { detail: { language: currentLang } });
    document.dispatchEvent(event);

    console.log(`🌐 Language changed to: ${currentLang}`);
  });

  // Карусель - добавим больше слайдов
  if (typeof window.Swiper !== 'undefined') {
    setTimeout(() => {
      try {
        new window.Swiper('.swiper', {
          slidesPerView: 1,
          spaceBetween: 20,
          pagination: {
            el: '.swiper-pagination',
            clickable: true,
          },
          autoplay: {
            delay: 4000,
            disableOnInteraction: false,
          },
          loop: true,
          breakpoints: {
            640: {
              slidesPerView: 2,
            }
          }
        });
        console.log('🔄 Carousel initialized');
      } catch (e) {
        console.warn('⚠️ Carousel error:', e);
      }
    }, 500);
  }

  // Счетчик символов
  const queryInput = document.getElementById('queryInput');
  queryInput.addEventListener('input', function() {
    const length = this.value.length;
    const charCount = document.getElementById('charCount') || createCharCounter();
    charCount.textContent = `${length} символов`;
    charCount.style.color = length > 500 ? '#ef4444' : length > 200 ? '#f59e0b' : '#6b7280';
  });

  function createCharCounter() {
    const charCount = document.createElement('div');
    charCount.id = 'charCount';
    charCount.className = 'text-xs text-gray-500 mt-1 text-right';
    queryInput.parentNode.appendChild(charCount);
    return charCount;
  }

  // Форма генерации запроса
  const schemaContextInput = document.getElementById('schemaContext');
  const liveResultSource = document.getElementById('liveResultSource');
  const demoResultSource = document.getElementById('demoResultSource');
  document.getElementById('queryForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    generationUnavailable.classList.add('hidden');

    const text = queryInput.value.trim();
    const schemaContext = schemaContextInput.value.trim();
    const dbType = document.getElementById('dbType').value;
    const complexity = document.getElementById('complexity').value;

    if (!text) {
      showAlert(currentLang === 'ru'
        ? 'Пожалуйста, опишите ваш запрос'
        : 'Please describe your query', 'error');
      return;
    }

    if (schemaContext.length > schemaContextInput.maxLength) {
      showAlert(window.t('schemaContextTooLong'), 'error');
      return;
    }

    const requestBody = { text, db_type: dbType, complexity, language: currentLang };
    if (schemaContext) {
      requestBody.schema_context = schemaContext;
    }

    // Индикатор загрузки
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = currentLang === 'ru'
      ? '<span class="flex items-center justify-center"><span class="animate-spin mr-2">⟳</span> Генерация...</span>'
      : '<span class="flex items-center justify-center"><span class="animate-spin mr-2">⟳</span> Generating...</span>';
    submitBtn.disabled = true;

    // Скрываем старый результат
    resultSection.classList.add('hidden');

    try {
      console.log('📤 Sending request to:', `${API_BASE_URL}/generate`);

      const response = await fetch(`${API_BASE_URL}/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify(requestBody)
      });

      console.log('📥 Received response:', response.status);

      if (response.status === 503) {
        generationUnavailable.classList.remove('hidden');
        return;
      }

      if (!response.ok) {
        let errorText = `HTTP error ${response.status}`;
        try {
          const errorData = await response.json();
          if (typeof errorData.detail === 'string' && errorData.detail) {
            errorText = errorData.detail;
          }
        } catch {
          // Не удалось распарсить JSON
        }
        throw new Error(errorText);
      }

      const result = await response.json();
      // Отображаем результат
      highlightSQL(result.query);
      document.getElementById('explanation').textContent = result.explanation;
      const providerName = result.source === 'live' ? providerNames.get(result.provider) : undefined;
      const model = providerName ? `${result.model} (${providerName})` : result.model;
      document.getElementById('executionTime').textContent = currentLang === 'ru'
        ? `Время: ${result.executed_in} сек. | Модель: ${model}`
        : `Time: ${result.executed_in} sec. | Model: ${model}`;

      liveResultSource.classList.toggle('hidden', result.source !== 'live');
      demoResultSource.classList.toggle('hidden', result.source !== 'demo');
      resultSection.classList.remove('hidden');

      // Прокручиваем к результату
      setTimeout(() => {
        resultSection.scrollIntoView({
          behavior: 'smooth',
          block: 'center'
        });
      }, 100);

      if (result.source === 'demo') {
        showAlert(window.t('demoResult'), 'info');
      } else if (result.source === 'live') {
        showAlert(currentLang === 'ru' ? '✅ Запрос успешно сгенерирован!' : '✅ Query generated successfully!', 'success');
      }

    } catch (error) {
      console.error('❌ Error generating query:', error);

      // Показываем ошибку
      document.getElementById('queryOutput').textContent = currentLang === 'ru'
        ? `-- Ошибка при генерации запроса\n-- ${error.message}`
        : `-- Error generating query\n-- ${error.message}`;
      document.getElementById('explanation').textContent = currentLang === 'ru'
        ? 'Проверьте подключение к бэкенду.'
        : 'Check backend connection.';
      document.getElementById('executionTime').textContent = '';

      liveResultSource.classList.add('hidden');
      demoResultSource.classList.add('hidden');
      resultSection.classList.remove('hidden');

      showAlert(currentLang === 'ru'
        ? `❌ Ошибка: ${error.message}`
        : `❌ Error: ${error.message}`, 'error');
    } finally {
      // Восстанавливаем кнопку
      submitBtn.innerHTML = originalText;
      submitBtn.disabled = false;
    }
  });

  // Кнопка копирования
  document.getElementById('copyBtn').addEventListener('click', function() {
    const text = document.getElementById('queryOutput').textContent;

    if (!text) return;

    navigator.clipboard.writeText(text).then(function() {
      const copyBtn = document.getElementById('copyBtn');
      const originalText = copyBtn.innerHTML;

      copyBtn.innerHTML = currentLang === 'ru' ? '✓ Скопировано!' : '✓ Copied!';
      copyBtn.classList.add('bg-green-500');

      setTimeout(function() {
        copyBtn.innerHTML = originalText;
        copyBtn.classList.remove('bg-green-500');
      }, 2000);

      showAlert(currentLang === 'ru' ? '✅ Текст скопирован!' : '✅ Text copied!', 'success');
    }).catch(function(err) {
      console.error('❌ Copy failed:', err);
      showAlert(currentLang === 'ru' ? '❌ Ошибка копирования' : '❌ Copy failed', 'error');
    });
  });

  // Функция подсветки SQL
  function highlightSQL(sql) {
    const pre = document.getElementById('queryOutput');
    if (!pre) return;

    // Ключевые слова SQL
    const keywords = [
      'SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER',
      'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT', 'OFFSET', 'INSERT', 'UPDATE',
      'DELETE', 'CREATE', 'ALTER', 'DROP', 'TABLE', 'DATABASE', 'INDEX',
      'VIEW', 'PROCEDURE', 'FUNCTION', 'TRIGGER', 'UNION', 'ALL', 'DISTINCT',
      'AS', 'ON', 'USING', 'SET', 'VALUES', 'INTO', 'NULL', 'NOT', 'AND',
      'OR', 'IS', 'BETWEEN', 'LIKE', 'IN', 'EXISTS', 'CASE', 'WHEN', 'THEN',
      'ELSE', 'END', 'ASC', 'DESC'
    ];

    const tokenPattern = new RegExp([
      /(?<comment>--[^\r\n]*)/.source,
      /(?<string>'(?:''|[^'])*')/.source,
      `(?<keyword>\\b(?:${keywords.join('|')})\\b)`,
      /(?<number>\b\d+\b)/.source
    ].join('|'), 'gi');
    const classes = {
      comment: 'text-gray-500 italic',
      string: 'text-green-600',
      keyword: 'text-purple-600 font-semibold',
      number: 'text-blue-600'
    };

    const fragment = document.createDocumentFragment();
    let offset = 0;
    for (const match of sql.matchAll(tokenPattern)) {
      fragment.append(sql.slice(offset, match.index));
      const span = document.createElement('span');
      const token = Object.keys(classes).find(key => match.groups[key] !== undefined);
      span.className = classes[token];
      span.textContent = match[0];
      fragment.append(span);
      offset = match.index + match[0].length;
    }
    fragment.append(sql.slice(offset));
    pre.replaceChildren(fragment);
  }

  // Функция показа уведомлений
  function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg transition-all duration-300 transform translate-x-full ${type === 'error' ? 'bg-red-500 text-white' : type === 'success' ? 'bg-green-500 text-white' : 'bg-blue-500 text-white'}`;
    alertDiv.textContent = message;

    document.body.appendChild(alertDiv);

    setTimeout(() => {
      alertDiv.classList.remove('translate-x-full');
      alertDiv.classList.add('translate-x-0');
    }, 10);

    setTimeout(() => {
      alertDiv.classList.remove('translate-x-0');
      alertDiv.classList.add('translate-x-full');
      setTimeout(() => {
        if (document.body.contains(alertDiv)) {
          document.body.removeChild(alertDiv);
        }
      }, 300);
    }, 3000);
  }

  // Функция проверки соединения с бэкендом
  async function checkBackendConnection() {
    try {
      console.log('🔍 Checking backend connection...');
      const response = await fetch(`${API_BASE_URL}/health`);

      if (response.ok) {
        const data = await response.json();
        console.log('✅ Backend connected:', data);
        showAlert(currentLang === 'ru' ? '✅ Соединение с бэкендом установлено' : '✅ Backend connected', 'success');
      } else {
        console.warn('⚠️ Backend connection failed:', response.status);
        showAlert(currentLang === 'ru' ? '⚠️ Бэкенд не отвечает' : '⚠️ Backend not responding', 'error');
      }
    } catch (error) {
      console.error('❌ Backend connection error:', error);
      showAlert(currentLang === 'ru'
        ? '❌ Не удалось подключиться к бэкенду. Убедитесь, что сервер запущен на порту 8000.'
        : '❌ Failed to connect to backend. Make sure server is running on port 8000.', 'error');
    }
  }

  // Примеры запросов
  createExamples();

  function createExamples() {
    const examples = [
      {
        title: currentLang === 'ru' ? "Найти активных пользователей" : "Find active users",
        description: currentLang === 'ru' ? "Выбрать всех пользователей старше 25 лет со статусом 'active'" : "Select all users older than 25 with 'active' status",
        query: currentLang === 'ru' ? "показать всех пользователей старше 25 лет со статусом active" : "show all users older than 25 years with status active"
      },
      {
        title: currentLang === 'ru' ? "Статистика заказов" : "Order statistics",
        description: currentLang === 'ru' ? "Подсчитать общую сумму заказов по месяцам" : "Calculate total order amount by month",
        query: currentLang === 'ru' ? "получить общую сумму заказов по каждому месяцу за последний год" : "get total order amount for each month in the last year"
      },
      {
        title: currentLang === 'ru' ? "Поиск товаров" : "Product search",
        description: currentLang === 'ru' ? "Найти товары в определенной категории" : "Find products in specific category",
        query: currentLang === 'ru' ? "найти все товары в категории 'Электроника' с ценой от 100 до 1000" : "find all products in category 'Electronics' with price between 100 and 1000"
      },
      {
        title: currentLang === 'ru' ? "Анализ пользователей" : "User analysis",
        description: currentLang === 'ru' ? "Показать топ-10 самых активных пользователей" : "Show top 10 most active users",
        query: currentLang === 'ru' ? "показать топ 10 пользователей с наибольшим количеством заказов за последний месяц" : "show top 10 users with the most orders in the last month"
      }
    ];

    const examplesContainer = document.createElement('div');
    examplesContainer.className = 'grid grid-cols-1 md:grid-cols-2 gap-4 mt-8';
    examplesContainer.id = 'examplesContainer';

    examples.forEach(example => {
      const exampleDiv = document.createElement('div');
      exampleDiv.className = 'p-4 rounded-lg border-2 cursor-pointer hover:border-blue-500 transition-all hover:shadow-md';
      exampleDiv.style.borderColor = 'var(--color-border)';

      exampleDiv.innerHTML = `
        <p class="font-medium mb-2 text-gray-800 dark:text-white">${example.title}</p>
        <p class="text-sm text-gray-600 dark:text-gray-300">${example.description}</p>
        <div class="mt-2 text-xs text-gray-500 dark:text-gray-400">${currentLang === 'ru' ? 'Нажмите для использования' : 'Click to use'}</div>
      `;

      exampleDiv.addEventListener('click', () => {
        document.getElementById('queryInput').value = example.query;
        document.getElementById('openModal').click();

        // Запускаем событие input для обновления счетчика
        const event = new Event('input', { bubbles: true });
        document.getElementById('queryInput').dispatchEvent(event);
      });

      examplesContainer.appendChild(exampleDiv);
    });

    // Добавляем контейнер с примерами после кнопки открытия модального окна
    const openModalBtn = document.getElementById('openModal');
    if (openModalBtn && openModalBtn.parentNode) {
      openModalBtn.parentNode.parentNode.insertBefore(examplesContainer, openModalBtn.parentNode.nextSibling);
    }
  }

  // Обработчик события смены темы
  document.addEventListener('themeChanged', (e) => {
    console.log(`🎨 Theme changed to: ${e.detail.theme}`, e.detail.themeData);
  });
}, { once: true });
