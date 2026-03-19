import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

hide_st_style = """<style>.stDeployButton {display:none;} footer {visibility: hidden;} .block-container {padding-top: 1.5rem;}</style>"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# Refresco cada 15 min
st_autorefresh(interval=900000, key="datarefresh")

# --- 2. FUNCIÓN DE SCRAPING (RASPADO WEB SMN) ---
def get_smn_scraping():
    """Extrae la tabla de METAR directamente de la web del SMN Argentina."""
    url = "https://www.smn.gob.ar/descarga-de-datos" # Página de datos abiertos
    # Simulamos ser un navegador real para que el SMN no nos bloquee
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        # Intentamos leer el archivo de texto que el SMN actualiza
        res = requests.get("https://www.smn.gob.ar/adjuntos/metar.txt", headers=headers, timeout=15)
        if res.status_code == 200:
            return res.text
    except:
        return None
    return None

def buscar_en_texto(icao, texto):
    if not texto: return "Error de conexión"
    lineas = texto.split('\n')
    for linea in lineas:
        if icao.upper() in linea.upper():
            return linea.strip()
    return "No reportado por SMN"

# --- 3. INTERFAZ ---
st.title("🖥️ Vigilancia FIR SAVC (Directo SMN)")

st.write(f"Sincronizado: **{datetime.now().strftime('%H:%M:%S')}**")

if st.button("🔄 Actualizar Ahora"):
    st.rerun()

st.divider()

# Obtenemos los datos una sola vez para todos los aeródromos
bloque_datos = get_smn_scraping()

cols = st.columns(2)

for i, icao in enumerate(AERODROMOS):
    reporte = buscar_en_texto(icao, bloque_datos)
    
    with cols[i % 2]:
        with st.expander(f"📍 {icao}", expanded=True):
            if "Error" in reporte:
                st.error("❌ El SMN bloqueó la conexión.")
            elif "No reportado" in reporte:
                st.info("⚪ Sin reporte en esta hora.")
            else:
                if "SPECI" in reporte:
                    st.warning(f"🔔 {reporte}")
                else:
                    st.success(f"✅ {reporte}")

# --- PANEL DE DIAGNÓSTICO ---
with st.expander("🛠️ Ver Datos Crudos del SMN"):
    if bloque_datos:
        st.text_area("Contenido del servidor SMN:", bloque_datos[:2000], height=250)
    else:
        st.error("No se pudo obtener el archivo metar.txt del SMN.")