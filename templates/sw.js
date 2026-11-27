const VERSION = "__VERSION__";
const PREFIX = "meditech-shell-";
const CACHE = PREFIX + VERSION;
const PRECACHE = __PRECACHE__;

self.addEventListener("install", (event) => {
  // "reload" skips the browser's HTTP cache so the stored copy is the server's current one.
  // addAll rejects if any file fails, which leaves the previous version in charge.
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(PRECACHE.map((url) => new Request(url, { cache: "reload" }))))
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const names = await caches.keys();
      await Promise.all(names.filter((n) => n.startsWith(PREFIX) && n !== CACHE).map((n) => caches.delete(n)));
      await self.clients.claim();
    })()
  );
});

self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") self.skipWaiting();
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/") || url.pathname === "/sw.js") return;

  if (req.mode === "navigate") {
    // The app is one page. "/?view=emergency" and the like are the same page.
    if (url.pathname === "/") event.respondWith(fromCache("/", req));
    return;
  }
  event.respondWith(fromCache(req, req));
});

async function fromCache(key, req) {
  const hit = await caches.match(key, { cacheName: CACHE });
  if (hit) return hit;
  try {
    return await fetch(req);
  } catch (err) {
    return Response.error();
  }
}
