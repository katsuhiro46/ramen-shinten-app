document.addEventListener('DOMContentLoaded', () => {
    const loading = document.getElementById('weather-loading');
    const card = document.getElementById('weather-card');
    const subtitle = document.getElementById('weather-subtitle');
    const date = document.getElementById('weather-date');
    const title = document.getElementById('weather-title');
    const list = document.getElementById('weather-list');
    const attention = document.getElementById('weather-attention');

    fetchWeather();

    async function fetchWeather() {
        try {
            const response = await fetch('/api/weather');
            const data = await response.json();

            if (!response.ok || data.status === 'error') {
                throw new Error(data.message || 'Weather API request failed');
            }

            renderWeather(data.weather);
        } catch (err) {
            console.error('Weather fetch error:', err);
            loading.innerHTML = '<p class="error-msg">天気取得に失敗しました</p>';
        }
    }

    function renderWeather(weather) {
        const route = weather.route.join('・');
        subtitle.textContent = `${weather.weekday_name}ルート`;
        date.textContent = formatDate(weather.target_date);
        title.textContent = `${weather.weekday_label}／${route}`;

        list.innerHTML = '';
        weather.forecasts.forEach(item => {
            const row = document.createElement('article');
            row.className = 'weather-row';
            row.innerHTML = `
                <div>
                    <h3>${item.name}</h3>
                    <p>${item.full_name}</p>
                </div>
                <div class="weather-values">
                    <strong>${item.weather_icon}${item.weather_label}</strong>
                    <span>${item.max_temp}/${item.min_temp}℃</span>
                    <span>降水${item.precipitation}%</span>
                    <span>風${Math.round(item.wind)}m/s</span>
                </div>
            `;
            list.appendChild(row);
        });

        if (weather.attention) {
            attention.textContent = weather.attention;
            attention.classList.remove('hidden');
        } else {
            attention.classList.add('hidden');
        }

        loading.classList.add('hidden');
        card.classList.remove('hidden');
    }

    function formatDate(value) {
        const parsed = new Date(`${value}T00:00:00+09:00`);
        return parsed.toLocaleDateString('ja-JP', {
            month: 'numeric',
            day: 'numeric',
            weekday: 'long',
        });
    }
});
