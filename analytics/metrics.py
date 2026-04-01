import numpy as np
import pandas as pd

def haversine(lat1, lon1, lat2, lon2):
    R = 6_371_000
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi, dlam = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

def total_distance(gps_df):
    lats, lngs = gps_df['Lat'].values, gps_df['Lng'].values
    dist = 0.0
    for i in range(1, len(lats)):
        dist += haversine(lats[i-1], lngs[i-1], lats[i], lngs[i])
    return dist

def trapz_integrate(values, times_us):
    dt = np.diff(times_us) / 1e6
    acc = np.array(values)
    velocities = np.zeros(len(acc))
    for i in range(1, len(acc)):
        v = velocities[i-1] + (acc[i-1] + acc[i]) / 2.0 * dt[i-1]
        if np.abs(acc[i]) < 0.05: v *= 0.99
        velocities[i] = v
    return velocities

def compute_sampling_rate(df, time_col='TimeUS'):
    if df is None or time_col not in df.columns or len(df) < 2: return None
    times = pd.to_numeric(df[time_col], errors='coerce').dropna().values
    if len(times) < 2: return None
    dt_mean = np.mean(np.diff(times)) / 1e6
    return round(1.0 / dt_mean, 1) if dt_mean > 0 else None

def filter_gps(gps_df):
    df = gps_df.copy()
    if len(df) > 5: df = df.iloc[2:].reset_index(drop=True)
    if 'Lat' in df.columns and 'Lng' in df.columns:
        df = df[(df['Lat'] != 0) & (df['Lng'] != 0)]
    if len(df) > 10:
        lat_med, lng_med = df['Lat'].median(), df['Lng'].median()
        df = df[((df['Lat'] - lat_med).abs() < 0.1) & ((df['Lng'] - lng_med).abs() < 0.1)]
    return df.reset_index(drop=True)

def downsample_df(df, max_points=5000):
    if df is None or len(df) <= max_points: return df
    step = len(df) // max_points
    return df.iloc[::step].reset_index(drop=True)

def compute_metrics(gps_df, imu_df=None, att_df=None, vibe_df=None):
    metrics = {}
    df = filter_gps(gps_df)
    metrics['total_distance_m'] = round(total_distance(df), 1)
    if 'TimeUS' in df.columns:
        metrics['total_duration_s'] = round((df['TimeUS'].iloc[-1] - df['TimeUS'].iloc[0]) / 1e6, 1)
    else: metrics['total_duration_s'] = None
    metrics['gps_sampling_hz'] = compute_sampling_rate(df)
    metrics['imu_sampling_hz'] = compute_sampling_rate(imu_df)
    if 'Alt' in df.columns:
        metrics['start_alt_m'] = round(float(df['Alt'].iloc[0]), 1)
        metrics['max_alt_m'] = round(float(df['Alt'].max()), 1)
        metrics['max_climb_rate'] = round(float(df['Alt'].max() - df['Alt'].iloc[0]), 1)
    if 'Spd' in df.columns:
        metrics['max_horiz_speed_ms'] = round(float(pd.to_numeric(df['Spd'], errors='coerce').max()), 2)
    if 'VZ' in df.columns:
        metrics['max_vert_speed_ms'] = round(float(pd.to_numeric(df['VZ'], errors='coerce').abs().max()), 2)
    if imu_df is not None and all(c in imu_df.columns for c in ['AccX', 'AccY', 'AccZ']):
        ax, ay, az = [pd.to_numeric(imu_df[c], errors='coerce').values for c in ['AccX', 'AccY', 'AccZ']]
        if att_df is not None and 'Roll' in att_df.columns:
            merged = pd.merge_asof(imu_df[['TimeUS', 'AccX', 'AccY', 'AccZ']], att_df[['TimeUS', 'Roll', 'Pitch', 'Yaw']], on='TimeUS')
            r, p = np.radians(merged['Roll'].values), np.radians(merged['Pitch'].values)
            acc_z_earth = merged['AccX'].values * np.sin(-p) + merged['AccY'].values * np.sin(r) * np.cos(p) + merged['AccZ'].values * np.cos(r) * np.cos(p)
            v_z_imu = trapz_integrate(acc_z_earth + 9.80665, merged['TimeUS'].values)
            metrics['imu_max_vz_ms'] = round(float(np.abs(v_z_imu).max()), 2)
            metrics['max_acceleration'] = round(float(np.nanpercentile(np.abs(np.sqrt(ax**2 + ay**2 + az**2) - 9.80665), 95)), 2)
        else:
            metrics['max_acceleration'] = round(float(np.nanpercentile(np.abs(np.sqrt(ax**2 + ay**2 + az**2) - 9.81), 95)), 2)
            if 'TimeUS' in imu_df.columns:
                metrics['imu_max_vz_ms'] = round(float(np.abs(trapz_integrate(az - np.nanmean(az[:10]), imu_df['TimeUS'].values)).max()), 2)
    if vibe_df is not None and 'VibeX' in vibe_df.columns:
        v_max = max(vibe_df['VibeX'].max(), vibe_df['VibeY'].max(), vibe_df['VibeZ'].max())
        metrics['max_vibration'] = round(float(v_max), 2)
    return metrics
