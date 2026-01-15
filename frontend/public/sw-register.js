// Регистрация Service Worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', function() {
    navigator.serviceWorker.register('service-worker.js')
      .then(function(registration) {
        console.log('Service Worker зарегистрирован: ', registration.scope);
      })
      .catch(function(err) {
        console.log('Ошибка регистрации: ', err);
      });
  });
} else {
  console.log('Service Worker не поддерживается');
}