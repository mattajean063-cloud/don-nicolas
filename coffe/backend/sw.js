self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('message', (event) => {
  if (!event.data || event.data.type !== 'FLASH_NOTIFY') return;

  const { title, body } = event.data;

  self.registration.showNotification(title || 'Don Nicolás', {
    body: body || 'Nueva actualización',
    icon: '/favicon.ico',
    badge: '/favicon.ico',
    vibrate: [180, 80, 180],
    tag: 'don-nicolas-flash',
    requireInteraction: true
  });
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      if (clientList.length > 0) {
        const client = clientList[0];
        return client.focus();
      }
      return clients.openWindow('/admin');
    })
  );
});
