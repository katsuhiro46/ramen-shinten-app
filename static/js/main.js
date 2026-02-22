document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('accordion-container');
    const loading = document.getElementById('loading');

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

            if (!data.shops || data.shops.length === 0) {
                loading.innerHTML = '<p class="error-msg">新店情報がありません</p>';
                return;
            }

            // 県別にグループ化
            const grouped = {};
            PREF_ORDER.forEach(pref => { grouped[pref] = []; });
            data.shops.forEach(shop => {
                if (grouped[shop.area]) {
                    grouped[shop.area].push(shop);
                }
            });

            loading.classList.add('hidden');

            // アコーディオン生成
            PREF_ORDER.forEach(pref => {
                const shops = grouped[pref];
                const config = PREF_CONFIG[pref];
                const section = createAccordion(pref, shops, config);
                container.appendChild(section);
            });

        } catch (err) {
            console.error('Fetch error:', err);
            loading.innerHTML = '<p class="error-msg">データの取得に失敗しました</p>';
        }
    }

    function createAccordion(prefName, shops, config) {
        const section = document.createElement('div');
        section.className = 'accordion';

        const button = document.createElement('button');
        button.className = 'accordion-btn';
        button.style.borderLeftColor = config.color;
        button.innerHTML = `
            <span class="pref-label">
                <span class="pref-emoji">${config.emoji}</span>
                <span class="pref-name">${prefName}</span>
                <span class="shop-count">${shops.length}件</span>
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
                ul.appendChild(createShopItem(shop, config));
            });
            panel.appendChild(ul);
        }

        button.addEventListener('click', () => {
            const isOpen = section.classList.toggle('open');
            button.querySelector('.arrow').textContent = isOpen ? '▲' : '▼';
        });

        section.appendChild(button);
        section.appendChild(panel);
        return section;
    }

    function createShopItem(shop, config) {
        const li = document.createElement('li');
        li.className = 'shop-item';

        const meta = [shop.city, shop.open_date].filter(Boolean).join(' ｜ ');

        li.innerHTML = `
            <div class="shop-row">
                <a href="${shop.url}" target="_blank" class="shop-link">${shop.name}</a>
                <button class="navi-btn" aria-label="ナビ">📍</button>
            </div>
            ${meta ? `<div class="shop-meta">${meta}</div>` : ''}
        `;

        // ナビボタン
        li.querySelector('.navi-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            const q = encodeURIComponent(`${shop.name} ${shop.city || ''}`);
            window.open(`https://www.google.com/maps/search/?api=1&query=${q}`, '_blank');
        });

        return li;
    }

    // 起動
    fetchAndRender();
});
