import streamlit as st
import requests
import re
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

hide_st_style = """<style>.stDeployButton {display:none;} footer {visibility: hidden;} .block-container {padding-top: 1.5rem;}</style>"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# Refresco cada 10 min
st_autorefresh(interval=600000, key="datarefresh")

# --- 2. LÓGICA DE DATOS (CON SALTADOR DE BLOQUEO) ---
def get_smn_proxy():
    """Usa un proxy para que el SMN no bloquee al servidor de Streamlit."""
    url_directa = "https://www.smn.gob.ar/adjuntos/metar.txt"
    # Este proxy actúa como intermediario para evitar el bloqueo de red
    proxy_url = f"https://api.allorigins.win/get?url={url_directa}"
    
    try:
        response = requests.get(proxy_url, timeout=20)
        if response.status_code == 200:
            # El proxy devuelve un JSON, extraemos el texto del SMN
            data = response.json()
            return data.get('contents', "")
    except Exception as e:
        return f"ERROR_RED: {str(e)}"
    return None

def buscar_reporte(icao, bloque):
    if not bloque or "ERROR_RED" in bloque: return "Falla de enlace"
    
    lineas = bloque.split('\n')
    for linea in lineas:
        if icao.upper() in linea.upper():
            return linea.strip().replace('\r', '')
    return "No reportado"

# --- 3. INTERFAZ ---
st.title("🖥️ Vigilancia FIR SAVC (Enlace Emergencia)")
st.write(f"Actualización vía Proxy: **{datetime.now().strftime('%H:%M:%S')}**")

if st.button("🔄 Refrescar ahora"):
    st.rerun()

st.divider()

# Obtenemos los datos con el saltador de bloqueo
datos_smn = get_smn_proxy()

cols = st.columns(2)

for i, icao in enumerate(AERODROMOS):
    metar = buscar_reporte(icao, datos_smn)
    
    with cols[i % 2]:
        with st.expander(f"📍 {icao}", expanded=True):
            if metar == "Falla de enlace":
                st.error("❌ Error de red (Servidor SMN bloqueado)")
            elif metar == "No reportado":
                st.info("⚪ Sin reporte actual")
            else:
                if "SPECI" in metar:
                    st.warning(f"🔔 {metar}")
                else:
                    st.success(f"✅ {metar}")

# PANEL DE CONTROL (Solo para verificar si llega algo)
with st.expander("🛠️ Ver qué está llegando del SMN"):
    if datos_smn:
        st.text_area("Datos recibidos:", datos_smn[:1000], height=150)
    else:
        st.write("No se recibió nada aún.")
