import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

# Estética de Monitor
hide_st_style = """
            <style>
            .stDeployButton {display:none;}
            footer {visibility: hidden;}
            .block-container {padding-top: 1.5rem;}
            [data-testid="stExpander"] {border: 1px solid #e0e0e0; border-radius: 8px;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# Refresco cada 10 minutos (Sin riesgo de bloqueo)
st_autorefresh(interval=600000, key="datarefresh")

# --- 2. MOTOR DE DATOS (RED GLOBAL ILIMITADA) ---
def obtener_metar_noaa(icao):
    """Consulta la base de datos de la NOAA que es gratuita e ilimitada."""
    try:
        # Buscamos las últimas 2 horas de datos para asegurar que traiga el reporte vigente
        url = f"https://www.aviationweather.gov/adds/dataserver_current/httpparam?dataSource=metars&requestType=retrieve&format=xml&stationString={icao}&hoursBeforeNow=2"
        res = requests.get(url, timeout=10)
        root = ET.fromstring(res.content)
        # Buscamos el nodo que contiene el texto raw del METAR
        metar_node = root.find(".//raw_text")
        return metar_node.text if metar_node is not None else "Sin reporte reciente"
    except Exception:
        return "Error de conexión"

# --- 3. INTERFAZ ---
st.title("🖥️ Monitor de Vigilancia FIR SAVC")
st.write(f"Sincronizado: **{datetime.now().strftime('%H:%M:%S')}**")

if st.button("🔄 Actualizar Ahora"):
    st.rerun()

cols = st.columns(2)

for i, icao in enumerate(AERODROMOS):
    metar = obtener_metar_noaa(icao)
    
    with cols[i % 2]:
        # Si el METAR tiene ráfagas (G), le ponemos un color de advertencia
        status = "⚠️ RAFAGAS" if "G" in metar else "✅ NORMAL"
        
        with st.expander(f"📍 {icao} - {status}", expanded=True):
            if "Sin reporte" in metar or "Error" in metar:
                st.info(f"Esperando reporte de {icao}...")
            else:
                st.success(f"**{metar}**")
                
                # Alerta visual rápida para viento fuerte
                if "G" in metar:
                    st.warning("Detectado viento con ráfagas.")

st.divider()
st.caption("Fuente de datos: NOAA Aviation Weather Service (Uso ilimitado)")
