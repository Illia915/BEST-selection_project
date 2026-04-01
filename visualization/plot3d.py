import plotly.graph_objects as go
import pandas as pd
import numpy as np


def build_3d_track(gps_enu_df, color_by='speed'):
    df = gps_enu_df.copy()

    if color_by == 'speed' and 'Spd' in df.columns:
        color_values = pd.to_numeric(df['Spd'], errors='coerce').fillna(0).values
        colorbar_title = 'Швидкість (м/с)'
        colorscale = 'Viridis'
    else:
        t = pd.to_numeric(df['TimeUS'], errors='coerce').values
        color_values = (t - t.min()) / (t.max() - t.min() + 1e-9)
        colorbar_title = 'Час польоту (норм.)'
        colorscale = 'Plasma'

    track = go.Scatter3d(
        x=df['E_m'],
        y=df['N_m'],
        z=df['U_m'],
        mode='lines+markers',
        line=dict(
            color=color_values,
            colorscale=colorscale,
            width=4,
            colorbar=dict(title=colorbar_title, thickness=15, len=0.6),
        ),
        marker=dict(size=2, color=color_values, colorscale=colorscale, opacity=0.7),
        name='Траєкторія',
        hovertemplate=(
            '<b>E:</b> %{x:.1f} м<br>'
            '<b>N:</b> %{y:.1f} м<br>'
            '<b>Висота:</b> %{z:.1f} м<br>'
            '<extra></extra>'
        ),
    )

    start = go.Scatter3d(
        x=[df['E_m'].iloc[0]],
        y=[df['N_m'].iloc[0]],
        z=[df['U_m'].iloc[0]],
        mode='markers+text',
        marker=dict(size=10, color='green', symbol='circle'),
        text=['Старт'],
        textposition='top center',
        name='Старт',
    )

    finish = go.Scatter3d(
        x=[df['E_m'].iloc[-1]],
        y=[df['N_m'].iloc[-1]],
        z=[df['U_m'].iloc[-1]],
        mode='markers+text',
        marker=dict(size=10, color='red', symbol='square'),
        text=['Фінш'],
        textposition='top center',
        name='Фінш',
    )

    shadow = go.Scatter3d(
        x=df['E_m'],
        y=df['N_m'],
        z=np.zeros(len(df)),
        mode='lines',
        line=dict(color='lightgray', width=1, dash='dot'),
        name='Проекція',
        opacity=0.5,
    )

    fig = go.Figure(data=[shadow, track, start, finish])

    fig.update_layout(
        title=dict(text='3D-траєкторія польоту БПЛА', font=dict(size=18)),
        scene=dict(
            xaxis=dict(title='Схід (м)'),
            yaxis=dict(title='Північ (м)'),
            zaxis=dict(title='Висота (м)'),
            aspectmode='data',
            camera=dict(eye=dict(x=1.5, y=1.5, z=0.8)),
        ),
        legend=dict(x=0, y=1),
        margin=dict(l=0, r=0, b=0, t=40),
        height=600,
    )

    return fig


def build_altitude_chart(gps_df):
    df = gps_df.copy()
    time_s = (pd.to_numeric(df['TimeUS'], errors='coerce') -
              pd.to_numeric(df['TimeUS'], errors='coerce').iloc[0]) / 1e6

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=time_s,
        y=pd.to_numeric(df['Alt'], errors='coerce'),
        mode='lines',
        line=dict(color='royalblue', width=2),
        fill='tozeroy',
        fillcolor='rgba(65, 105, 225, 0.2)',
        name='Висота',
    ))
    fig.update_layout(
        title='Висота від часу',
        xaxis_title='Час (с)',
        yaxis_title='Висота (м)',
        height=300,
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return fig


def build_speed_chart(gps_df):
    if 'Spd' not in gps_df.columns:
        return None

    df = gps_df.copy()
    time_s = (pd.to_numeric(df['TimeUS'], errors='coerce') -
              pd.to_numeric(df['TimeUS'], errors='coerce').iloc[0]) / 1e6

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=time_s,
        y=pd.to_numeric(df['Spd'], errors='coerce'),
        mode='lines',
        line=dict(color='darkorange', width=2),
        name='Швидкість (GPS)',
    ))
    fig.update_layout(
        title='Швидкість від часу (GPS)',
        xaxis_title='Час (с)',
        yaxis_title='Швидкість (м/с)',
        height=300,
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return fig


def build_speed_comparison_chart(imu_df, att_df, gps_df):
    """
    Будує графік порівняння вертикальної швидкості: GPS vs IMU (Tilt Compensated).
    Це найкращий спосіб довести математичну точність проекту.
    """
    if imu_df is None or att_df is None or 'VZ' not in gps_df.columns:
        return None

    from analytics.metrics import trapz_integrate
    
    # 1. Розрахунок IMU VZ (земна система)
    merged = pd.merge_asof(
        imu_df[['TimeUS', 'AccX', 'AccY', 'AccZ']], 
        att_df[['TimeUS', 'Roll', 'Pitch']], 
        on='TimeUS'
    )
    r = np.radians(merged['Roll'].values)
    p = np.radians(merged['Pitch'].values)
    acc_z_earth = (
        merged['AccX'].values * np.sin(-p) + 
        merged['AccY'].values * np.sin(r) * np.cos(p) + 
        merged['AccZ'].values * np.cos(r) * np.cos(p)
    )
    acc_z_pure = acc_z_earth + 9.80665
    v_z_imu = trapz_integrate(acc_z_pure, merged['TimeUS'].values)
    
    t_imu = (merged['TimeUS'].values - gps_df['TimeUS'].iloc[0]) / 1e6
    t_gps = (gps_df['TimeUS'].values - gps_df['TimeUS'].iloc[0]) / 1e6
    
    fig = go.Figure()
    
    # Додаємо GPS дані (вертикальна швидкість)
    fig.add_trace(go.Scatter(
        x=t_gps, y=gps_df['VZ'].abs(),
        mode='lines', name='GPS V-Speed',
        line=dict(color='royalblue', width=1.5, dash='dash')
    ))
    
    # Додаємо IMU дані (проінтегровані)
    fig.add_trace(go.Scatter(
        x=t_imu, y=np.abs(v_z_imu),
        mode='lines', name='IMU V-Speed (Ideal)',
        line=dict(color='red', width=2)
    ))
    
    fig.update_layout(
        title='Перевірка точності: GPS vs IMU (Tilt Compensated)',
        xaxis_title='Час (с)',
        yaxis_title='Вертикальна швидкість (м/с)',
        height=350,
        margin=dict(l=40, r=20, t=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig
