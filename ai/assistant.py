import os
import requests

GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent"
)


def analyze_flight(metrics, gps_df=None, api_key=None):
    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        return (
            "API ключ Gemini не знайдено.\n"
            "Отримай безкоштовний ключ на https://aistudio.google.com/app/apikey\n"
            "і встав його в поле вище або в змінну середовища GEMINI_API_KEY."
        )

    anomalies = _detect_anomalies(gps_df) if gps_df is not None else []
    prompt = _build_prompt(metrics, anomalies)

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 1024,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }

    try:
        resp = requests.post(
            f"{GEMINI_API_URL}?key={key}",
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]

    except requests.HTTPError as e:
        if e.response.status_code == 400:
            return f"Невірний API ключ або запит.\nДеталі: {e.response.text[:300]}"
        if e.response.status_code == 429:
            return "Перевищено ліміт запитів Gemini. Спробуй через хвилину."
        return f"HTTP помилка {e.response.status_code}: {e.response.text[:300]}"

    except Exception as e:
        return f"Помилка з'єднання: {e}"


def _detect_anomalies(gps_df):
    import pandas as pd
    import numpy as np

    anomalies = []

    if 'Alt' in gps_df.columns and 'TimeUS' in gps_df.columns:
        alts  = pd.to_numeric(gps_df['Alt'],    errors='coerce').values
        times = pd.to_numeric(gps_df['TimeUS'], errors='coerce').values / 1e6

        for idx in range(1, len(alts)):
            dt = times[idx] - times[idx - 1]
            if dt <= 0:
                continue
            dalt = alts[idx] - alts[idx - 1]
            rate = dalt / dt

            t_sec = round(times[idx] - times[0], 1)

            if dalt < -5:
                anomalies.append(
                    f"Різка втрата висоти {dalt:.1f} м на {t_sec} с польоту "
                    f"(швидкість зниження {abs(rate):.1f} м/с)"
                )
            elif dalt > 5:
                anomalies.append(
                    f"Різкий набір висоти +{dalt:.1f} м на {t_sec} с польоту "
                    f"(швидкість підйому {rate:.1f} м/с)"
                )

    if 'Spd' in gps_df.columns:
        spds  = pd.to_numeric(gps_df['Spd'],    errors='coerce').values
        times = pd.to_numeric(gps_df['TimeUS'], errors='coerce').values / 1e6

        for idx, spd in enumerate(spds):
            if spd > 20:
                t_sec = round(times[idx] - times[0], 1)
                anomalies.append(f"Перевищення швидкості: {spd:.1f} м/с на {t_sec} с польоту")

    return anomalies[:10]


def _build_prompt(metrics, anomalies):
    metrics_text = "\n".join([
        f"- Загальна дистанція: {metrics.get('total_distance_m', 'н/д')} м",
        f"- Тривалість польоту: {metrics.get('total_duration_s', 'н/д')} с",
        f"- Максимальна горизонтальна швидкість: {metrics.get('max_horiz_speed_ms', 'н/д')} м/с",
        f"- Максимальна вертикальна швидкість: {metrics.get('max_vert_speed_ms', 'н/д')} м/с",
        f"- Максимальна висота: {metrics.get('max_alt_m', 'н/д')} м",
        f"- Висота старту: {metrics.get('start_alt_m', 'н/д')} м",
        f"- Набір висоти: {metrics.get('max_climb_rate', 'н/д')} м",
        f"- Максимальне прискорення: {metrics.get('max_acceleration', 'н/д')} м/с²",
    ])

    anomalies_text = (
        "\n".join(f"- {a}" for a in anomalies)
        if anomalies
        else "- Аномалій не виявлено"
    )

    return f"""Ти — система автоматичного аналізу телеметрії БПЛА.
Без привітань і звернень. Відповідай ТІЛЬКИ у форматі нижче, без відхилень.
Мова: українська. Стиль: технічний, лаконічний. Використовуй конкретні числа з даних.

ТЕЛЕМЕТРІЯ:
{metrics_text}

АНОМАЛІЇ:
{anomalies_text}

ФОРМАТ ВІДПОВІДІ (суворо дотримуйся):

## Статус місії
Одне речення: загальна оцінка (успішний / з відхиленнями / аварійний).

## Ключові показники
- Дистанція: ...
- Тривалість: ...
- Макс. швидкість: ... (оцінка: норма / підвищена / критична)
- Макс. висота: ...
- Набір висоти: ...
- Макс. прискорення: ... (оцінка: норма / підвищена / критична)

## Виявлені відхилення
Перелік конкретних проблем із цифрами. Якщо немає — написати "Відхилень не виявлено".

## Висновок
2-3 речення технічного підсумку та рекомендацій."""
