import numpy as np


def wgs84_to_ecef(lat_deg, lon_deg, alt_m):
    a  = 6_378_137.0
    e2 = 0.00669437999014

    lat = np.radians(lat_deg)
    lon = np.radians(lon_deg)

    N = a / np.sqrt(1 - e2 * np.sin(lat) ** 2)

    X = (N + alt_m) * np.cos(lat) * np.cos(lon)
    Y = (N + alt_m) * np.cos(lat) * np.sin(lon)
    Z = (N * (1 - e2) + alt_m) * np.sin(lat)

    return X, Y, Z


def ecef_to_enu(x, y, z, lat0_deg, lon0_deg, alt0_m):
    x0, y0, z0 = wgs84_to_ecef(lat0_deg, lon0_deg, alt0_m)

    dx = x - x0
    dy = y - y0
    dz = z - z0

    lat0 = np.radians(lat0_deg)
    lon0 = np.radians(lon0_deg)

    sin_lat = np.sin(lat0)
    cos_lat = np.cos(lat0)
    sin_lon = np.sin(lon0)
    cos_lon = np.cos(lon0)

    E = -sin_lon * dx + cos_lon * dy
    N = -sin_lat * cos_lon * dx - sin_lat * sin_lon * dy + cos_lat * dz
    U =  cos_lat * cos_lon * dx + cos_lat * sin_lon * dy + sin_lat * dz

    return E, N, U


def gps_to_enu(gps_df):
    df = gps_df.copy()

    lat0 = float(df['Lat'].iloc[0])
    lon0 = float(df['Lng'].iloc[0])
    alt0 = float(df['Alt'].iloc[0]) if 'Alt' in df.columns else 0.0

    lats = df['Lat'].values.astype(float)
    lngs = df['Lng'].values.astype(float)
    alts = df['Alt'].values.astype(float) if 'Alt' in df.columns else np.zeros(len(df))

    X, Y, Z = wgs84_to_ecef(lats, lngs, alts)
    E, N, U = ecef_to_enu(X, Y, Z, lat0, lon0, alt0)

    df['E_m'] = E
    df['N_m'] = N
    df['U_m'] = U

    return df
