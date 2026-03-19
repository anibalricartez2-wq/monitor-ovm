import streamlit as st
import requests
import re
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

if 'historial_alertas' not in st.session_state:
    st.session_state.historial_alertas = []

hide_st_style = """<style>.stDeployButton {display:none;} footer {visibility: hidden;} .block-container {padding-top: 1.5rem;}</style>"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# Refresco cada 10 min para no saturar
st_autorefresh(interval=600000, key="datarefresh")

# --- 2. LÓGICA DE OBTENCIÓN (SMN ARGENTINA) ---
def get_smn_data():
    """Busca en dos fuentes posibles del SMN."""
    urls = [
        "https://www.smn.gob.ar/adjuntos/metar.txt",
        "https://analisis.smn.gob.ar/dictados/metar.txt" # Fuente alternativa
    ]
    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200 and len(response.text) > 100:
                return response.text
        except:
            continue
    return ""

def extraer_reporte_flexible(icao, bloque_texto):
    """Busca el OACI en cualquier parte de la línea, ignorando mayúsculas/minúsculas."""
    if not bloque_texto:
        return "Error de conexión con SMN"
    
    lineas = bloque_texto.split('\n')
    for linea in lineas:
        # Buscamos si el código OACI aparece en la línea (ej: "SAVC 191400Z...")
        if icao.upper() in linea.upper():
            # Limpiamos caracteres extraños que a veces mete el SMN
            reporte = linea.strip().replace('\r', '')
            return reporte
    return "No reportado actualmente"

# --- 3. INTERFAZ ---
st.title("🖥️ Vigilancia FIR SAVC (SMN Directo)")

st.write(f"Sincronizado: **{datetime.now().strftime('%H:%M:%S')}**")

# Botón de actualización manual
if st.button("🔄 Refrescar ahora"):
    st.rerun()

# Obtener datos
bloque_smn = get_smn_data()

cols = st.columns(2)

for i, icao in enumerate(AERODROMOS):
    metar = extraer_reporte_flexible(icao, bloque_smn)
    
    with cols[i % 2]:
        with st.expander(f"📍 {icao}", expanded=True):
            if "No reportado" in metar:
                st.error(f"❌ {metar}")
            elif "Error" in metar:
                st.warning(f"⚠️ {metar}")
            else:
                if "SPECI" in metar:
                    st.warning(f"🔔 {metar}")
                else:
                    st.success(f"✅ {metar}")

# --- SECCIÓN DE DIAGNÓSTICO (Solo para vos) ---
st.divider()
with st.expander("🛠️ Depuración de Datos (Ver qué recibe el bot)"):
    if bloque_smn:
        st.text_area("Contenido recibido del SMN:", bloque_smn, height=200)
    else:
        st.error("No se pudo recibir ningún dato del SMN. Revisar conexión a internet de la PC.")