import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import pandas as pd
import pytest

from analytics.coords import wgs84_to_ecef, ecef_to_enu, gps_to_enu
from analytics.metrics import haversine, filter_gps, compute_sampling_rate, total_distance
from scraper.dataflash import get_gps_dataframe, get_imu_dataframe, get_attitude_dataframe
from ai.prompts import detect_anomalies


# ── coords ────────────────────────────────────────────────────────────────────

def test_wgs84_to_ecef_equator():
    X, Y, Z = wgs84_to_ecef(0.0, 0.0, 0.0)
    assert abs(X - 6_378_137.0) < 1.0
    assert abs(Y) < 1.0
    assert abs(Z) < 1.0

def test_ecef_to_enu_origin_is_zero():
    lat0, lon0, alt0 = 50.45, 30.52, 100.0
    X0, Y0, Z0 = wgs84_to_ecef(lat0, lon0, alt0)
    E, N, U = ecef_to_enu(X0, Y0, Z0, lat0, lon0, alt0)
    assert abs(E) < 1e-6
    assert abs(N) < 1e-6
    assert abs(U) < 1e-6

def test_gps_to_enu_first_point_zero():
    df = pd.DataFrame({
        'Lat': [50.45, 50.451, 50.452],
        'Lng': [30.52, 30.521, 30.522],
        'Alt': [100.0, 101.0, 102.0],
        'TimeUS': [0, 200000, 400000],
    })
    enu = gps_to_enu(df)
    assert abs(enu['E_m'].iloc[0]) < 1e-6
    assert abs(enu['N_m'].iloc[0]) < 1e-6
    assert abs(enu['U_m'].iloc[0]) < 1e-6

def test_gps_to_enu_north_is_positive():
    df = pd.DataFrame({
        'Lat': [50.0, 50.01],
        'Lng': [30.0, 30.0],
        'Alt': [0.0, 0.0],
        'TimeUS': [0, 1000000],
    })
    enu = gps_to_enu(df)
    assert enu['N_m'].iloc[1] > 0

def test_gps_to_enu_east_is_positive():
    df = pd.DataFrame({
        'Lat': [50.0, 50.0],
        'Lng': [30.0, 30.01],
        'Alt': [0.0, 0.0],
        'TimeUS': [0, 1000000],
    })
    enu = gps_to_enu(df)
    assert enu['E_m'].iloc[1] > 0


# ── metrics ───────────────────────────────────────────────────────────────────

def test_haversine_same_point():
    assert haversine(50.0, 30.0, 50.0, 30.0) == pytest.approx(0.0)

def test_haversine_kyiv_lviv():
    dist = haversine(50.4501, 30.5234, 49.8397, 24.0297)
    assert 460_000 < dist < 480_000

def test_haversine_symmetry():
    d1 = haversine(50.0, 30.0, 48.0, 25.0)
    d2 = haversine(48.0, 25.0, 50.0, 30.0)
    assert d1 == pytest.approx(d2)

def test_total_distance_straight_line():
    df = pd.DataFrame({
        'Lat': [50.0, 50.0, 50.0],
        'Lng': [30.0, 30.01, 30.02],
    })
    d = total_distance(df)
    d_single = haversine(50.0, 30.0, 50.0, 30.01)
    assert d == pytest.approx(d_single * 2, rel=1e-6)

def test_filter_gps_removes_zeros():
    df = pd.DataFrame({
        'Lat': [0.0, 50.45, 50.451, 50.452],
        'Lng': [0.0, 30.52, 30.521, 30.522],
    })
    filtered = filter_gps(df)
    assert (filtered['Lat'] != 0).all()
    assert (filtered['Lng'] != 0).all()

def test_filter_gps_removes_outliers():
    df = pd.DataFrame({
        'Lat': [50.45] * 20 + [99.0],
        'Lng': [30.52] * 20 + [99.0],
    })
    filtered = filter_gps(df)
    assert 99.0 not in filtered['Lat'].values
    assert 99.0 not in filtered['Lng'].values

def test_compute_sampling_rate():
    df = pd.DataFrame({'TimeUS': np.arange(0, 10 * 200_000, 200_000)})
    hz = compute_sampling_rate(df)
    assert hz == pytest.approx(5.0)

def test_compute_sampling_rate_too_short():
    df = pd.DataFrame({'TimeUS': [0]})
    assert compute_sampling_rate(df) is None


# ── dataflash column mapping ──────────────────────────────────────────────────

def _make_dataframes(gps_cols, imu_cols, att_cols=None):
    n = 5
    dfs = {}
    dfs['GPS'] = pd.DataFrame({c: np.linspace(50.0, 50.01, n) if c.lower() in ('lat', 'latitude') else
                                   np.linspace(30.0, 30.01, n) if c.lower() in ('lng', 'lon', 'longitude') else
                                   np.linspace(100.0, 110.0, n) if c.lower() in ('alt', 'altitude') else
                                   np.linspace(0, 4 * 200_000, n) if c == 'TimeUS' else
                                   np.ones(n) for c in gps_cols})
    dfs['IMU'] = pd.DataFrame({c: np.random.randn(n) if c.lower() not in ('timeus',) else
                                   np.linspace(0, 4 * 10_000, n) for c in imu_cols})
    if att_cols:
        dfs['ATT'] = pd.DataFrame({c: np.zeros(n) if c.lower() not in ('timeus',) else
                                       np.linspace(0, 4 * 200_000, n) for c in att_cols})
    return dfs

def test_get_gps_dataframe_standard_columns():
    dfs = _make_dataframes(['Lat', 'Lng', 'Alt', 'Spd', 'VZ', 'TimeUS'], ['AccX', 'AccY', 'AccZ', 'TimeUS'])
    gps = get_gps_dataframe(dfs)
    assert gps is not None
    assert 'Lat' in gps.columns
    assert 'Lng' in gps.columns

def test_get_gps_dataframe_alt_column_names():
    dfs = _make_dataframes(['latitude', 'longitude', 'altitude', 'TimeUS'], ['AccX', 'AccY', 'AccZ', 'TimeUS'])
    gps = get_gps_dataframe(dfs)
    assert gps is not None
    assert 'Lat' in gps.columns
    assert 'Lng' in gps.columns

def test_get_gps_dataframe_missing_returns_none():
    dfs = {'IMU': pd.DataFrame({'AccX': [1, 2]})}
    assert get_gps_dataframe(dfs) is None

def test_get_imu_dataframe_standard_columns():
    dfs = _make_dataframes(['Lat', 'Lng', 'TimeUS'], ['AccX', 'AccY', 'AccZ', 'GyrX', 'GyrY', 'GyrZ', 'TimeUS'])
    imu = get_imu_dataframe(dfs)
    assert imu is not None
    assert 'AccX' in imu.columns
    assert 'AccZ' in imu.columns

def test_get_imu_dataframe_short_names():
    dfs = _make_dataframes(['Lat', 'Lng', 'TimeUS'], ['AX', 'AY', 'AZ', 'GX', 'GY', 'GZ', 'TimeUS'])
    imu = get_imu_dataframe(dfs)
    assert imu is not None
    assert 'AccX' in imu.columns

def test_get_attitude_dataframe():
    dfs = _make_dataframes(['Lat', 'Lng', 'TimeUS'], ['AccX', 'TimeUS'], att_cols=['Roll', 'Pitch', 'Yaw', 'TimeUS'])
    att = get_attitude_dataframe(dfs)
    assert att is not None
    assert 'Roll' in att.columns
    assert 'Pitch' in att.columns

def test_get_attitude_dataframe_missing_returns_none():
    dfs = {'GPS': pd.DataFrame({'Lat': [50.0]})}
    assert get_attitude_dataframe(dfs) is None


# ── ai anomaly detection ──────────────────────────────────────────────────────

def _make_gps(spd=5.0, alt_start=100.0, alt_end=100.0, n=10):
    return pd.DataFrame({
        'Spd': np.full(n, spd),
        'Alt': np.linspace(alt_start, alt_end, n),
        'Lat': np.linspace(50.0, 50.01, n),
        'Lng': np.linspace(30.0, 30.01, n),
    })

def test_detect_anomalies_no_anomalies():
    gps = _make_gps(spd=5.0, alt_start=100.0, alt_end=105.0)
    assert detect_anomalies(gps) == []

def test_detect_anomalies_high_speed():
    gps = _make_gps(spd=25.0)
    anomalies = detect_anomalies(gps)
    assert any('швидкість' in a.lower() or 'speed' in a.lower() or 'швидкост' in a.lower() for a in anomalies)

def test_detect_anomalies_sharp_drop():
    gps = _make_gps(alt_start=150.0, alt_end=50.0, n=5)
    anomalies = detect_anomalies(gps)
    assert any('падіння' in a.lower() for a in anomalies)

def test_detect_anomalies_sharp_climb():
    gps = _make_gps(alt_start=50.0, alt_end=150.0, n=5)
    anomalies = detect_anomalies(gps)
    assert any('набір' in a.lower() for a in anomalies)

def test_detect_anomalies_empty_df():
    assert detect_anomalies(None) == []
    assert detect_anomalies(pd.DataFrame()) == []

def test_detect_anomalies_climb_rate_units():
    # climb rate = dAlt/dt → must be in м/с, not bare м
    gps = _make_gps(alt_start=200.0, alt_end=50.0, n=5)
    anomalies = detect_anomalies(gps)
    assert any(anomalies), "expected at least one anomaly for sharp altitude drop"
    for a in anomalies:
        if 'падіння' in a or 'набір' in a:
            assert 'м/с' in a