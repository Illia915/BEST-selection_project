import pandas as pd

def parse_log(filepath):
    from pymavlink import DFReader
    log = DFReader.DFReader_binary(filepath)
    records = {}
    while True:
        msg = log.recv_msg()
        if msg is None: break
        msg_type = msg.get_type()
        if msg_type in ('FMT', 'FMTU', 'MULT', 'UNIT', 'PARM'): continue
        try:
            row = msg.to_dict()
            row.pop('mavpackettype', None)
        except: continue
        if msg_type not in records: records[msg_type] = []
        records[msg_type].append(row)
    return {name: pd.DataFrame(rows) for name, rows in records.items() if rows}

def get_gps_dataframe(dataframes):
    for name in ['GPS', 'GPS2', 'GNSS']:
        if name not in dataframes: continue
        df = dataframes[name].copy()
        col_map = {c: n for c, n in zip(df.columns, ['Lat', 'Lng', 'Alt', 'Spd', 'VZ']) if c.lower() in ('lat', 'latitude', 'lng', 'lon', 'longitude', 'alt', 'altitude', 'spd', 'speed', 'groundspeed', 'vz', 'veld')}
        df = df.rename(columns=col_map)
        for c in ['Lat', 'Lng', 'Alt', 'Spd', 'VZ', 'TimeUS']:
            if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
        if 'Lat' in df.columns: return df.dropna(subset=['Lat', 'Lng']).sort_values('TimeUS').reset_index(drop=True)
    return None

def get_imu_dataframe(dataframes):
    for name in ['IMU', 'IMU2', 'IMU3']:
        if name not in dataframes: continue
        df = dataframes[name].copy()
        col_map = {c: n for c, n in zip(df.columns, ['AccX', 'AccY', 'AccZ', 'GyrX', 'GyrY', 'GyrZ']) if c.lower() in ('accx', 'ax', 'accy', 'ay', 'accz', 'az', 'gyrx', 'gx', 'gyry', 'gy', 'gyrz', 'gz')}
        df = df.rename(columns=col_map)
        for c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
        return df.sort_values('TimeUS').reset_index(drop=True)
    return None

def get_attitude_dataframe(dataframes):
    if 'ATT' in dataframes:
        df = dataframes['ATT'].copy()
        for c in ['Roll', 'Pitch', 'Yaw', 'TimeUS']:
            if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
        return df.sort_values('TimeUS').reset_index(drop=True)
    return None
