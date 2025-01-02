// static/sw.js

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open('my-app-cache').then((cache) => {
            return cache.addAll([
                '/',
                '/templates/login.html',
                '/templates/register.html',
                '/templates/avance.html',
                '/templates/perfil.html',
                '/static/styles.css',
                '/static/script.js',
                '/static/assets/icon-192x192.png',
                '/static/assets/icon-512x512.png'
            ]);
        })
    );
});

self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request).then((cachedResponse) => {
            return cachedResponse || fetch(event.request);
        })
    );
});
