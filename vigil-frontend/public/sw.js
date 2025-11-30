const CACHE_NAME = "vigil-pwa-v3";

const ASSETS_TO_CACHE = [
  "/",
  "/index.html",
  "/manifest.webmanifest",
  "/camera_demo.jpg",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
];

// Install – cache core assets
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
  self.skipWaiting();
});

// Activate – clean old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      )
    )
  );
  self.clients.claim();
});

// Fetch – handle only same-origin http(s) GET requests, skip /api and extensions
self.addEventListener("fetch", (event) => {
  const request = event.request;

  if (request.method !== "GET") return;

  const url = new URL(request.url);

  // Only handle our own origin & http(s)
  if (url.origin !== self.location.origin) return;
  if (url.protocol !== "http:" && url.protocol !== "https:") return;

  // Never touch API calls
  if (url.pathname.startsWith("/api")) return;

  // Navigation requests: network-first, cache fallback
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // update cached index.html
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put("/", copy).catch(() => {});
          });
          return response;
        })
        .catch(() =>
          // offline or network failed → try cached index
          caches.match("/index.html")
        )
    );
    return;
  }

  // Static assets: cache-first, then network, only cache valid http responses
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;

      return fetch(request)
        .then((response) => {
          if (
            !response ||
            response.status !== 200 ||
            response.type !== "basic"
          ) {
            return response;
          }

          const respClone = response.clone();
          return caches
            .open(CACHE_NAME)
            .then((cache) =>
              cache.put(request, respClone).catch(() => {
                // ignore put errors (e.g. weird schemes)
              })
            )
            .then(() => response);
        })
        .catch(() => cached || null);
    })
  );
});

// Push notifications
self.addEventListener("push", (event) => {
  let data = {};
  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      console.error("Push data parse error", e);
    }
  }

  const title = data.title || "VIGIL Alert";
  const body = data.body || "";
  const url = data.url || "/";

  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      icon: "/icons/icon-192.png",
      data: { url },
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = event.notification.data && event.notification.data.url;

  event.waitUntil(
    clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((clientList) => {
        for (const client of clientList) {
          if ("focus" in client) {
            client.navigate(url || "/");
            return client.focus();
          }
        }
        if (clients.openWindow) {
          return clients.openWindow(url || "/");
        }
      })
  );
});
