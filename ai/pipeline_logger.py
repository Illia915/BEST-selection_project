import os
import json
import datetime


_STORAGE = os.getenv("LOG_STORAGE", "local").lower()
_LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
_MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
_MONGO_DB = os.getenv("MONGO_DB", "uav_telemetry")


def log_pipeline(
    model: str,
    prompt: str,
    response: str,
    metrics: dict,
    prompt_tokens: int,
    completion_tokens: int,
    duration_s: float,
    filename: str = "",
):
    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "filename": filename,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "duration_s": round(duration_s, 3),
        "metrics_snapshot": metrics,
        "prompt": prompt,
        "response": response,
    }

    if _STORAGE == "mongodb":
        _log_to_mongo(entry)
    else:
        _log_to_file(entry)


def _log_to_file(entry: dict):
    os.makedirs(_LOG_DIR, exist_ok=True)
    date_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    path = os.path.join(_LOG_DIR, f"ai_pipeline_{date_str}.json")

    records = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                records = json.load(f)
        except (json.JSONDecodeError, IOError):
            records = []

    records.append(entry)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def _log_to_mongo(entry: dict):
    try:
        from pymongo import MongoClient
        client = MongoClient(_MONGO_URI, serverSelectionTimeoutMS=3000)
        db = client[_MONGO_DB]
        db["ai_pipeline"].insert_one(entry)
        client.close()
    except Exception as e:
        _log_to_file(entry)
