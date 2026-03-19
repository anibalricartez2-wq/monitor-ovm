import streamlit as st
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

# API KEY (Plan Free: 100 consultas/día)
API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

# Refresco cada 20 minutos para no agotar los créditos de la API
st_autorefresh(interval=1200000, key="vigilancia_refresh")

# --- 2. MOTOR DE DATOS (OPTIMIZADO) ---
def obtener_datos_checkwx(icao_list):
    """Consulta todos los aeródromos en un solo pedido para ahorrar créditos."""
    icaos = ",".join(icao_list)
    url = f"https://api.checkwx.com/metar/{icaos}"
    headers = {"X-API-Key": API_KEY}
    try:
        res = requests.get(url, headers=headers, timeout=15).json()
        return res.get('data', [])
    except:
        return []

# --- 3. INTERFAZ ---
st.title("🖥️ Monitor Automático FIR SAVC")
st.write(f"Última actualización: **{datetime.now().strftime('%H:%M:%S')}**")

if st.button("🔄 Actualizar Ahora"):
    st.rerun()

# Obtenemos la lista de METARs
datos_raw = obtener_datos_checkwx(AERODROMOS)

# Creamos un diccionario para asignar cada reporte a su aeropuerto
reportes = {icao: "Esperando reporte..." for icao in AERODROMOS}
for metar in datos_raw:
    for icao in AERODROMOS:
        if icao in metar:
            reportes[icao] = metar

cols = st.columns(2)

for i, icao in enumerate(AERODROMOS):
    metar_texto = reportes[icao]
    
    with cols[i % 2]:
        # Lógica de alertas visuales
        status = "⚠️ RAFAGAS" if "G" in metar_texto else "✅ NORMAL"
        
        with st.expander(f"📍 {icao} - {status}", expanded=True):
            if "Esperando" in metar_texto:
                st.info(f"Buscando reporte de {icao} en red internacional...")
            else:
                st.success(f"**{metar_texto}**")
                if "G" in metar_texto:
                    st.warning("Se detectó viento con ráfagas.")

st.divider()
st.caption("Sistema de Vigilancia OVM - Datos vía CheckWX API.")
