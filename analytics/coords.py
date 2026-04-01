import numpy as np


def wgs84_to_ecef(lat_deg, lon_deg, alt_m):
    """
    WGS-84 → ECEF (Earth-Centered, Earth-Fixed).

    Земля моделюється як еліпсоїд, тому проста сферична
    тригонометрія не підходить. ECEF — декартова система
    з початком у центрі Землі.

    Радіус кривизни N(φ) враховує, що Земля «сплюснута»
    на полюсах (полярний радіус менший за екваторіальний):

        N(φ) = a / √(1 − e²·sin²(φ))

        X = (N + h)·cos(φ)·cos(λ)
        Y = (N + h)·cos(φ)·sin(λ)
        Z = (N·(1−e²) + h)·sin(φ)

    Параметри еліпсоїда WGS-84:
        a  = 6 378 137.0 м  — велика піввісь (екватор)
        e² = 0.006694       — ексцентриситет²
    """
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
    """
    ECEF → ENU (East-North-Up) відносно точки старту.

    ENU — локальна система, де осі задані відносно
    спостерігача: E — на схід, N — на північ, U — вгору.
    Ідеальна для польотної візуалізації: одиниці — метри
    від точки зльоту, осі інтуїтивні.

    Перетворення — це поворот ECEF на матрицю R,
    де рядки — одиничні вектори осей ENU у ECEF:

        | E |   | −sin(λ)          cos(λ)         0      |   | dx |
        | N | = | −sin(φ)·cos(λ)  −sin(φ)·sin(λ)  cos(φ) | × | dy |
        | U |   |  cos(φ)·cos(λ)   cos(φ)·sin(λ)  sin(φ) |   | dz |

    де φ, λ — широта і довгота точки відліку (старту).
    """
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
    """Конвертує весь GPS-трек WGS-84 → ENU. Точка відліку — перший запис."""
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
