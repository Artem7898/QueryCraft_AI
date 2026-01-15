[file name]: assets/js/csrf-protection.js
[file content begin]
/**
 * CSRF Protection для QueryCraft AI
 */

class CSRFProtection {
  constructor() {
    this.token = null;
    this.initialize();
  }

  initialize() {
    this.token = this.getTokenFromStorage() || this.generateToken();
    this.saveToken(this.token);
    this.setupFormProtection();
    console.log('🛡️ CSRF protection initialized');
  }

  generateToken() {
    const array = new Uint8Array(32);
    window.crypto.getRandomValues(array);
    return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
  }

  getToken() {
    return this.token;
  }

  getTokenFromStorage() {
    return localStorage.getItem('csrf_token');
  }

  saveToken(token) {
    localStorage.setItem('csrf_token', token);
  }

  setupFormProtection() {
    document.addEventListener('DOMContentLoaded', () => {
      const forms = document.querySelectorAll('form');
      forms.forEach(form => {
        if (!form.querySelector('input[name="csrf_token"]')) {
          const input = document.createElement('input');
          input.type = 'hidden';
          input.name = 'csrf_token';
          input.value = this.token;
          form.appendChild(input);
        }
      });
    });
  }

  validateToken(token) {
    return token === this.token;
  }

  refreshToken() {
    this.token = this.generateToken();
    this.saveToken(this.token);
    return this.token;
  }
}

window.csrfProtection = new CSRFProtection();
[file content end]