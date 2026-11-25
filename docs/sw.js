const CACHE='darkith-reader-v2';
const SHELL=['./','./index.html','./README.md'];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL)).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{
  const request=event.request;
  if(request.method!=='GET'||new URL(request.url).origin!==self.location.origin)return;
  const isDocument=request.mode==='navigate'||request.destination==='document';
  event.respondWith((async()=>{
    const cache=await caches.open(CACHE);
    try{
      const response=await fetch(request);
      if(response.ok)await cache.put(request,response.clone());
      return response;
    }catch(error){
      const cached=await cache.match(request)||await cache.match('./index.html');
      if(cached)return cached;
      if(isDocument)return new Response('Darkith Reader is offline and no cached page is available yet. Connect once to load the reader and canonical README.',{status:503,headers:{'Content-Type':'text/plain; charset=utf-8'}});
      throw error;
    }
  })());
});