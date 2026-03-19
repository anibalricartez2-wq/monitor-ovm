import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

hide_st_style = """<style>.stDeployButton {display:none;} footer {visibility: hidden;} .block-container {padding-top: 1.5rem;}</style>"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# Refresco cada 10 min
st_autorefresh(interval=600000, key="datarefresh")

# --- 2. LÓGICA DE DATOS INTERNACIONAL (NOAA ADDS) ---
def get_noaa_data(icao):
    """Obtiene METAR de la base de datos global de aviación (EE.UU.)."""
    try:
        url = f"https://www.aviationweather.gov/adds/dataserver_current/httpparam?dataSource=metars&requestType=retrieve&format=xml&stationString={icao}&hoursBeforeNow=2"
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            # Buscamos el texto del METAR en el XML
            metar_element = root.find(".//raw_text")
            if metar_element is not None:
                return metar_element.text
    except Exception as e:
        return f"Error técnico: {str(e)}"
    return "No disponible en red internacional"

# --- 3. INTERFAZ ---
st.title("🖥️ Vigilancia FIR SAVC (Red Global ADDS)")
st.write(f"Sincronizado con Servidor Global: **{datetime.now().strftime('%H:%M:%S')}**")

if st.button("🔄 Forzar Refresco"):
    st.rerun()

st.divider()

cols = st.columns(2)

for i, icao in enumerate(AERODROMOS):
    metar = get_noaa_data(icao)
    
    with cols[i % 2]:
        with st.expander(f"📍 {icao}", expanded=True):
            if "Error" in metar:
                st.error("❌ Falla de conexión con el servidor global.")
            elif "No disponible" in metar:
                st.info(f"⚪ {icao}: Sin reporte en circuito internacional.")
            else:
                if "SPECI" in metar:
                    st.warning(f"🔔 {metar}")
                else:
                    st.success(f"✅ {metar}")

st.info("ℹ️ Esta fuente es la NOAA (EE.UU.). Si un aeródromo local no figura, es porque el SMN no exportó el dato al mundo.")
