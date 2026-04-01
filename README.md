# UAV Telemetry Analyzer

Веб-застосунок для аналізу бінарних лог-файлів польотних контролерів Ardupilot з 3D-візуалізацією траєкторії та AI-аналізом польоту.

## Стек технологій

| Бібліотека | Призначення |
|---|---|
| **pymavlink** | Офіційна бібліотека Ardupilot для читання бінарного формату DataFlash (.BIN) |
| **pandas / numpy** | Структуровані масиви даних і векторні обчислення метрик |
| **plotly** | Інтерактивна 3D-візуалізація траєкторії з colormap |
| **folium** | 2D-карта на базі Leaflet.js без API ключа |
| **streamlit** | Веб-інтерфейс на Python без фронтенду |
| **Google Gemini 2.5 Flash** | Безкоштовний LLM для автоматичного аналізу польоту |
| **requests** | HTTP-клієнт для Gemini API |
| **pymongo** | Зберігання AI pipeline логів у MongoDB |

## Запуск

### Локально

```bash
git clone https://github.com/Illia915/BEST-selection_project.git
cd BEST-selection_project
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

Відкриється браузер за адресою `http://localhost:8501`

### Docker (з MongoDB)

```bash
cp .env.example .env
docker-compose up --build
```

Відкрити `http://localhost:8501`

## Конфігурація

Скопіюй `.env.example` → `.env` і заповни:

```env
GEMINI_API_KEY=AIza...         # ключ з aistudio.google.com
GEMINI_MODEL=gemini-2.5-flash  # модель за замовчуванням
LOG_AI_PIPELINE=true           # логувати AI запити
LOG_STORAGE=local              # local або mongodb
MONGO_URI=mongodb://localhost:27017
MONGO_DB=uav_telemetry
```

## Структура проекту

```
uav-telemetry-analyzer/
├── app.py                      # Streamlit веб-інтерфейс
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── data/
│   ├── 00000001.BIN
│   └── 00000019.BIN
├── scraper/
│   └── dataflash.py            # Парсинг бінарних логів Ardupilot
├── analytics/
│   ├── metrics.py              # Haversine, трапецієвидне інтегрування, метрики
│   └── coords.py               # WGS-84 → ECEF → ENU перетворення
├── visualization/
│   ├── plot3d.py               # 3D-траєкторія (Plotly)
│   └── map_view.py             # 2D-карта (Folium / Leaflet)
├── ai/
│   ├── assistant.py            # AI-аналіз, A/B порівняння моделей
│   ├── prompts.py              # Промпти для Gemini
│   ├── token_counter.py        # Лічильник токенів за сесію
│   └── pipeline_logger.py      # Логування AI pipeline (JSON / MongoDB)
├── logs/                       # Локальні JSON логи (git ignored)
└── tests/
    ├── test_parser.py
    └── test_mavlink.py
```

## Функціональність

### MVP
- Парсинг бінарних .BIN логів Ardupilot через pymavlink
- Витяг GPS та IMU даних у pandas DataFrame з фільтрацією GPS-шуму
- Метрики польоту: дистанція (**haversine**), швидкість, висота, прискорення (95-й перцентиль IMU), тривалість, швидкість з IMU (**трапецієвидне інтегрування**)
- 3D-траєкторія з конвертацією **WGS-84 → ECEF → ENU**, кольорування за швидкістю або часом

### Nice-to-have
- Інтерактивний веб-дашборд (Streamlit) з завантаженням файлу
- 2D-карта (Folium / OpenStreetMap, без API ключа)
- AI-аналіз через **Google Gemini 2.5 Flash** зі структурованим технічним висновком
- **A/B порівняння моделей** — запустити кілька Gemini моделей паралельно та порівняти відповіді
- **Лічильник токенів** — відображення використаних токенів за сесію
- **Логування AI pipeline** — кожен запит зберігається в JSON або MongoDB з промптом, відповіддю, метриками та кількістю токенів
- **Docker Compose** з MongoDB для persistentного зберігання логів

## AI-аналіз

Безкоштовний ключ: [aistudio.google.com](https://aistudio.google.com/app/apikey)

Підтримувані моделі:
- `gemini-2.5-flash` — рекомендовано
- `gemini-2.5-flash-lite` — швидший
- `gemini-2.5-pro` — точніший

## Тести

```bash
python tests/test_parser.py
python tests/test_mavlink.py
```
