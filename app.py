import streamlit as st
import requests
import re
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

# API KEY PROPORCIONADA
API_KEY = "1c208dc6ec9442cd97575bdf518fb4a9"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

# Estética de Monitor de Torre
hide_st_style = """
            <style>
            .stDeployButton {display:none;}
            footer {visibility: hidden;}
            .block-container {padding-top: 1.5rem;}
            [data-testid="stExpander"] {border: 1px solid #d1d1d1; border-radius: 10px;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# Refresco cada 10 minutos (600.000 ms)
st_autorefresh(interval=600000, key="datarefresh")

# --- 2. LÓGICA DE AUDITORÍA ---
def diff_angular(d1, d2):
    diff = abs(d1 - d2)
    return diff if diff <= 180 else 360 - diff

def parse_viento(texto):
    if not texto or "Sin datos" in texto: return None, None, None
    if "00000KT" in texto: return 0, 0, 0
    match = re.search(r'(\d{3})(\d{2,3})(G\d{2,3})?KT', texto)
    if match:
        d = int(match.group(1))
        v = int(match.group(2))
        r = int(match.group(3)[1:]) if match.group(3) else 0
        return d, v, r
    return None, None, None

def auditar(icao, metar, taf):
    alertas = []
    dm, vm, rm = parse_viento(metar)
    dt, vt, rt = parse_viento(taf)
    
    if vm is not None and vt is not None:
        # CRIT A: Giro >= 60° con viento >= 10kt
        if vm >= 10 or vt >= 10:
            da = diff_angular(dm, dt)
            if da >= 60:
                alertas.append(f"🔴 CRIT A: Giro de {da}°")
        
        # CRIT B: Dif Intensidad >= 10kt
        dif_i = abs(vm - vt)
        if dif_i >= 10:
            alertas.append(f"🟠 CRIT B: Dif. Int. {dif_i}kt")
            
    return alertas

# --- 3. INTERFAZ ---
st.title("🖥️ Vigilancia Profesional FIR SAVC")
st.write(f"Última actualización: **{datetime.now().strftime('%H:%M:%S')}**")

if st.button("🔄 Actualizar Manual"):
    st.rerun()

headers = {"X-API-Key": API_KEY}
cols = st.columns(2)

for i, icao in enumerate(AERODROMOS):
    try:
        # Llamadas a la API
        res_m = requests.get(f"https://api.checkwx.com/metar/{icao}", headers=headers, timeout=10).json()
        metar = res_m.get('data', ['Sin datos'])[0]
        
        res_t = requests.get(f"https://api.checkwx.com/taf/{icao}", headers=headers, timeout=10).json()
        taf = res_t.get('data', ['Sin datos'])[0]
        
        alertas = auditar(icao, metar, taf) if "Sin datos" not in [metar, taf] else []

        with cols[i % 2]:
            status_label = "⚠️ ALERTA" if alertas else "✅ NORMAL"
            with st.expander(f"📍 {icao} - {status_label}", expanded=True):
                if "Sin datos" in taf:
                    st.caption("TAF: No disponible")
                else:
                    st.caption("TAF VIGENTE:")
                    st.code(taf)
                
                st.markdown(f"**METAR:** `{metar}`")
                
                for a in alertas:
                    st.error(a)
    except:
        with cols[i % 2]:
            st.warning(f"📍 {icao}: Error de conexión temporal.")

st.divider()
st.info("💡 Este monitor compara automáticamente el METAR actual contra el TAF para detectar desvíos críticos.")
