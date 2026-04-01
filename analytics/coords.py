import numpy as np
import pandas as pd

def wgs84_to_ecef(lat, lon, alt):
    a, e2 = 6378137.0, 0.00669437999014
    phi, lam = np.radians(lat), np.radians(lon)
    N = a / np.sqrt(1 - e2 * np.sin(phi)**2)
    return (N+alt)*np.cos(phi)*np.cos(lam), (N+alt)*np.cos(phi)*np.sin(lam), (N*(1-e2)+alt)*np.sin(phi)

def ecef_to_enu(x, y, z, lat0, lon0, alt0):
    x0, y0, z0 = wgs84_to_ecef(lat0, lon0, alt0)
    phi, lam = np.radians(lat0), np.radians(lon0)
    dx, dy, dz = x-x0, y-y0, z-z0
    t = -np.sin(lam)*dx + np.cos(lam)*dy
    n = -np.sin(phi)*np.cos(lam)*dx - np.sin(phi)*np.sin(lam)*dy + np.cos(phi)*dz
    u = np.cos(phi)*np.cos(lam)*dx + np.cos(phi)*np.sin(lam)*dy + np.sin(phi)*dz
    return t, n, u

def gps_to_enu(gps_df):
    df = gps_df.copy()
    lat0, lon0, alt0 = df['Lat'].iloc[0], df['Lng'].iloc[0], df.get('Alt', pd.Series([0])).iloc[0]
    ecef = df.apply(lambda r: wgs84_to_ecef(r['Lat'], r['Lng'], r.get('Alt', 0)), axis=1)
    enu = ecef.apply(lambda c: ecef_to_enu(c[0], c[1], c[2], lat0, lon0, alt0))
    df['E_m'], df['N_m'], df['U_m'] = enu.apply(lambda c: c[0]), enu.apply(lambda c: c[1]), enu.apply(lambda c: c[2])
    return df
