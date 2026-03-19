import streamlit as st
import requests
import re
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

# COLOCÁ ACÁ LA LLAVE QUE GENERASTE
API_KEY = "1c208dc6ec9442cd97575bdf518fb4a9" 
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

if 'historial_alertas' not in st.session_state:
    st.session_state.historial_alertas = []

st_autorefresh(interval=900000, key="datarefresh") # 15 minutos

# --- 2. LÓGICA TÉCNICA (AUDITORÍA) ---
def diff_angular(d1, d2):
    diff = abs(d1 - d2)
    return diff if diff <= 180 else 360 - diff

def parse_viento(texto):
    if not texto or "Sin datos" in texto: return None, None, None
    if "00000KT" in texto: return 0, 0, 0
    match = re.search(r'(\d{3})(\d{2,3})(G\d{2,3})?KT', texto)
    if match:
        return int(match.group(1)), int(match.group(2)), (int(match.group(3)[1:]) if match.group(3) else 0)
    return None, None, None

def auditar(icao, reporte, taf):
    alertas = []
    dr, vr, rr = parse_viento(reporte)
    dt, vt, rt = parse_viento(taf)
    if vr is not None and vt is not None:
        if vr >= 10 or vt >= 10:
            d_ang = diff_angular(dr, dt)
            if d_ang >= 60: alertas.append(f"CRIT A: Giro {d_ang}°")
        if abs(vr - vt) >= 10: alertas.append(f"CRIT B: Dif Int {abs(vr-vt)}kt")
    return alertas

# --- 3. INTERFAZ ---
st.title("✈️ Vigilancia Profesional FIR SAVC")
st.write(f"Sincronizado: **{datetime.now().strftime('%H:%M:%S')}**")

if API_KEY == "1c208dc6ec9442cd97575bdf518fb4a9":
    st.warning("⚠️ Por favor, ingresá tu API Key de CheckWX en el código.")
    st.stop()

headers = {"X-API-Key": API_KEY}
cols = st.columns(2)

for i, icao in enumerate(AERODROMOS):
    try:
        # Pedimos METAR y TAF
        res_m = requests.get(f"https://api.checkwx.com/metar/{icao}", headers=headers).json()
        metar = res_m.get('data', ['Sin datos'])[0]
        res_t = requests.get(f"https://api.checkwx.com/taf/{icao}", headers=headers).json()
        taf = res_t.get('data', ['Sin datos'])[0]
        
        alertas = auditar(icao, metar, taf)

        with cols[i % 2]:
            estado = "⚠️ ALERTA" if alertas else "✅ OK"
            with st.expander(f"📍 {icao} - {estado}", expanded=True):
                st.caption("TAF:")
                st.code(taf)
                st.markdown(f"**METAR:** `{metar}`")
                for a in alertas: st.error(a)
    except:
        st.error(f"Error cargando {icao}")
