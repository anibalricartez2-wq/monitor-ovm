import streamlit as st
import requests
import re
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

# API KEY
API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

hide_st_style = """
            <style>
            .stDeployButton {display:none;}
            footer {visibility: hidden;}
            .block-container {padding-top: 1.5rem;}
            [data-testid="stExpander"] {border: 1px solid #e0e0e0; border-radius: 8px;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

st_autorefresh(interval=600000, key="datarefresh")

# --- 2. FUNCIONES TÉCNICAS ---
def diff_angular(d1, d2):
    diff = abs(d1 - d2)
    return diff if diff <= 180 else 360 - diff

def parse_viento(texto):
    if not texto or "Esperando" in texto or "No disponible" in texto: 
        return None, None, None
    if "00000KT" in texto: 
        return 0, 0, 0
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
        if vm >= 10 or vt >= 10:
            da = diff_angular(dm, dt)
            if da >= 60:
                alertas.append(f"🔴 CRIT A: Giro de {da}°")
        dif_i = abs(vm - vt)
        if dif_i >= 10:
            alertas.append(f"🟠 CRIT B: Dif. Int. {dif_i}kt")
    return alertas

# --- 3. INTERFAZ ---
st.title("Monitor de Vigilancia FIR SAVC")
st.write(f"Sincronizado: **{datetime.now().strftime('%H:%M:%S')}**")

if st.button("🔄 Actualizar Ahora"):
    st.rerun()

headers = {"X-API-Key": API_KEY}
cols = st.columns(2)

for i, icao in enumerate(AERODROMOS):
    try:
        # Petición METAR
        res_m = requests.get(f"https://api.checkwx.com/metar/{icao}", headers=headers, timeout=10).json()
        metar = res_m.get('data', ['Esperando METAR...'])[0]
        
        # Petición TAF
        res_t = requests.get(f"https://api.checkwx.com/taf/{icao}", headers=headers, timeout=10).json()
        taf = res_t.get('data', ['TAF No disponible'])[0]
        
        alertas = auditar(icao, metar, taf)

        with cols[i % 2]:
            status = "⚠️ ALERTA" if alertas else "✅ NORMAL"
            with st.expander(f"📍 {icao} - {status}", expanded=True):
                if "No disponible" in taf:
                    st.info("No hay TAF cargado.")
                else:
                    st.caption("TAF VIGENTE:")
                    st.code(taf)
                
                st.markdown(f"**METAR:** `{metar}`")
                for a in alertas:
                    st.error(a)
    except Exception as e:
        with cols[i % 2]:
            st.error(f"📍 {icao}: Error de conexión. ({e})")

st.divider()
st.caption("Vigilancia meteorológica para despacho.")
