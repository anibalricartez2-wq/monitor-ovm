import streamlit as st
import requests
import re
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Vigilancia OPMET - AVWX", page_icon="✈️", layout="wide")
st_autorefresh(interval=120000, key="datarefresh") # 2 minutos

# REEMPLAZA ESTO CON TU TOKEN DE AVWX
TOKEN = "gi50QuV83GkvYuzJn6x2VsSuX08YVVO6U_piFZ5lKmc" 
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

def diff_angular(d1, d2):
    diff = abs(d1 - d2)
    return diff if diff <= 180 else 360 - diff

def parse_viento(texto):
    if not texto or "Nil" in texto: return None, None, None
    match = re.search(r'(\d{3})(\d{2,3})(G\d{2,3})?KT', texto)
    if match:
        return int(match.group(1)), int(match.group(2)), (int(match.group(3)[1:]) if match.group(3) else 0)
    return None, None, None

def auditar(reporte, taf):
    alertas = []
    dr, vr, rr = parse_viento(reporte)
    dt, vt, rt = parse_viento(taf)
    if vr is not None and vt is not None:
        d_ang = diff_angular(dr, dt)
        if d_ang >= 60 and (vr >= 10 or vt >= 10): alertas.append(f"🚩 CRIT A: Giro {d_ang}°")
        if abs(vr - vt) >= 10: alertas.append(f"🚩 CRIT B: Dif Int {abs(vr-vt)}kt")
        if rr >= (vt + 10): alertas.append(f"🚩 CRIT C: Ráfaga {rr}kt")
    
    vis_match = re.search(r'\s(\d{4})\s', reporte)
    if vis_match:
        vis = int(vis_match.group(1))
        for u in [5000, 3000, 1500, 800]:
            if vis < u: alertas.append(f"🚩 CRIT E: Vis < {u}m"); break

    return alertas

st.title("🖥️ Monitor OPMET Real-Time (AVWX)")
st.write(f"Último intento: **{datetime.now().strftime('%H:%M:%S')}**")

cols = st.columns(2)
headers = {"Authorization": f"BEARER {TOKEN}"}

for i, icao in enumerate(AERODROMOS):
    try:
        # Pedimos METAR y TAF por separado para asegurar frescura
        r_m = requests.get(f"https://avwx.rest/api/metar/{icao}?options=raw", headers=headers).json()
        r_t = requests.get(f"https://avwx.rest/api/taf/{icao}?options=raw", headers=headers).json()
        
        metar = r_m.get('raw', 'Sin datos')
        taf = r_t.get('raw', 'Sin datos')
        
        # AVWX incluye el SPECI dentro de la consulta de METAR si es el reporte vigente
        alertas = auditar(metar, taf) if 'Sin datos' not in [metar, taf] else []
        
        with cols[i % 2]:
            estado = "⚠️ ALERTA" if alertas else "✅ OK"
            with st.expander(f"📍 {icao} - {estado}", expanded=True):
                st.caption("TAF:")
                st.code(taf)
                st.markdown(f"**ACTUAL:** `{metar}`")
                for a in alertas: st.error(a)
    except:
        st.error(f"Error en {icao}")