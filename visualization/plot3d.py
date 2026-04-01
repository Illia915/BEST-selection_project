import plotly.graph_objects as go
import pandas as pd
import numpy as np

def build_3d_track(gps_enu_df, color_by='speed'):
    df = gps_enu_df.copy()
    if color_by == 'speed' and 'Spd' in df.columns:
        color_values = pd.to_numeric(df['Spd'], errors='coerce').fillna(0).values
        colorbar_title, colorscale = 'Швидкість (м/с)', 'Viridis'
    else:
        t = pd.to_numeric(df['TimeUS'], errors='coerce').values
        color_values = (t - t.min()) / (t.max() - t.min() + 1e-9)
        colorbar_title, colorscale = 'Час польоту', 'Plasma'
    track = go.Scatter3d(x=df['E_m'], y=df['N_m'], z=df['U_m'], mode='lines+markers', line=dict(color=color_values, colorscale=colorscale, width=4, colorbar=dict(title=colorbar_title, thickness=15, len=0.6)), marker=dict(size=2, color=color_values, colorscale=colorscale, opacity=0.7), name='Траєкторія')
    start = go.Scatter3d(x=[df['E_m'].iloc[0]], y=[df['N_m'].iloc[0]], z=[df['U_m'].iloc[0]], mode='markers+text', marker=dict(size=10, color='green'), text=['Старт'], name='Старт')
    finish = go.Scatter3d(x=[df['E_m'].iloc[-1]], y=[df['N_m'].iloc[-1]], z=[df['U_m'].iloc[-1]], mode='markers+text', marker=dict(size=10, color='red'), text=['Фінш'], name='Фінш')
    shadow = go.Scatter3d(x=df['E_m'], y=df['N_m'], z=np.zeros(len(df)), mode='lines', line=dict(color='lightgray', width=1, dash='dot'), name='Проекція', opacity=0.5)
    fig = go.Figure(data=[shadow, track, start, finish])
    fig.update_layout(title='3D-траєкторія БПЛА', scene=dict(xaxis_title='Схід (м)', yaxis_title='Північ (м)', zaxis_title='Висота (м)', aspectmode='data'), margin=dict(l=0, r=0, b=0, t=40), height=600)
    return fig

def build_altitude_chart(gps_df):
    df = gps_df.copy()
    t = (df['TimeUS'] - df['TimeUS'].iloc[0]) / 1e6
    fig = go.Figure(go.Scatter(x=t, y=df['Alt'], mode='lines', fill='tozeroy', name='Висота'))
    fig.update_layout(title='Висота (GPS)', xaxis_title='Час (с)', yaxis_title='Висота (м)', height=300)
    return fig

def build_speed_chart(gps_df):
    if 'Spd' not in gps_df.columns: return None
    t = (gps_df['TimeUS'] - gps_df['TimeUS'].iloc[0]) / 1e6
    fig = go.Figure(go.Scatter(x=t, y=gps_df['Spd'], mode='lines', name='Швидкість'))
    fig.update_layout(title='Швидкість (GPS)', xaxis_title='Час (с)', yaxis_title='Швидкість (м/с)', height=300)
    return fig

def build_speed_comparison_chart(imu_df, att_df, gps_df):
    if imu_df is None or att_df is None or 'VZ' not in gps_df.columns: return None
    from analytics.metrics import trapz_integrate
    merged = pd.merge_asof(imu_df[['TimeUS', 'AccX', 'AccY', 'AccZ']], att_df[['TimeUS', 'Roll', 'Pitch']], on='TimeUS')
    r, p = np.radians(merged['Roll'].values), np.radians(merged['Pitch'].values)
    acc_z_earth = merged['AccX'].values * np.sin(-p) + merged['AccY'].values * np.sin(r) * np.cos(p) + merged['AccZ'].values * np.cos(r) * np.cos(p)
    v_z_imu = trapz_integrate(acc_z_earth + 9.80665, merged['TimeUS'].values)
    t_imu = (merged['TimeUS'].values - gps_df['TimeUS'].iloc[0]) / 1e6
    t_gps = (gps_df['TimeUS'].values - gps_df['TimeUS'].iloc[0]) / 1e6
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t_gps, y=gps_df['VZ'].abs(), mode='lines', name='GPS V-Speed', line=dict(dash='dash')))
    fig.add_trace(go.Scatter(x=t_imu, y=np.abs(v_z_imu), mode='lines', name='IMU V-Speed', line=dict(color='red')))
    fig.update_layout(title='GPS vs IMU Accuracy', xaxis_title='Час (с)', yaxis_title='м/с', height=350, legend=dict(orientation="h"))
    return fig
