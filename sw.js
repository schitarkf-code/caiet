/*
 * Service Worker-ul ramei „Caiet de ucenicie” (GitHub Pages).
 * Se trezește la fiecare notificare push trimisă de server (Push.gs). Push-ul nu are conținut: cerem starea de la
 * aplicație (doGet ?push=<hash-ul abonamentului>), afișăm notificarea și punem cifra pe iconiță.
 *   - iPhone / iPad (aplicația pe ecranul principal) și Windows / macOS: cifră pe iconiță (setAppBadge);
 *   - Android: sistemul pune bulina pe iconiță cât timp notificarea nu e citită.
 * Fiecare push TREBUIE să afișeze o notificare (cerința Safari și Chrome), chiar dacă starea nu a putut fi citită.
 * Adresa aplicației vine din parametrul ?app= al înregistrării (index.html), ca să o scrieți într-un singur loc.
 */
'use strict';
var APP_URL = new URL(self.location.href).searchParams.get('app') || '';
var TAG = 'caiet';

self.addEventListener('install', function () { self.skipWaiting(); });
self.addEventListener('activate', function (e) { e.waitUntil(self.clients.claim()); });

function hex(buf) { return Array.prototype.map.call(new Uint8Array(buf), function (b) { return ('0' + b.toString(16)).slice(-2); }).join(''); }

/** Cheia dispozitivului = SHA-256 al adresei de abonare (aceeași regulă ca pe server). */
function deviceKey() {
  return self.registration.pushManager.getSubscription().then(function (sub) {
    if (!sub) return '';
    return crypto.subtle.digest('SHA-256', new TextEncoder().encode(sub.endpoint)).then(hex);
  });
}

function fetchState() {
  return deviceKey().then(function (k) {
    if (!k || !APP_URL) return null;
    var ctrl = new AbortController();
    var t = setTimeout(function () { ctrl.abort(); }, 9000);
    return fetch(APP_URL + '?push=' + k, { cache: 'no-store', credentials: 'omit', redirect: 'follow', signal: ctrl.signal })
      .then(function (r) { clearTimeout(t); return r.ok ? r.json() : null; })
      .catch(function () { clearTimeout(t); return null; });
  });
}

function setBadge(n) {
  if (!('setAppBadge' in self.navigator)) return Promise.resolve();
  var p = n > 0 ? self.navigator.setAppBadge(n) : n === 0 ? self.navigator.clearAppBadge() : self.navigator.setAppBadge();
  return p.catch(function () { /* fără cifră pe acest sistem */ });
}

self.addEventListener('push', function (e) {
  e.waitUntil(fetchState().then(function (st) {
    var ok = !!(st && st.ok);
    var n = ok ? Math.max(0, Math.min(99999, Number(st.n) || 0)) : null;
    var title = ok && st.titlu ? String(st.titlu).slice(0, 80) : 'Caiet de ucenicie';
    var body = ok && st.text ? String(st.text).slice(0, 240) : 'Ai noutăți. Deschide aplicația ca să le vezi.';
    // dispozitivul nu mai e legat de un cont (ieșire din cont): nu mai punem cifră
    var badge = st && st.sters ? setBadge(0) : setBadge(n);
    return badge.then(function () {
      return self.registration.showNotification(title, {
        body: body, tag: TAG, renotify: true,
        icon: 'icon-192.png', badge: 'badge-96.png',
        requireInteraction: !!(ok && st.urgent),
        data: { url: self.registration.scope }
      });
    });
  }));
});

self.addEventListener('notificationclick', function (e) {
  e.notification.close();
  var url = (e.notification.data && e.notification.data.url) || self.registration.scope;
  e.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (list) {
    for (var i = 0; i < list.length; i++) {
      if (list[i].url.indexOf(self.registration.scope) === 0 && 'focus' in list[i]) return list[i].focus();
    }
    return self.clients.openWindow ? self.clients.openWindow(url) : null;
  }));
});

/* Abonamentul a fost reînnoit de browser: pagina îl trimite serverului la următoarea deschidere a aplicației. */
self.addEventListener('pushsubscriptionchange', function (e) {
  var opts = e.oldSubscription && e.oldSubscription.options;
  if (!opts) return;
  e.waitUntil(self.registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: opts.applicationServerKey }).catch(function () {}));
});
