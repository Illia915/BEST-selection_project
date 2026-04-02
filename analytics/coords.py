import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

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
    """Convert GPS coordinates to local ENU (East-North-Up) system.
    
    Args:
        gps_df: DataFrame with Lat, Lng, Alt columns
        
    Returns:
        DataFrame with added E_m, N_m, U_m columns
        
    Raises:
        ValueError: If required columns are missing or data is invalid
    """
    df = gps_df.copy()
    
    # Validate required columns
    required_cols = ['Lat', 'Lng']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
    
    # Handle empty dataframe
    if len(df) == 0:
        logger.warning("Empty GPS dataframe, returning as-is")
        df['E_m'] = []
        df['N_m'] = []
        df['U_m'] = []
        return df
    
    # Get origin point (first valid GPS coordinate)
    valid_idx = df['Lat'].notna() & df['Lng'].notna()
    if not valid_idx.any():
        raise ValueError("No valid GPS coordinates found")
    
    first_valid = df[valid_idx].iloc[0]
    lat0 = first_valid['Lat']
    lon0 = first_valid['Lng']
    alt0 = first_valid.get('Alt', 0) if 'Alt' in df.columns else 0
    
    # Vectorized conversion (much faster than apply)
    lats = np.radians(df['Lat'].fillna(0).values)
    lons = np.radians(df['Lng'].fillna(0).values)
    alts = df['Alt'].fillna(0).values if 'Alt' in df.columns else np.zeros(len(df))
    
    lat0_r, lon0_r = np.radians(lat0), np.radians(lon0)
    
    # WGS-84 constants
    a = 6378137.0  # Earth radius in meters
    e2 = 0.00669437999014  # Eccentricity squared
    
    # Convert to ECEF
    N = a / np.sqrt(1 - e2 * np.sin(lats)**2)
    x = (N + alts) * np.cos(lats) * np.cos(lons)
    y = (N + alts) * np.cos(lats) * np.sin(lons)
    z = (N * (1 - e2) + alts) * np.sin(lats)
    
    # Origin ECEF coordinates
    N0 = a / np.sqrt(1 - e2 * np.sin(lat0_r)**2)
    x0 = (N0 + alt0) * np.cos(lat0_r) * np.cos(lon0_r)
    y0 = (N0 + alt0) * np.cos(lat0_r) * np.sin(lon0_r)
    z0 = (N0 * (1 - e2) + alt0) * np.sin(lat0_r)
    
    # Differences from origin
    dx = x - x0
    dy = y - y0
    dz = z - z0
    
    # Rotate to ENU
    df['E_m'] = -np.sin(lon0_r) * dx + np.cos(lon0_r) * dy
    df['N_m'] = -np.sin(lat0_r) * np.cos(lon0_r) * dx - np.sin(lat0_r) * np.sin(lon0_r) * dy + np.cos(lat0_r) * dz
    df['U_m'] = np.cos(lat0_r) * np.cos(lon0_r) * dx + np.cos(lat0_r) * np.sin(lon0_r) * dy + np.sin(lat0_r) * dz
    
    return df
