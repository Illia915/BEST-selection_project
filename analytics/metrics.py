import numpy as np
import pandas as pd


def haversine(lat1, lon1, lat2, lon2):
    R = 6_371_000

    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlam = np.radians(lon2 - lon1)

    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    return R * c


def filter_gps(gps_df):
    df = gps_df.copy()

    if 'Alt' in df.columns and 'TimeUS' in df.columns:
        alt_start = df['Alt'].iloc[0]
        df = df[df['Alt'] > alt_start - 200].copy()

    if 'Lat' in df.columns and 'Lng' in df.columns and len(df) > 10:
        lat_med = df['Lat'].median()
        lng_med = df['Lng'].median()
        df = df[
            ((df['Lat'] - lat_med).abs() < 0.5) &
            ((df['Lng'] - lng_med).abs() < 0.5)
        ].copy()

    return df.reset_index(drop=True)


def total_distance(gps_df):
    lats = gps_df['Lat'].values
    lngs = gps_df['Lng'].values

    dist = 0.0
    for idx in range(1, len(lats)):
        dist += haversine(lats[idx - 1], lngs[idx - 1], lats[idx], lngs[idx])

    return dist


def trapz_integrate(values, times_us):
    dt = np.diff(times_us) / 1e6
    acc = np.array(values)

    velocities = np.zeros(len(acc))
    for idx in range(1, len(acc)):
        velocities[idx] = velocities[idx - 1] + (acc[idx - 1] + acc[idx]) / 2.0 * dt[idx - 1]

    return velocities


def compute_metrics(gps_df, imu_df=None):
    metrics = {}

    df = filter_gps(gps_df)

    metrics['total_distance_m'] = round(total_distance(df), 1)

    if 'TimeUS' in df.columns:
        t_start = df['TimeUS'].iloc[0]
        t_end   = df['TimeUS'].iloc[-1]
        metrics['total_duration_s'] = round((t_end - t_start) / 1e6, 1)
    else:
        metrics['total_duration_s'] = None

    if 'Alt' in df.columns:
        metrics['start_alt_m'] = round(float(df['Alt'].iloc[0]), 1)
        metrics['max_alt_m']   = round(float(df['Alt'].max()), 1)
        metrics['max_climb_rate'] = round(float(df['Alt'].max() - df['Alt'].iloc[0]), 1)
    else:
        metrics['start_alt_m']    = None
        metrics['max_alt_m']      = None
        metrics['max_climb_rate'] = None

    if 'Spd' in df.columns:
        spd = pd.to_numeric(df['Spd'], errors='coerce')
        metrics['max_horiz_speed_ms'] = round(float(spd.max()), 2)
    else:
        lats = df['Lat'].values
        lngs = df['Lng'].values
        times = df['TimeUS'].values / 1e6
        speeds = []
        for idx in range(1, len(lats)):
            dt = times[idx] - times[idx - 1]
            if dt > 0:
                d = haversine(lats[idx - 1], lngs[idx - 1], lats[idx], lngs[idx])
                speeds.append(d / dt)
        metrics['max_horiz_speed_ms'] = round(max(speeds), 2) if speeds else None

    if 'VZ' in df.columns:
        vz = pd.to_numeric(df['VZ'], errors='coerce').abs()
        metrics['max_vert_speed_ms'] = round(float(vz.max()), 2)
    elif 'Alt' in df.columns and 'TimeUS' in df.columns:
        alts  = df['Alt'].values
        times = df['TimeUS'].values / 1e6
        climb_rates = []
        for idx in range(1, len(alts)):
            dt = times[idx] - times[idx - 1]
            if 0 < dt < 2.0:
                rate = abs(alts[idx] - alts[idx - 1]) / dt
                if rate < 50:
                    climb_rates.append(rate)
        metrics['max_vert_speed_ms'] = round(max(climb_rates), 2) if climb_rates else None
    else:
        metrics['max_vert_speed_ms'] = None

    if imu_df is not None and all(c in imu_df.columns for c in ['AccX', 'AccY', 'AccZ']):
        ax = pd.to_numeric(imu_df['AccX'], errors='coerce').values
        ay = pd.to_numeric(imu_df['AccY'], errors='coerce').values
        az = pd.to_numeric(imu_df['AccZ'], errors='coerce').values
        total_acc = np.sqrt(ax ** 2 + ay ** 2 + az ** 2)
        p95 = np.nanpercentile(total_acc, 95)
        metrics['max_acceleration'] = round(float(p95), 2)
    else:
        metrics['max_acceleration'] = None

    return metrics
