import streamlit as st
import os

from scraper.dataflash import parse_log, get_gps_dataframe, get_imu_dataframe
from analytics.metrics import compute_metrics
from analytics.coords import gps_to_enu
from visualization.plot3d import build_3d_track, build_altitude_chart, build_speed_chart
from visualization.map_view import build_map
from ai.assistant import analyze_flight, analyze_flight_ab, AVAILABLE_MODELS, DEFAULT_MODEL
from ai.token_counter import get_session_usage

st.set_page_config(page_title='UAV Telemetry Analyzer', page_icon='', layout='wide')

st.title('UAV Telemetry Analyzer')
st.caption('Аналіз логів Ardupilot · 3D-траєкторія · Карта · AI-висновок')

st.sidebar.header('Завантаження логу')

uploaded = st.sidebar.file_uploader(
    'Виберіть .BIN файл',
    type=['BIN', 'bin'],
    help='Бінарний лог польотного контролера Ardupilot',
)

if uploaded is not None:
    st.session_state.pop('demo_path', None)

demo_path = st.session_state.get('demo_path')

if uploaded is None:
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    if os.path.exists(data_dir):
        bin_files = [f for f in os.listdir(data_dir) if f.endswith('.BIN')]
        if bin_files:
            st.sidebar.markdown('---')
            st.sidebar.subheader('або оберіть тестовий файл')
            chosen = st.sidebar.selectbox('Файл із папки data/', bin_files)
            if st.sidebar.button('Завантажити тестовий файл'):
                st.session_state['demo_path'] = os.path.join(data_dir, chosen)
                demo_path = st.session_state['demo_path']

st.sidebar.markdown('---')
color_by = st.sidebar.radio(
    'Колір 3D-траєкторії',
    ['speed', 'time'],
    format_func=lambda x: 'Швидкість' if x == 'speed' else 'Час',
)

st.sidebar.markdown('---')
st.sidebar.subheader('AI-аналіз')
gemini_key = st.sidebar.text_input(
    'Gemini API Key',
    type='password',
    placeholder='AIza...',
    help='Безкоштовний ключ: https://aistudio.google.com/app/apikey',
)

ai_mode = st.sidebar.radio(
    'Режим',
    ['single', 'ab'],
    format_func=lambda x: 'Одна модель' if x == 'single' else 'A/B порівняння',
)

if ai_mode == 'single':
    selected_model = st.sidebar.selectbox(
        'Модель',
        list(AVAILABLE_MODELS.keys()),
        format_func=lambda x: AVAILABLE_MODELS[x],
        index=list(AVAILABLE_MODELS.keys()).index(DEFAULT_MODEL),
    )
    ab_models = None
else:
    model_options = list(AVAILABLE_MODELS.keys())
    ab_models = st.sidebar.multiselect(
        'Моделі для порівняння',
        model_options,
        default=model_options[:2],
        format_func=lambda x: AVAILABLE_MODELS[x],
    )
    selected_model = None


@st.cache_data(show_spinner='Парсинг бінарного логу...')
def load_log(file_bytes_or_path):
    if isinstance(file_bytes_or_path, str):
        return parse_log(file_bytes_or_path)
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix='.BIN') as tmp:
        tmp.write(file_bytes_or_path)
        tmp_path = tmp.name
    result = parse_log(tmp_path)
    os.unlink(tmp_path)
    return result


if uploaded is not None or demo_path:

    if uploaded is not None:
        dataframes = load_log(uploaded.read())
        filename   = uploaded.name
    else:
        dataframes = load_log(str(demo_path))
        filename   = os.path.basename(demo_path)

    st.sidebar.success(f'✅ {filename}')

    with st.sidebar.expander('Знайдені повідомлення'):
        for name, df in sorted(dataframes.items()):
            st.write(f'`{name}` — {len(df)} рядків')

    gps_df = get_gps_dataframe(dataframes)
    imu_df = get_imu_dataframe(dataframes)

    if gps_df is None or len(gps_df) < 2:
        st.error('GPS-дані не знайдено або їх недостатньо.')
        st.info('Спробуйте файл 00000019.BIN — він містить повний польотний лог.')
        st.stop()

    gps_enu = gps_to_enu(gps_df)
    metrics = compute_metrics(gps_df, imu_df)

    st.subheader('Підсумкові метрики польоту')

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric('Дистанція',
                  f"{metrics['total_distance_m']:,.0f} м" if metrics['total_distance_m'] else '—')
        st.metric('Тривалість',
                  f"{metrics['total_duration_s']:.0f} с" if metrics['total_duration_s'] else '—')
    with col2:
        st.metric('Макс. швидкість',
                  f"{metrics['max_horiz_speed_ms']} м/с" if metrics['max_horiz_speed_ms'] else '—')
        st.metric('Верт. швидкість',
                  f"{metrics['max_vert_speed_ms']} м/с" if metrics['max_vert_speed_ms'] else '—')
    with col3:
        st.metric('Макс. висота',
                  f"{metrics['max_alt_m']} м" if metrics['max_alt_m'] else '—')
        st.metric('Набір висоти',
                  f"{metrics['max_climb_rate']} м" if metrics['max_climb_rate'] else '—')
    with col4:
        st.metric('Макс. прискорення',
                  f"{metrics['max_acceleration']} м/с²" if metrics['max_acceleration'] else '—')
        st.metric('GPS-точок', len(gps_df))

    st.markdown('---')

    tab_3d, tab_map, tab_charts, tab_ai = st.tabs([
        '3D-траєкторія', 'Карта', 'Графіки', 'AI-аналіз',
    ])

    with tab_3d:
        st.plotly_chart(build_3d_track(gps_enu, color_by=color_by), use_container_width=True)

    with tab_map:
        st.caption('Leaflet · OpenStreetMap · без API ключа · колір за швидкістю')
        try:
            from streamlit_folium import st_folium
            st_folium(build_map(gps_df), use_container_width=True, height=550)
        except ImportError:
            st.warning('Встанови: `pip install folium streamlit-folium`')

    with tab_charts:
        col_l, col_r = st.columns(2)
        with col_l:
            if 'Alt' in gps_df.columns:
                st.plotly_chart(build_altitude_chart(gps_df), use_container_width=True)
        with col_r:
            spd_fig = build_speed_chart(gps_df)
            if spd_fig:
                st.plotly_chart(spd_fig, use_container_width=True)
        with st.expander('Сирі GPS-дані'):
            st.dataframe(gps_df.head(200), use_container_width=True)

    with tab_ai:
        st.subheader('AI-аналіз польоту')

        if ai_mode == 'single':
            st.caption(f'Модель: **{AVAILABLE_MODELS.get(selected_model, selected_model)}**')
        else:
            st.caption(f'A/B порівняння: **{len(ab_models or [])} моделі**')

        col_btn, col_info = st.columns([1, 3])
        with col_btn:
            run_ai = st.button('Запустити аналіз', type='primary', use_container_width=True)
        with col_info:
            st.info('Gemini виявить аномалії та сформує структурований технічний висновок.')

        if run_ai:
            if not gemini_key:
                st.warning('Введи Gemini API ключ у бічній панелі.')
            elif ai_mode == 'ab':
                if not ab_models:
                    st.warning('Оберіть хоча б дві моделі для A/B порівняння.')
                else:
                    with st.spinner('Запити до моделей...'):
                        results = analyze_flight_ab(
                            metrics=metrics, gps_df=gps_df,
                            api_key=gemini_key, models=ab_models,
                        )
                    cols = st.columns(len(results))
                    for col, res in zip(cols, results):
                        with col:
                            model_label = AVAILABLE_MODELS.get(res['model'], res['model'])
                            st.markdown(f'### {model_label}')
                            st.markdown(
                                f'`{res["prompt_tokens"]} prompt` · '
                                f'`{res["completion_tokens"]} completion`'
                            )
                            st.markdown(res['text'])
                            st.download_button(
                                f'Зберегти ({res["model"]})',
                                data=res['text'],
                                file_name=f'flight_analysis_{res["model"]}.txt',
                                mime='text/plain',
                            )
            else:
                with st.spinner('Gemini аналізує політ...'):
                    result = analyze_flight(
                        metrics=metrics, gps_df=gps_df,
                        api_key=gemini_key, model=selected_model,
                    )
                st.markdown('### Висновок')
                st.markdown(
                    f'`{result["prompt_tokens"]} prompt tokens` · '
                    f'`{result["completion_tokens"]} completion tokens`'
                )
                st.markdown(result['text'])
                st.download_button(
                    'Зберегти висновок',
                    data=result['text'],
                    file_name='flight_analysis.txt',
                    mime='text/plain',
                )

        usage = get_session_usage()
        if usage['requests'] > 0:
            st.markdown('---')
            st.caption(
                f'Сесія: **{usage["requests"]} запитів** · '
                f'**{usage["total_tokens"]} токенів** '
                f'({usage["prompt_tokens"]} prompt + {usage["completion_tokens"]} completion)'
            )

else:
    st.info('Завантажте .BIN файл у бічній панелі')
    st.markdown('''
    ### Можливості

    | Функція | Опис |
    |---------|------|
    | 3D-траєкторія | Plotly · обертання · колір за швидкістю або часом |
    | Карта | Leaflet + OpenStreetMap · без API ключа |
    | Метрики | Дистанція haversine · швидкість · висота · прискорення |
    | AI-аналіз | Gemini — одна модель або A/B порівняння |
    | Токени | Лічильник використаних токенів за сесію |

    ### Запуск
    ```bash
    pip install -r requirements.txt
    streamlit run app.py
    ```
    ''')
