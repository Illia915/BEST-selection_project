"""
Скрипт для перевірки парсера без запуску Streamlit.
Запускається звичайним чином: python test_parser.py
"""
import os
from parser.dataflash import parse_log, get_gps_dataframe, get_imu_dataframe
from analytics.metrics import compute_metrics
from analytics.coords import gps_to_enu

# ── Шлях до файлу ─────────────────────────────────────────────────────────────
# Змінити на 00000001.BIN або 00000019.BIN
LOG_FILE = os.path.join('data', '00000001.BIN')

if not os.path.exists(LOG_FILE):
    print(f'❌ Файл не знайдено: {LOG_FILE}')
    print('   Поклади .BIN файли у папку data/')
    exit(1)

# ── Парсинг ───────────────────────────────────────────────────────────────────
print(f'📂 Парсинг: {LOG_FILE}')
dataframes = parse_log(LOG_FILE)

print(f'\n✅ Знайдено {len(dataframes)} типів повідомлень:')
for name, df in sorted(dataframes.items()):
    print(f'   {name:8s} — {len(df):5d} рядків  |  колонки: {list(df.columns)[:6]}...')

# ── GPS ───────────────────────────────────────────────────────────────────────
print('\n── GPS ──────────────────────────────────────────────────')
gps_df = get_gps_dataframe(dataframes)

if gps_df is None:
    print('❌ GPS-даних не знайдено')
    print('   Доступні повідомлення:', list(dataframes.keys()))
else:
    print(f'✅ GPS: {len(gps_df)} точок')
    print(gps_df[['Lat', 'Lng', 'Alt'] + 
                  ([col] for col in ['Spd', 'TimeUS'] if col in gps_df.columns)
                  ].head(5) if False else gps_df.head(5))

    # ── ENU ───────────────────────────────────────────────────────────────
    print('\n── ENU конвертація ─────────────────────────────────────')
    gps_enu = gps_to_enu(gps_df)
    print(f'✅ Діапазон E: {gps_enu["E_m"].min():.1f} .. {gps_enu["E_m"].max():.1f} м')
    print(f'   Діапазон N: {gps_enu["N_m"].min():.1f} .. {gps_enu["N_m"].max():.1f} м')
    print(f'   Діапазон U: {gps_enu["U_m"].min():.1f} .. {gps_enu["U_m"].max():.1f} м')

    # ── Метрики ───────────────────────────────────────────────────────────
    print('\n── Метрики польоту ─────────────────────────────────────')
    imu_df  = get_imu_dataframe(dataframes)
    metrics = compute_metrics(gps_df, imu_df)

    for key, val in metrics.items():
        unit = {
            'total_distance_m':   'м',
            'max_horiz_speed_ms': 'м/с',
            'max_vert_speed_ms':  'м/с',
            'max_acceleration':   'м/с²',
            'max_climb_rate':     'м',
            'total_duration_s':   'с',
            'start_alt_m':        'м',
            'max_alt_m':          'м',
        }.get(key, '')
        print(f'   {key:25s}: {val} {unit}')

print('\n✅ Готово! Тепер запусти: streamlit run app.py')
