import pandas as pd


def parse_log(filepath):
    try:
        from pymavlink import DFReader
    except ImportError:
        raise ImportError("pymavlink не встановлено. Запусти: pip install pymavlink")

    log = DFReader.DFReader_binary(filepath)
    records = {}

    while True:
        msg = log.recv_msg()
        if msg is None:
            break

        msg_type = msg.get_type()
        if msg_type in ('FMT', 'FMTU', 'MULT', 'UNIT', 'PARM'):
            continue

        try:
            row = msg.to_dict()
            row.pop('mavpackettype', None)
        except Exception:
            continue

        if msg_type not in records:
            records[msg_type] = []
        records[msg_type].append(row)

    dataframes = {}
    for name, rows in records.items():
        if rows:
            dataframes[name] = pd.DataFrame(rows)

    return dataframes


def get_gps_dataframe(dataframes):
    for name in ['GPS', 'GPS2', 'GNSS']:
        if name not in dataframes:
            continue

        df = dataframes[name].copy()

        col_map = {}
        for col in df.columns:
            if col.lower() in ('lat', 'latitude'):
                col_map[col] = 'Lat'
            elif col.lower() in ('lng', 'lon', 'longitude'):
                col_map[col] = 'Lng'
            elif col.lower() in ('alt', 'altitude'):
                col_map[col] = 'Alt'
            elif col.lower() in ('spd', 'speed', 'groundspeed'):
                col_map[col] = 'Spd'
            elif col.lower() in ('vz', 'veld'):
                col_map[col] = 'VZ'
        if col_map:
            df = df.rename(columns=col_map)

        for col in ['Lat', 'Lng', 'Alt', 'Spd', 'VZ', 'TimeUS']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        if 'Lat' in df.columns and 'Lng' in df.columns:
            df = df.dropna(subset=['Lat', 'Lng'])
            df = df[(df['Lat'] != 0) | (df['Lng'] != 0)]

        if 'TimeUS' in df.columns:
            df = df.sort_values('TimeUS').reset_index(drop=True)

        if len(df) >= 2:
            return df

    return None


def get_imu_dataframe(dataframes):
    for name in ['IMU', 'IMU2', 'IMU3']:
        if name not in dataframes:
            continue

        df = dataframes[name].copy()

        col_map = {}
        for col in df.columns:
            cl = col.lower()
            if cl in ('accx', 'ax'): col_map[col] = 'AccX'
            elif cl in ('accy', 'ay'): col_map[col] = 'AccY'
            elif cl in ('accz', 'az'): col_map[col] = 'AccZ'
            elif cl in ('gyrx', 'gx'): col_map[col] = 'GyrX'
            elif cl in ('gyry', 'gy'): col_map[col] = 'GyrY'
            elif cl in ('gyrz', 'gz'): col_map[col] = 'GyrZ'
        if col_map:
            df = df.rename(columns=col_map)

        for col in df.columns:
            if col != 'TimeUS':
                df[col] = pd.to_numeric(df[col], errors='coerce')
        if 'TimeUS' in df.columns:
            df['TimeUS'] = pd.to_numeric(df['TimeUS'], errors='coerce')
            df = df.sort_values('TimeUS').reset_index(drop=True)

        return df

    return None
