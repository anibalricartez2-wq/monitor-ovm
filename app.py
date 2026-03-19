import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Vigilancia FIR SAVC - EMERGENCIA", page_icon="✈️", layout="wide")
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

# Refresco automático cada 15 minutos (para no saturar)
st_autorefresh(interval=900000, key="emergencia_refresh")

# --- 2. MOTOR DE DATOS (RED GLOBAL ILIMITADA) ---
def obtener_metar_noaa(icao):
    """Consulta la base de datos de la NOAA (EE.UU.) que es gratuita."""
    try:
        url = f"https://www.aviationweather.gov/adds/dataserver_current/httpparam?dataSource=metars&requestType=retrieve&format=xml&stationString={icao}&hoursBeforeNow=2"
        res = requests.get(url, timeout=10)
        root = ET.fromstring(res.content)
        metar_node = root.find(".//raw_text")
        return metar_node.text if metar_node is not None else "Sin reporte"
    except:
        return "Error de conexión"

# --- 3. INTERFAZ ---
st.title("🖥️ Monitor de Emergencia FIR SAVC")
st.warning("⚠️ Modo de Contingencia Activo (Red NOAA Global)")
st.write(f"Sincronizado: **{datetime.now().strftime('%H:%M:%S')}**")

cols = st.columns(2)

for i, icao in enumerate(AERODROMOS):
    metar = obtener_metar_noaa(icao)
    
    with cols[i % 2]:
        with st.expander(f"📍 {icao}", expanded=True):
            if "Error" in metar or "Sin reporte" in metar:
                st.error(f"❌ {icao}: Dato no disponible")
            else:
                st.success(f"✅ **{metar}**")
                # Si el METAR tiene ráfagas (G), resaltarlo
                if "G" in metar:
                    st.warning("⚠️ Alerta de Ráfagas detectada")

st.divider()
st.caption("Este modo no consume créditos de API. Ideal para uso continuo en la oficina.")
