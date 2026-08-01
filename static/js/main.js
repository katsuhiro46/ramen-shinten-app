document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('accordion-container');
    const loading = document.getElementById('loading');
    const newShopSection = document.getElementById('new-shop-section');
    const newShopList = document.getElementById('new-shop-list');
    const newShopCount = document.getElementById('new-shop-count');
    const pushPanel = document.getElementById('push-panel');
    const pushToggle = document.getElementById('push-toggle');
    const pushStatus = document.getElementById('push-status');

    // 県別カラー設定
    const PREF_CONFIG = {
        '群馬': { code: 'gunma', color: '#E60012', emoji: '🔴' },
        '栃木': { code: 'tochigi', color: '#0066CC', emoji: '🔵' },
        '茨城': { code: 'ibaraki', color: '#228B22', emoji: '🟢' },
        '埼玉': { code: 'saitama', color: '#FFD700', emoji: '🟡' },
    };

    // 県の表示順
    const PREF_ORDER = ['群馬', '栃木', '茨城', '埼玉'];

    async function fetchAndRender() {
        try {
            const response = await fetch('/api/news');
            const data = await response.json();

            if (!response.ok || data.status === 'error') {
                throw new Error(data.message || 'API request failed');
            }

            if (!data.shops || data.shops.length === 0) {
                loading.innerHTML = '<p class="error-msg">データ取得に失敗しました</p>';
                return;
            }

            const additionEvents = normalizeAdditionEvents(data.addition_events);
            const highlightedEvents = selectHighlightedEvents(additionEvents);
            const highlightedShops = collectEventShops(highlightedEvents);
            const highlightedKeys = new Set(highlightedShops.map(shopKey));

            // 県別にグループ化
            const grouped = {};
            PREF_ORDER.forEach(pref => { grouped[pref] = []; });
            data.shops.forEach(shop => {
                if (grouped[shop.area]) {
                    grouped[shop.area].push(shop);
                }
            });

            loading.classList.add('hidden');
            renderNewShopSection(highlightedShops);

            // アコーディオン生成
            PREF_ORDER.forEach(pref => {
                const shops = [...grouped[pref]].sort((left, right) => {
                    return Number(highlightedKeys.has(shopKey(right)))
                        - Number(highlightedKeys.has(shopKey(left)));
                });
                const config = PREF_CONFIG[pref];
                const section = createAccordion(pref, shops, config, highlightedKeys);
                container.appendChild(section);
            });

        } catch (err) {
            console.error('Fetch error:', err);
            loading.innerHTML = '<p class="error-msg">データ取得に失敗しました</p>';
        }
    }

    function normalizeAdditionEvents(events) {
        if (!Array.isArray(events)) {
            return [];
        }

        return events.filter(event => (
            event
            && typeof event.id === 'string'
            && Array.isArray(event.shops)
            && event.shops.length > 0
        ));
    }

    function selectHighlightedEvents(events) {
        const requestedEventId = new URLSearchParams(window.location.search).get('new');
        if (requestedEventId) {
            const requestedEvent = events.find(event => event.id === requestedEventId);
            return requestedEvent ? [requestedEvent] : [];
        }

        return events.length > 0 ? [events[events.length - 1]] : [];
    }

    function collectEventShops(events) {
        const shops = [];
        const collectedKeys = new Set();

        events.forEach(event => {
            event.shops.forEach(shop => {
                const key = shopKey(shop);
                if (!collectedKeys.has(key)) {
                    shops.push(shop);
                    collectedKeys.add(key);
                }
            });
        });

        return shops;
    }

    function renderNewShopSection(shops) {
        if (shops.length === 0 || !newShopSection || !newShopList || !newShopCount) {
            return;
        }

        shops.forEach(shop => {
            const config = PREF_CONFIG[shop.area] || {};
            newShopList.appendChild(createShopItem(shop, config, true));
        });
        newShopCount.textContent = `${shops.length}件`;
        newShopSection.classList.remove('hidden');
    }

    function createAccordion(prefName, shops, config, highlightedKeys) {
        const section = document.createElement('div');
        section.className = 'accordion';
        const highlightedCount = shops.filter(shop => highlightedKeys.has(shopKey(shop))).length;
        if (highlightedCount > 0) {
            section.classList.add('open', 'has-new');
        }

        const button = document.createElement('button');
        button.className = 'accordion-btn';
        button.type = 'button';
        button.setAttribute('aria-expanded', highlightedCount > 0 ? 'true' : 'false');
        button.style.borderLeftColor = config.color;
        button.innerHTML = `
            <span class="pref-label">
                <span class="pref-emoji">${config.emoji}</span>
                <span class="pref-name">${prefName}</span>
                <span class="shop-count">${shops.length}件</span>
                ${highlightedCount > 0 ? `<span class="accordion-new-count">NEW ${highlightedCount}</span>` : ''}
            </span>
            <span class="arrow">▼</span>
        `;

        const panel = document.createElement('div');
        panel.className = 'accordion-panel';

        if (shops.length === 0) {
            panel.innerHTML = '<p class="no-data">新店情報なし</p>';
        } else {
            const ul = document.createElement('ul');
            ul.className = 'shop-list';
            shops.forEach(shop => {
                ul.appendChild(createShopItem(shop, config, highlightedKeys.has(shopKey(shop))));
            });
            panel.appendChild(ul);
        }

        button.addEventListener('click', () => {
            const isOpen = section.classList.toggle('open');
            button.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        });

        section.appendChild(button);
        section.appendChild(panel);
        return section;
    }

    function createShopItem(shop, config, isNew = false) {
        const li = document.createElement('li');
        li.className = isNew ? 'shop-item is-new' : 'shop-item';
        li.style.setProperty('--pref-color', config.color || '#FFD700');

        const meta = [
            shop.city,
            shop.open_date,
            shop.point ? `${shop.point}ポイント` : '',
            Number.isInteger(shop.review_count) ? `${shop.review_count}レビュー` : '',
        ].filter(Boolean).join(' ｜ ');
        const name = escapeHtml(shop.name || '店名不明');
        const url = escapeHtml(safeShopUrl(shop.url));

        li.innerHTML = `
            <div class="shop-row">
                <a href="${url}" target="_blank" rel="noopener" class="shop-link">
                    <span class="shop-name">${name}</span>
                    ${isNew ? '<span class="new-badge">NEW</span>' : ''}
                </a>
                <button class="navi-btn" type="button" aria-label="${name}を地図で開く">📍</button>
            </div>
            ${meta ? `<div class="shop-meta">${escapeHtml(meta)}</div>` : ''}
        `;

        // ナビボタン
        li.querySelector('.navi-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            const q = encodeURIComponent(`${shop.name} ${shop.city || ''}`);
            window.open(`https://www.google.com/maps/search/?api=1&query=${q}`, '_blank', 'noopener');
        });

        return li;
    }

    function shopKey(shop) {
        return shop.url || `${shop.area || ''}:${shop.name || ''}:${shop.city || ''}`;
    }

    function safeShopUrl(value) {
        try {
            const url = new URL(value, window.location.origin);
            return ['http:', 'https:'].includes(url.protocol) ? url.href : '#';
        } catch (_err) {
            return '#';
        }
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // 起動
    fetchAndRender();
    initPushNotifications();

    async function initPushNotifications() {
        if (!pushPanel || !pushToggle || !pushStatus) {
            return;
        }

        if (!('serviceWorker' in navigator) || !('PushManager' in window) || !('Notification' in window)) {
            return;
        }

        try {
            const configResponse = await fetch('/api/push/config');
            const config = await configResponse.json();
            if (!config.enabled || !config.publicKey) {
                return;
            }

            pushPanel.classList.remove('hidden');
            const registration = await navigator.serviceWorker.register(
                '/service-worker.js?v=20260801-1',
                { updateViaCache: 'none' }
            );
            const subscription = await registration.pushManager.getSubscription();
            updatePushButton(subscription);

            pushToggle.addEventListener('click', async () => {
                pushToggle.disabled = true;
                try {
                    const currentSubscription = await registration.pushManager.getSubscription();
                    if (currentSubscription) {
                        await unsubscribePush(currentSubscription);
                        updatePushButton(null);
                        return;
                    }

                    const permission = await Notification.requestPermission();
                    if (permission !== 'granted') {
                        pushStatus.textContent = '通知が許可されませんでした';
                        updatePushButton(null);
                        return;
                    }

                    const newSubscription = await registration.pushManager.subscribe({
                        userVisibleOnly: true,
                        applicationServerKey: urlBase64ToUint8Array(config.publicKey),
                    });
                    await subscribePush(newSubscription);
                    updatePushButton(newSubscription);
                } catch (err) {
                    console.error('Push error:', err);
                    pushStatus.textContent = '通知設定に失敗しました';
                } finally {
                    pushToggle.disabled = false;
                }
            });
        } catch (err) {
            console.error('Push init error:', err);
        }
    }

    function updatePushButton(subscription) {
        if (subscription) {
            pushToggle.textContent = '新店通知を停止する';
            pushStatus.textContent = '新しいお店が追加されたら通知します';
        } else {
            pushToggle.textContent = '新店通知を受け取る';
            pushStatus.textContent = 'スマホ通知で新店追加をお知らせします';
        }
        pushToggle.disabled = false;
    }

    async function subscribePush(subscription) {
        const response = await fetch('/api/push/subscribe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(subscription),
        });

        if (!response.ok) {
            throw new Error('Subscribe failed');
        }
    }

    async function unsubscribePush(subscription) {
        await fetch('/api/push/unsubscribe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(subscription),
        });
        await subscription.unsubscribe();
    }

    function urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);

        for (let i = 0; i < rawData.length; i++) {
            outputArray[i] = rawData.charCodeAt(i);
        }

        return outputArray;
    }
});
