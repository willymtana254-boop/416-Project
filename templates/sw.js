/* MediTECH AI service worker. Served by pwa.py at /sw.js, which fills in the
 * version and the list of files to cache. Do not edit the two placeholders.
 *
 * What it does
 *   - Caches the app shell (page, scripts, styles, fonts, icons) when it
 *     installs, so the app opens with no connection.
 *   - Serves the shell from the cache first. Every file in the cache belongs
 *     to one version, so the page and its scripts always match.
 *   - Waits for the page to ask before replacing the running version, so an
 *     update never swaps the app under a patient in the middle of an assessment.
 *
 * What it never does
 *   - It never touches /api/. Assessments, sign-in, saved history and
 *     facility searches always go straight to the network and are never stored
 *     by this worker.
 *   - It ignores other websites and every request that is not a plain GET.
 */
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
