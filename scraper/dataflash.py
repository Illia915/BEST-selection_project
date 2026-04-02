import pandas as pd
import logging

logger = logging.getLogger(__name__)

def parse_log(filepath):
    from pymavlink import DFReader
    
    try:
        log = DFReader.DFReader_binary(filepath)
    except FileNotFoundError:
        logger.error(f"Log file not found: {filepath}")
        raise
    except Exception as e:
        logger.error(f"Failed to open log file: {e}")
        raise
    
    records = {}
    msg_count = 0
    error_count = 0
    
    while True:
        try:
            msg = log.recv_msg()
            if msg is None:
                break
            msg_type = msg.get_type()
            if msg_type in ('FMT', 'FMTU', 'MULT', 'UNIT', 'PARM'):
                continue
            try:
                row = msg.to_dict()
                row.pop('mavpackettype', None)
            except Exception as e:
                error_count += 1
                logger.debug(f"Failed to parse message {msg_type}: {e}")
                continue
            if msg_type not in records:
                records[msg_type] = []
            records[msg_type].append(row)
            msg_count += 1
        except Exception as e:
            error_count += 1
            logger.warning(f"Error reading message: {e}")
            continue
    
    if error_count > 0:
        logger.warning(f"Parsed {msg_count} messages with {error_count} errors")
    
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
            elif cl in ('gyrx', 'gx'): col_map[c] = 'GyrX'
            elif cl in ('gyry', 'gy'): col_map[c] = 'GyrY'
            elif cl in ('gyrz', 'gz'): col_map[c] = 'GyrZ'
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

def get_baro_dataframe(dataframes):
    for name in ['BARO', 'BAR2', 'BAR3']:
        if name not in dataframes: continue
        df = dataframes[name].copy()
        col_map = {}
        for c in df.columns:
            cl = c.lower()
            if cl in ('alt', 'altitude'): col_map[c] = 'Alt'
            elif cl in ('press', 'pressure'): col_map[c] = 'Press'
            elif cl in ('temp', 'temperature'): col_map[c] = 'Temp'
        df = df.rename(columns=col_map)
        for c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
        return df.sort_values('TimeUS').reset_index(drop=True)
    return None

def get_battery_dataframe(dataframes):
    for name in ['BAT', 'BAT2', 'CURR']:
        if name not in dataframes: continue
        df = dataframes[name].copy()
        col_map = {}
        for c in df.columns:
            cl = c.lower()
            if cl in ('volt', 'voltage', 'v'): col_map[c] = 'Volt'
            elif cl in ('curr', 'current', 'i'): col_map[c] = 'Curr'
            elif cl in ('currtot', 'consumedah', 'mah'): col_map[c] = 'CurrTot'
        df = df.rename(columns=col_map)
        for c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
        return df.sort_values('TimeUS').reset_index(drop=True)
    return None

def get_mode_dataframe(dataframes):
    if 'MODE' in dataframes:
        df = dataframes['MODE'].copy()
        if 'TimeUS' in df.columns: df['TimeUS'] = pd.to_numeric(df['TimeUS'], errors='coerce')
        return df.sort_values('TimeUS').reset_index(drop=True)
    return None
