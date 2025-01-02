// static/script.js

if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/sw.js').then(function(registration) {
        console.log('Service Worker registrado con éxito:', registration);
    }).catch(function(error) {
        console.error('Fallo en el registro del Service Worker:', error);
    });
}
