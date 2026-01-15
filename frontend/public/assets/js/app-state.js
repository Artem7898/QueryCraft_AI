/**
 * App State Manager для QueryCraft AI
 * Централизованное управление состоянием приложения
 */

class AppState {
  constructor() {
    this.state = {
      language: localStorage.getItem('lang') || 'ru',
      theme: localStorage.getItem('theme') || 'light',
      apiConnected: false,
      lastQuery: null,
      queryHistory: JSON.parse(localStorage.getItem('queryHistory')) || [],
      settings: {
        autoCopy: false,
        autoSave: true,
        notifications: true,
        darkMode: localStorage.getItem('theme') === 'dark'
      }
    };

    this.subscribers = [];
  }

  /**
   * Получить текущее состояние
   */
  getState() {
    return { ...this.state };
  }

  /**
   * Обновить состояние
   */
  setState(updates) {
    const oldState = { ...this.state };
    this.state = { ...this.state, ...updates };

    // Сохраняем в localStorage при необходимости
    this.persistState();

    // Уведомляем подписчиков
    this.notifySubscribers(oldState, this.state);

    return this.state;
  }

  /**
   * Подписаться на изменения состояния
   */
  subscribe(callback) {
    this.subscribers.push(callback);
    return () => {
      this.subscribers = this.subscribers.filter(cb => cb !== callback);
    };
  }

  /**
   * Уведомить подписчиков
   */
  notifySubscribers(oldState, newState) {
    this.subscribers.forEach(callback => {
      try {
        callback(oldState, newState);
      } catch (error) {
        console.error('Error in state subscriber:', error);
      }
    });
  }

  /**
   * Сохранить состояние в localStorage
   */
  persistState() {
    if (this.state.settings.autoSave) {
      localStorage.setItem('lang', this.state.language);
      localStorage.setItem('theme', this.state.theme);
      localStorage.setItem('queryHistory', JSON.stringify(this.state.queryHistory));
      localStorage.setItem('appSettings', JSON.stringify(this.state.settings));
    }
  }

  /**
   * Добавить запрос в историю
   */
  addToHistory(query, result) {
    const historyItem = {
      id: Date.now(),
      timestamp: new Date().toISOString(),
      query,
      result: {
        sql: result.query,
        explanation: result.explanation,
        executionTime: result.executed_in,
        model: result.model
      }
    };

    this.state.queryHistory.unshift(historyItem);

    // Ограничиваем историю 50 записями
    if (this.state.queryHistory.length > 50) {
      this.state.queryHistory = this.state.queryHistory.slice(0, 50);
    }

    this.persistState();
    this.notifySubscribers(this.state, this.state);

    return historyItem;
  }

  /**
   * Очистить историю запросов
   */
  clearHistory() {
    this.state.queryHistory = [];
    localStorage.removeItem('queryHistory');
    this.notifySubscribers(this.state, this.state);
  }

  /**
   * Получить историю запросов
   */
  getHistory() {
    return [...this.state.queryHistory];
  }

  /**
   * Обновить настройки
   */
  updateSettings(settings) {
    return this.setState({
      settings: { ...this.state.settings, ...settings }
    });
  }

  /**
   * Проверить подключение к API
   */
  async checkApiConnection() {
    try {
      const response = await fetch('http://localhost:8000/api/v1/health');
      const connected = response.ok;

      this.setState({ apiConnected: connected });
      return connected;
    } catch (error) {
      this.setState({ apiConnected: false });
      return false;
    }
  }
}

// Создаем глобальный экземпляр AppState
window.appState = new AppState();

// Экспортируем для использования в модулях
if (typeof module !== 'undefined' && module.exports) {
  module.exports = AppState;
}