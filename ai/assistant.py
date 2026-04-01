import os
import time
import requests

from ai.prompts import build_analysis_prompt
from ai.token_counter import estimate_tokens, record_usage
from ai.pipeline_logger import log_pipeline

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

AVAILABLE_MODELS = {
    "gemini-2.5-flash": "Gemini 2.5 Flash (рекомендовано)",
    "gemini-2.5-flash-lite": "Gemini 2.5 Flash Lite (швидший)",
    "gemini-2.5-pro": "Gemini 2.5 Pro (точніший)",
}

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def analyze_flight(metrics: dict, gps_df=None, api_key: str = "", model: str = "") -> dict:
    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        return {
            "text": (
                "API ключ Gemini не знайдено.\n"
                "Отримай безкоштовний ключ на https://aistudio.google.com/app/apikey"
            ),
            "model": model or DEFAULT_MODEL,
            "prompt_tokens": 0,
            "completion_tokens": 0,
        }

    used_model = model or DEFAULT_MODEL
    anomalies = _detect_anomalies(gps_df) if gps_df is not None else []
    prompt = build_analysis_prompt(metrics, anomalies)

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 1024,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }

    t0 = time.time()
    try:
        resp = requests.post(
            f"{GEMINI_BASE_URL}/{used_model}:generateContent?key={key}",
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        response_text = data["candidates"][0]["content"]["parts"][0]["text"]

        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", estimate_tokens(prompt))
        completion_tokens = usage.get("candidatesTokenCount", estimate_tokens(response_text))

    except requests.HTTPError as e:
        if e.response.status_code == 400:
            response_text = f"Невірний API ключ або запит.\n{e.response.text[:300]}"
        elif e.response.status_code == 429:
            response_text = "Перевищено ліміт запитів Gemini. Спробуй через хвилину."
        else:
            response_text = f"HTTP помилка {e.response.status_code}: {e.response.text[:300]}"
        prompt_tokens = estimate_tokens(prompt)
        completion_tokens = 0

    except Exception as e:
        response_text = f"Помилка з'єднання: {e}"
        prompt_tokens = estimate_tokens(prompt)
        completion_tokens = 0

    duration = time.time() - t0
    record_usage(prompt_tokens, completion_tokens)

    if os.getenv("LOG_AI_PIPELINE", "true").lower() == "true":
        log_pipeline(
            model=used_model,
            prompt=prompt,
            response=response_text,
            metrics=metrics,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            duration_s=duration,
        )

    return {
        "text": response_text,
        "model": used_model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
    }


def analyze_flight_ab(metrics: dict, gps_df=None, api_key: str = "", models: list = None) -> list[dict]:
    if not models:
        models = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
    return [analyze_flight(metrics, gps_df, api_key, m) for m in models]


def _detect_anomalies(gps_df) -> list[str]:
    import pandas as pd

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
