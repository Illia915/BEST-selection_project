import pandas as pd

SYSTEM_PROMPT = """Ти — система автоматичного аналізу телеметрії БПЛА.
Без привітань і звернень. Відповідай ТІЛЬКИ у форматі нижче, без відхилень.
Мова: українська. Стиль: технічний, лаконічний. Використовуй конкретні числа з даних."""

def detect_anomalies(gps_df):
    anomalies = []
    if gps_df is None or len(gps_df) < 2: return anomalies
    
    spd = pd.to_numeric(gps_df['Spd'], errors='coerce')
    if spd.max() > 20: anomalies.append(f"Перевищення швидкості: {spd.max():.1f} м/с")
    
    alt = pd.to_numeric(gps_df['Alt'], errors='coerce')
    alt_diff = alt.diff().dropna()
    if alt_diff.min() < -5: anomalies.append(f"Різке падіння висоти: {alt_diff.min():.1f} м/с")
    if alt_diff.max() > 5: anomalies.append(f"Різкий набір висоти: {alt_diff.max():.1f} м/с")
    
    return anomalies[:10]

def get_flight_report_prompt(metrics, gps_df):
    anomalies = detect_anomalies(gps_df)
    m_text = "\n".join([f"- {k}: {v}" for k, v in metrics.items()])
    a_text = "\n".join([f"- {a}" for a in anomalies]) if anomalies else "- Відхилень не виявлено"
    
    return f"""ТЕЛЕМЕТРІЯ:
{m_text}

АНОМАЛІЇ:
{a_text}

ФОРМАТ ВІДПОВІДІ:
## Статус місії
...
## Ключові показники
...
## Виявлені відхилення
...
## Висновок
..."""
