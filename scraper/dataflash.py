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
        col_map = {}
        for c in df.columns:
            cl = c.lower()
            if cl in ('lat', 'latitude'): col_map[c] = 'Lat'
            elif cl in ('lng', 'lon', 'longitude'): col_map[c] = 'Lng'
            elif cl in ('alt', 'altitude'): col_map[c] = 'Alt'
            elif cl in ('spd', 'speed', 'groundspeed'): col_map[c] = 'Spd'
            elif cl in ('vz', 'veld'): col_map[c] = 'VZ'
        df = df.rename(columns=col_map)
        for c in ['Lat', 'Lng', 'Alt', 'Spd', 'VZ', 'TimeUS']:
            if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
        if 'Lat' in df.columns: return df.dropna(subset=['Lat', 'Lng']).sort_values('TimeUS').reset_index(drop=True)
    return None

def get_imu_dataframe(dataframes):
    for name in ['IMU', 'IMU2', 'IMU3']:
        if name not in dataframes: continue
        df = dataframes[name].copy()
        col_map = {}
        for c in df.columns:
            cl = c.lower()
            if cl in ('accx', 'ax'): col_map[c] = 'AccX'
            elif cl in ('accy', 'ay'): col_map[c] = 'AccY'
            elif cl in ('accz', 'az'): col_map[c] = 'AccZ'
        df = df.rename(columns=col_map)
        for c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
        return df.sort_values('TimeUS').reset_index(drop=True)
    return None

def get_attitude_dataframe(dataframes):
    if 'ATT' in dataframes:
        df = dataframes['ATT'].copy()
        for c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
        return df.sort_values('TimeUS').reset_index(drop=True)
    return None

def get_vibe_dataframe(dataframes):
    if 'VIBE' in dataframes:
        df = dataframes['VIBE'].copy()
        for c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
        return df.sort_values('TimeUS').reset_index(drop=True)
    return None
