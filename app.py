import streamlit as st
import requests
import re
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

st_autorefresh(interval=600000, key="datarefresh")

# --- 2. LÓGICA DE DATOS HÍBRIDA ---
def traer_datos(icao):
    """Intenta CheckWX, si falla o viene vacío, intenta fuente de emergencia."""
    headers = {"X-API-Key": API_KEY}
    metar, taf = "Sin datos", "Sin datos"
    
    try:
        # Intento METAR
        res_m = requests.get(f"https://api.checkwx.com/metar/{icao}", headers=headers, timeout=8).json()
        if res_m.get('data'):
            metar = res_m['data'][0]
        else:
            # FUENTE DE EMERGENCIA (AVWX) si CheckWX viene vacío
            res_alt = requests.get(f"https://avwx.rest/api/metar/{icao}?format=json", timeout=8).json()
            metar = res_alt.get('raw', "Sin reporte")
            
        # Intento TAF
        res_t = requests.get(f"https://api.checkwx.com/taf/{icao}", headers=headers, timeout=8).json()
        if res_t.get('data'):
            taf = res_t['data'][0]
        else:
            res_t_alt = requests.get(f"https://avwx.rest/api/taf/{icao}?format=json", timeout=8).json()
            taf = res_t_alt.get('raw', "Sin reporte TAF")
            
    except:
        pass
    return metar, taf

# --- 3. INTERFAZ ---
st.title("🛡️ Sistema de Vigilancia (Dual Link)")
st.write(f"Sincronizado: **{datetime.now().strftime('%H:%M:%S')}**")

cols = st.columns(2)

for i, icao in enumerate(AERODROMOS):
    m, t = traer_datos(icao)
    
    with cols[i % 2]:
        color = "✅" if "Sin datos" not in m else "❌"
        with st.expander(f"📍 {icao} {color}", expanded=True):
            if "Sin reporte" in m and "Sin reporte" in t:
                st.error("⚠️ Estación fuera de línea en circuitos internacionales.")
            else:
                st.caption("TAF:")
                st.code(t)
                st.markdown(f"**METAR:** `{m}`")

st.divider()
st.caption("Si ves 'Sin datos', verificá la activación de tu cuenta CheckWX en tu e-mail.")
