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

st.markdown("""
<style>
    /* ── Загальний фон ── */
    .stApp { background-color: #0f1117; color: #e0e0e0; }
    section[data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #21262d; }

    /* ── Metric cards ── */
    [data-testid="stMetric"] {
        background: #161b22;
        border: 1px solid #21262d;
        border-radius: 8px;
        padding: 16px 20px;
    }
    [data-testid="stMetricLabel"] { color: #8b949e !important; font-size: 11px !important; text-transform: uppercase; letter-spacing: 0.08em; }
    [data-testid="stMetricValue"] { color: #e6edf3 !important; font-size: 22px !important; font-weight: 600; }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] { background: #161b22; border-bottom: 1px solid #21262d; gap: 0; }
    .stTabs [data-baseweb="tab"] { color: #8b949e; padding: 10px 20px; font-size: 13px; font-weight: 500; border-bottom: 2px solid transparent; }
    .stTabs [aria-selected="true"] { color: #58a6ff !important; border-bottom: 2px solid #58a6ff !important; background: transparent !important; }

    /* ── Кнопки ── */
    .stButton > button[kind="primary"] {
        background: #238636; border: 1px solid #2ea043; color: #fff;
        font-weight: 600; border-radius: 6px;
    }
    .stButton > button[kind="primary"]:hover { background: #2ea043; }

    /* ── Header ── */
    .app-header {
        display: flex; align-items: center; justify-content: space-between;
        padding: 20px 0 16px; border-bottom: 1px solid #21262d; margin-bottom: 24px;
    }
    .app-title { font-size: 20px; font-weight: 700; color: #e6edf3; letter-spacing: -0.02em; }
    .app-subtitle { font-size: 12px; color: #8b949e; margin-top: 2px; }
    .status-badge {
        display: inline-flex; align-items: center; gap: 6px;
        background: #1f2937; border: 1px solid #374151;
        border-radius: 20px; padding: 4px 12px; font-size: 12px; color: #9ca3af;
    }
    .status-dot { width: 7px; height: 7px; border-radius: 50%; background: #22c55e; }

    /* ── Section labels ── */
    .section-label {
        font-size: 11px; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.1em; color: #8b949e; margin-bottom: 12px;
    }

    /* ── AI result card ── */
    .ai-card {
        background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 20px 24px;
    }
    .ai-card-header {
        display: flex; align-items: center; justify-content: space-between;
        margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid #21262d;
    }
    .model-badge {
        background: #1f2937; border: 1px solid #374151; border-radius: 4px;
        padding: 2px 8px; font-size: 11px; color: #58a6ff; font-family: monospace;
    }
    .token-info { font-size: 11px; color: #8b949e; }

    /* ── Token counter ── */
    .token-bar {
        background: #161b22; border: 1px solid #21262d; border-radius: 6px;
        padding: 10px 16px; display: flex; gap: 24px; margin-top: 16px;
    }
    .token-stat { font-size: 12px; color: #8b949e; }
    .token-stat span { color: #e6edf3; font-weight: 600; }

    /* ── Landing ── */
    .feature-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 20px 0; }
    .feature-card {
        background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 16px 18px;
    }
    .feature-card-title { font-size: 13px; font-weight: 600; color: #e6edf3; margin-bottom: 4px; }
    .feature-card-desc { font-size: 12px; color: #8b949e; }

    /* ── Expander / dataframe ── */
    [data-testid="stExpander"] { background: #161b22; border: 1px solid #21262d; border-radius: 6px; }
    [data-testid="stDataFrame"] { background: #161b22; }
    div[data-testid="stCaption"] { color: #6e7681 !important; font-size: 11px !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="app-header">
    <div>
        <div class="app-title">UAV Telemetry Analyzer</div>
        <div class="app-subtitle">Ardupilot DataFlash · 3D Trajectory · GPS/IMU Analytics · Gemini AI</div>
    </div>
    <div class="status-badge"><div class="status-dot"></div>System Online</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown('<div class="section-label">Data Source</div>', unsafe_allow_html=True)

uploaded = st.sidebar.file_uploader(
    'Upload .BIN file',
    type=['BIN', 'bin'],
    help='Ardupilot DataFlash binary log',
    label_visibility='collapsed',
)

if uploaded is not None:
    st.session_state.pop('demo_path', None)

demo_path = st.session_state.get('demo_path')

if uploaded is None:
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    if os.path.exists(data_dir):
        bin_files = [f for f in os.listdir(data_dir) if f.endswith('.BIN')]
        if bin_files:
            st.sidebar.markdown('<div class="section-label" style="margin-top:12px">Sample Logs</div>', unsafe_allow_html=True)
            chosen = st.sidebar.selectbox('', bin_files, label_visibility='collapsed')
            if st.sidebar.button('Load Sample File', use_container_width=True):
                st.session_state['demo_path'] = os.path.join(data_dir, chosen)
                demo_path = st.session_state['demo_path']

st.sidebar.markdown('<div class="section-label" style="margin-top:16px">Visualization</div>', unsafe_allow_html=True)
color_by = st.sidebar.radio(
    'Trajectory color',
    ['speed', 'time'],
    format_func=lambda x: 'By Speed' if x == 'speed' else 'By Time',
    label_visibility='collapsed',
)

st.sidebar.markdown('<div class="section-label" style="margin-top:16px">AI Engine</div>', unsafe_allow_html=True)
gemini_key = st.sidebar.text_input(
    'Gemini API Key',
    type='password',
    placeholder='AIza...',
    help='Free key: https://aistudio.google.com/app/apikey',
    label_visibility='collapsed',
)

ai_mode = st.sidebar.radio(
    'Mode',
    ['single', 'ab'],
    format_func=lambda x: 'Single Model' if x == 'single' else 'A/B Comparison',
    label_visibility='collapsed',
)

if ai_mode == 'single':
    selected_model = st.sidebar.selectbox(
        'Model',
        list(AVAILABLE_MODELS.keys()),
        format_func=lambda x: AVAILABLE_MODELS[x],
        index=list(AVAILABLE_MODELS.keys()).index(DEFAULT_MODEL),
        label_visibility='collapsed',
    )
    ab_models = None
else:
    model_options = list(AVAILABLE_MODELS.keys())
    ab_models = st.sidebar.multiselect(
        'Models',
        model_options,
        default=model_options[:2],
        format_func=lambda x: AVAILABLE_MODELS[x],
        label_visibility='collapsed',
    )
    selected_model = None


@st.cache_data(show_spinner='Parsing binary log...')
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

    with st.sidebar.expander('Message types'):
        for name, df in sorted(dataframes.items()):
            st.write(f'`{name}` — {len(df)} rows')

    gps_df = get_gps_dataframe(dataframes)
    imu_df = get_imu_dataframe(dataframes)

    if gps_df is None or len(gps_df) < 2:
        st.error('GPS data not found or insufficient.')
        st.info('Try 00000019.BIN — it contains a full flight log.')
        st.stop()

    gps_enu = gps_to_enu(gps_df)
    metrics = compute_metrics(gps_df, imu_df)

    st.markdown('<div class="section-label">Flight Metrics</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric('Total Distance',
                  f"{metrics['total_distance_m']:,.0f} m" if metrics['total_distance_m'] else '—')
        st.metric('Flight Duration',
                  f"{metrics['total_duration_s']:.0f} s" if metrics['total_duration_s'] else '—')
    with col2:
        st.metric('Max Horiz. Speed',
                  f"{metrics['max_horiz_speed_ms']} m/s" if metrics['max_horiz_speed_ms'] else '—')
        st.metric('Max Vert. Speed',
                  f"{metrics['max_vert_speed_ms']} m/s" if metrics['max_vert_speed_ms'] else '—')
    with col3:
        st.metric('Max Altitude',
                  f"{metrics['max_alt_m']} m" if metrics['max_alt_m'] else '—')
        st.metric('Altitude Gain',
                  f"{metrics['max_climb_rate']} m" if metrics['max_climb_rate'] else '—')
    with col4:
        st.metric('Max Acceleration',
                  f"{metrics['max_acceleration']} m/s²" if metrics['max_acceleration'] else '—')
        st.metric('GPS Points', len(gps_df))

    st.markdown('<div style="margin-top:24px"></div>', unsafe_allow_html=True)

    tab_3d, tab_map, tab_charts, tab_ai = st.tabs([
        '3D Trajectory', 'Map', 'Charts', 'AI Analysis',
    ])

    with tab_3d:
        st.plotly_chart(build_3d_track(gps_enu, color_by=color_by), use_container_width=True)

    with tab_map:
        try:
            from streamlit_folium import st_folium
            st_folium(build_map(gps_df), use_container_width=True, height=560)
        except ImportError:
            st.warning('Install: `pip install folium streamlit-folium`')

    with tab_charts:
        col_l, col_r = st.columns(2)
        with col_l:
            if 'Alt' in gps_df.columns:
                st.plotly_chart(build_altitude_chart(gps_df), use_container_width=True)
        with col_r:
            spd_fig = build_speed_chart(gps_df)
            if spd_fig:
                st.plotly_chart(spd_fig, use_container_width=True)
        with st.expander('Raw GPS Data'):
            st.dataframe(gps_df.head(200), use_container_width=True)

    with tab_ai:
        mode_label = (
            f'Single model · <span class="model-badge">{selected_model}</span>'
            if ai_mode == 'single'
            else f'A/B Comparison · <span class="model-badge">{len(ab_models or [])} models</span>'
        )
        st.markdown(f'<div style="font-size:13px;color:#8b949e;margin-bottom:16px">{mode_label}</div>',
                    unsafe_allow_html=True)

        col_btn, col_info = st.columns([1, 4])
        with col_btn:
            run_ai = st.button('Run Analysis', type='primary', use_container_width=True)
        with col_info:
            st.markdown(
                '<div style="font-size:12px;color:#8b949e;padding-top:8px">'
                'Gemini will detect anomalies and generate a structured technical flight report.'
                '</div>',
                unsafe_allow_html=True,
            )

        if run_ai:
            if not gemini_key:
                st.warning('Enter your Gemini API key in the sidebar.')
            elif ai_mode == 'ab':
                if not ab_models:
                    st.warning('Select at least two models for A/B comparison.')
                else:
                    with st.spinner('Querying models...'):
                        results = analyze_flight_ab(
                            metrics=metrics, gps_df=gps_df,
                            api_key=gemini_key, models=ab_models,
                        )
                    cols = st.columns(len(results))
                    for col, res in zip(cols, results):
                        with col:
                            st.markdown(f"""
                            <div class="ai-card">
                                <div class="ai-card-header">
                                    <span class="model-badge">{res['model']}</span>
                                    <span class="token-info">{res['prompt_tokens']}↑ {res['completion_tokens']}↓ tokens</span>
                                </div>
                            """, unsafe_allow_html=True)
                            st.markdown(res['text'])
                            st.markdown('</div>', unsafe_allow_html=True)
                            st.download_button(
                                f'Export ({res["model"]})',
                                data=res['text'],
                                file_name=f'flight_analysis_{res["model"]}.txt',
                                mime='text/plain',
                                use_container_width=True,
                            )
            else:
                with st.spinner('Analyzing flight...'):
                    result = analyze_flight(
                        metrics=metrics, gps_df=gps_df,
                        api_key=gemini_key, model=selected_model,
                    )
                st.markdown(f"""
                <div class="ai-card">
                    <div class="ai-card-header">
                        <span class="model-badge">{result['model']}</span>
                        <span class="token-info">{result['prompt_tokens']}↑ &nbsp;{result['completion_tokens']}↓ &nbsp;tokens</span>
                    </div>
                """, unsafe_allow_html=True)
                st.markdown(result['text'])
                st.markdown('</div>', unsafe_allow_html=True)
                st.download_button(
                    'Export Report',
                    data=result['text'],
                    file_name='flight_analysis.txt',
                    mime='text/plain',
                )

        usage = get_session_usage()
        if usage['requests'] > 0:
            st.markdown(f"""
            <div class="token-bar">
                <div class="token-stat">Requests <span>{usage['requests']}</span></div>
                <div class="token-stat">Total tokens <span>{usage['total_tokens']}</span></div>
                <div class="token-stat">Prompt <span>{usage['prompt_tokens']}</span></div>
                <div class="token-stat">Completion <span>{usage['completion_tokens']}</span></div>
            </div>
            """, unsafe_allow_html=True)

else:
    st.markdown("""
    <div style="text-align:center; padding: 60px 20px 40px;">
        <div style="font-size:48px; margin-bottom:12px">🛸</div>
        <div style="font-size:22px; font-weight:700; color:#e6edf3; margin-bottom:8px">
            Upload a flight log to begin
        </div>
        <div style="font-size:14px; color:#8b949e; max-width:480px; margin: 0 auto 40px;">
            Upload an Ardupilot <code>.BIN</code> file via the sidebar or select a sample log
            to analyse the flight trajectory, compute metrics and run AI diagnostics.
        </div>
    </div>

    <div class="feature-grid">
        <div class="feature-card">
            <div class="feature-card-title">3D Trajectory</div>
            <div class="feature-card-desc">Interactive Plotly · WGS-84 → ENU · color by speed or time</div>
        </div>
        <div class="feature-card">
            <div class="feature-card-title">Flight Metrics</div>
            <div class="feature-card-desc">Haversine distance · trapezoidal IMU integration · altitude · acceleration</div>
        </div>
        <div class="feature-card">
            <div class="feature-card-title">2D Map</div>
            <div class="feature-card-desc">Leaflet · OpenStreetMap · no API key · speed colormap</div>
        </div>
        <div class="feature-card">
            <div class="feature-card-title">AI Analysis</div>
            <div class="feature-card-desc">Gemini 2.5 Flash · anomaly detection · structured technical report</div>
        </div>
        <div class="feature-card">
            <div class="feature-card-title">A/B Model Comparison</div>
            <div class="feature-card-desc">Run multiple Gemini models simultaneously and compare outputs</div>
        </div>
        <div class="feature-card">
            <div class="feature-card-title">Pipeline Logging</div>
            <div class="feature-card-desc">Every AI request logged with tokens, prompt and response · JSON or MongoDB</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
