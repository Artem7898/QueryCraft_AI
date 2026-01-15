[file name]: service-worker.js
[file content begin]
const CACHE_NAME = 'querycraft-v2';

self.addEventListener('install', (event) => {
  console.log('Service Worker установлен');
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
  console.log('Service Worker активирован');
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        if (response) {
          return response;
        }
        return fetch(event.request);
      })
  );
});
[file content end]