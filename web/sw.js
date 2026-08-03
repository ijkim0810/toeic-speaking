const CACHE = "toeic-shadow-v1";
// 앱 셸만 미리 캐시. manifest.json/audio는 런타임에 채운다.
const CORE = ["./", "player-core.js", "manifest.webmanifest", "icon.svg"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(CORE)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) =>
    Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
  ).then(() => self.clients.claim()));
});

// 콘텐츠 해시가 붙는 audio/*.mp3 만 cache-first (내용 바뀌면 파일명이 바뀜 → 안전).
// index.html·player-core.js·manifest.json 등 가변 파일은 network-first:
// generate.py 재실행으로 문장/음성이 바뀌면 즉시 반영되고, 오프라인일 때만 캐시로 폴백.
self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  const isAudio = e.request.url.includes("/audio/");
  if (isAudio) {
    e.respondWith(
      caches.match(e.request).then((hit) =>
        hit || fetch(e.request).then((resp) => {
          const copy = resp.clone();
          caches.open(CACHE).then((c) => c.put(e.request, copy));
          return resp;
        })
      )
    );
  } else {
    e.respondWith(
      fetch(e.request, { cache: "no-store" }).then((resp) => {
        const copy = resp.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy));
        return resp;
      }).catch(() => caches.match(e.request))
    );
  }
});
