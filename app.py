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

# Refresco cada 15 min
st_autorefresh(interval=900000, key="datarefresh")

# --- 2. LÓGICA DE DATOS ---
def get_smn_data():
    """Obtiene el archivo de texto plano del SMN."""
    url = "https://www.smn.gob.ar/adjuntos/metar.txt"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.text
    except:
        return None
    return None

def buscar_reporte(icao, bloque):
    if not bloque: return "Error de conexión"
    lineas = bloque.split('\n')
    for linea in lineas:
        if icao.upper() in linea.upper():
            return linea.strip()
    return "No reportado"

# --- 3. INTERFAZ ---
st.title("🖥️ Vigilancia FIR SAVC (Directo SMN)")
st.write(f"Sincronizado: **{datetime.now().strftime('%H:%M:%S')}**")

if st.button("🔄 Actualizar Ahora"):
    st.rerun()

datos_crudos = get_smn_data()
cols = st.columns(2)

for i, icao in enumerate(AERODROMOS):
    reporte = buscar_reporte(icao, datos_crudos)
    with cols[i % 2]:
        with st.expander(f"📍 {icao}", expanded=True):
            if "Error" in reporte:
                st.error("❌ El SMN no responde.")
            elif "No reportado" in reporte:
                st.info("⚪ Sin reporte actual.")
            else:
                if "SPECI" in reporte:
                    st.warning(f"🔔 {reporte}")
                else:
                    st.success(f"✅ {reporte}")

st.divider()
st.caption("Fuente: Servicio Meteorológico Nacional (Argentina)")