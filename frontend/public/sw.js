// Service Worker for Institutional Offline-First Application Shell
const CACHE_NAME = "placement-engine-cache-v7";
const PRECACHE_URLS = [
  "/",
  "/index.html",
  "/sw.js",
  "/favicon.ico"
];

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_URLS).catch(() => {});
    })
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  // Pass non-GET and API requests directly to local backend
  if (event.request.method !== "GET" || event.request.url.includes("/api/")) {
    return;
  }

  // Network-first strategy for documents and assets to guarantee fresh UI updates
  event.respondWith(
    fetch(event.request)
      .then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const clone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return networkResponse;
      })
      .catch(() => {
        return caches.match(event.request).then((cached) => {
          if (cached) return cached;
          if (event.request.mode === "navigate" || event.request.destination === "document") {
            return caches.match("/index.html");
          }
          return new Response("Offline resource unavailable", { status: 503 });
        });
      })
  );
});
