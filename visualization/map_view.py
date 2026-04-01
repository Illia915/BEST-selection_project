import folium
import pandas as pd
import numpy as np


def build_map(gps_df):
    lats = pd.to_numeric(gps_df['Lat'], errors='coerce').values
    lngs = pd.to_numeric(gps_df['Lng'], errors='coerce').values

    center_lat = float(np.nanmean(lats))
    center_lng = float(np.nanmean(lngs))

    m = folium.Map(location=[center_lat, center_lng], zoom_start=16, tiles='OpenStreetMap')

    folium.TileLayer('CartoDB positron', name='Світла карта').add_to(m)
    folium.TileLayer('CartoDB dark_matter', name='Темна карта').add_to(m)

    if 'Spd' in gps_df.columns:
        speeds = pd.to_numeric(gps_df['Spd'], errors='coerce').fillna(0).values
        max_spd = speeds.max() if speeds.max() > 0 else 1.0

        for idx in range(len(lats) - 1):
            spd_norm = speeds[idx] / max_spd
            color = _speed_to_color(spd_norm)

            tooltip = f"Швидкість: {speeds[idx]:.1f} м/с"
            if 'Alt' in gps_df.columns:
                alt = pd.to_numeric(gps_df['Alt'], errors='coerce').iloc[idx]
                tooltip += f"<br>Висота: {alt:.1f} м"

            folium.PolyLine(
                locations=[[lats[idx], lngs[idx]], [lats[idx + 1], lngs[idx + 1]]],
                color=color,
                weight=4,
                opacity=0.85,
                tooltip=tooltip,
            ).add_to(m)
    else:
        coords = [[float(la), float(lo)] for la, lo in zip(lats, lngs)
                  if not (np.isnan(la) or np.isnan(lo))]
        folium.PolyLine(
            locations=coords,
            color='royalblue',
            weight=4,
            opacity=0.85,
            tooltip='Траєкторія польоту',
        ).add_to(m)

    folium.Marker(
        location=[float(lats[0]), float(lngs[0])],
        popup=folium.Popup(_make_popup(gps_df, 0), max_width=250),
        tooltip='Старт',
        icon=folium.Icon(color='green', icon='play', prefix='fa'),
    ).add_to(m)

    folium.Marker(
        location=[float(lats[-1]), float(lngs[-1])],
        popup=folium.Popup(_make_popup(gps_df, -1), max_width=250),
        tooltip='Фінш',
        icon=folium.Icon(color='red', icon='stop', prefix='fa'),
    ).add_to(m)

    step = max(1, len(lats) // 20)
    for idx in range(0, len(lats), step):
        if np.isnan(lats[idx]) or np.isnan(lngs[idx]):
            continue
        tooltip_text = f"Точка {idx}"
        if 'Alt' in gps_df.columns:
            alt = pd.to_numeric(gps_df['Alt'], errors='coerce').iloc[idx]
            tooltip_text += f" | Висота: {alt:.0f} м"
        if 'Spd' in gps_df.columns:
            spd = pd.to_numeric(gps_df['Spd'], errors='coerce').iloc[idx]
            tooltip_text += f" | Швидкість: {spd:.1f} м/с"

        folium.CircleMarker(
            location=[float(lats[idx]), float(lngs[idx])],
            radius=4,
            color='white',
            fill=True,
            fill_color='dodgerblue',
            fill_opacity=0.9,
            tooltip=tooltip_text,
        ).add_to(m)

    if 'Spd' in gps_df.columns:
        max_spd_val = float(pd.to_numeric(gps_df['Spd'], errors='coerce').max())
        _add_speed_legend(m, max_spd_val)

    folium.LayerControl().add_to(m)

    valid = [(float(la), float(lo)) for la, lo in zip(lats, lngs)
             if not (np.isnan(la) or np.isnan(lo))]
    if valid:
        m.fit_bounds([[min(p[0] for p in valid), min(p[1] for p in valid)],
                      [max(p[0] for p in valid), max(p[1] for p in valid)]])

    return m


def _speed_to_color(norm):
    if norm < 0.5:
        r = int(255 * norm * 2)
        g = 200
        b = 0
    else:
        r = 255
        g = int(200 * (1 - (norm - 0.5) * 2))
        b = 0
    return f'#{r:02x}{g:02x}{b:02x}'


def _make_popup(gps_df, idx):
    rows = []
    for col in ['Lat', 'Lng', 'Alt', 'Spd', 'TimeUS']:
        if col in gps_df.columns:
            val = pd.to_numeric(gps_df[col], errors='coerce').iloc[idx]
            label = {'Lat': 'Широта', 'Lng': 'Довгота', 'Alt': 'Висота (м)',
                     'Spd': 'Швидкість (м/с)', 'TimeUS': 'Час (мкс)'}.get(col, col)
            rows.append(f'<tr><td><b>{label}</b></td><td>{val:.4f}</td></tr>')
    return f'<table>{"".join(rows)}</table>'


def _add_speed_legend(m, max_spd):
    legend_html = f"""
    <div style="
        position: fixed; bottom: 30px; right: 10px; z-index: 1000;
        background: white; padding: 10px 14px; border-radius: 8px;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.3); font-family: sans-serif;
        font-size: 12px; min-width: 140px;">
        <b>Швидкість</b><br>
        <div style="
            background: linear-gradient(to right, #00c800, #ffcc00, #ff0000);
            height: 12px; border-radius: 4px; margin: 6px 0;">
        </div>
        <div style="display:flex; justify-content:space-between;">
            <span>0 м/с</span>
            <span>{max_spd:.1f} м/с</span>
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))


def generate_kml(gps_df):
    """
    Швидко генерує KML-файл з датафрейму GPS для перегляду в Google Earth.
    Використовує векторизацію Pandas для максимальної продуктивності.
    """
    df = gps_df.copy()
    
    # Відфільтровуємо порожні координати
    df = df.dropna(subset=['Lat', 'Lng'])
    
    if 'Alt' not in df.columns:
        df['Alt'] = 0.0
        
    # Формуємо рядок координат у форматі: lon,lat,alt
    coords = df[['Lng', 'Lat', 'Alt']].astype(str).agg(','.join, axis=1)
    coords_str = '\n                '.join(coords)
    
    kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Траєкторія польоту БПЛА</name>
    <Style id="flightPathStyle">
      <LineStyle>
        <color>7fff0000</color> <width>4</width>
      </LineStyle>
      <PolyStyle>
        <color>7f00ff00</color>
      </PolyStyle>
    </Style>
    <Placemark>
      <name>Маршрут</name>
      <styleUrl>#flightPathStyle</styleUrl>
      <LineString>
        <extrude>1</extrude>
        <tessellate>1</tessellate>
        <altitudeMode>absolute</altitudeMode>
        <coordinates>
                {coords_str}
        </coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>"""
    return kml
