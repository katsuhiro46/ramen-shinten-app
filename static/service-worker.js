self.addEventListener('install', (event) => {
    event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
    event.waitUntil(self.clients.claim());
});

self.addEventListener('push', (event) => {
    let payload = {
        title: 'ラーメン新店速報',
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
        icon: '/static/icons/icon.svg',
        badge: '/static/icons/icon.svg',
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
