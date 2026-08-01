self.APP_VERSION = '20260801-1';

self.addEventListener('install', (event) => {
    event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
    event.waitUntil((async () => {
        await self.clients.claim();
        const windowClients = await self.clients.matchAll({
            type: 'window',
            includeUncontrolled: true,
        });

        await Promise.all(windowClients.map(async (client) => {
            if ('navigate' in client) {
                try {
                    await client.navigate(client.url);
                } catch (_err) {
                    // A closed or suspended client can be ignored.
                }
            }
        }));
    })());
});

self.addEventListener('push', (event) => {
    let payload = {
        title: '【ラ】ラーメン新店速報',
        body: '新しいお店が追加されました',
        url: '/',
    };

    if (event.data) {
        try {
            payload = { ...payload, ...event.data.json() };
        } catch (_err) {
            payload.body = event.data.text();
        }
    }

    const options = {
        body: payload.body,
        icon: payload.icon || '/static/icons/icon.svg',
        badge: payload.badge || payload.icon || '/static/icons/icon.svg',
        tag: payload.tag || `ramen-shinten-${Date.now()}`,
        renotify: true,
        requireInteraction: true,
        timestamp: Date.now(),
        vibrate: [200, 100, 200],
        data: {
            url: payload.url || '/',
        },
    };

    event.waitUntil(self.registration.showNotification(payload.title, options));
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const targetUrl = event.notification.data?.url || '/';

    event.waitUntil((async () => {
        const windowClients = await clients.matchAll({
            type: 'window',
            includeUncontrolled: true,
        });

        for (const client of windowClients) {
            if ('focus' in client) {
                await client.focus();
                if ('navigate' in client) {
                    return client.navigate(targetUrl);
                }
                return;
            }
        }

        if (clients.openWindow) {
            return clients.openWindow(targetUrl);
        }
    })());
});
