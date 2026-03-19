import streamlit as st
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

# API KEY (Plan Free: 100 consultas/día)
API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

# --- 2. ESTRATEGIA DE CONSUMO (96 CONSULTAS/DÍA) ---
# Refresco cada 15 minutos (900.000 milisegundos)
st_autorefresh(interval=900000, key="vigilancia_refresh")

# Estética Profesional
hide_st_style = """
            <style>
            .stDeployButton {display:none;}
            footer {visibility: hidden;}
            .block-container {padding-top: 1.5rem;}
            [data-testid="stExpander"] {border: 1px solid #e0e0e0; border-radius: 8px;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- 3. MOTOR DE DATOS OPTIMIZADO ---
def obtener_datos_checkwx(icao_list):
    """Consulta todos los OACI en un solo pedido para ahorrar créditos."""
    icaos = ",".join(icao_list)
    url = f"https://api.checkwx.com/metar/{icaos}"
    headers = {"X-API-Key": API_KEY}
    try:
        res = requests.get(url, headers=headers, timeout=15).json()
        return res.get('data', [])
    except Exception:
        return []

# --- 4. INTERFAZ DE USUARIO ---
st.title("🖥️ Monitor Automático FIR SAVC")
st.write(f"Última actualización: **{datetime.now().strftime('%H:%M:%S')}**")

if st.button("🔄 Actualizar Ahora"):
    st.rerun()

# Obtenemos los reportes
datos_raw = obtener_datos_checkwx(AERODROMOS)

# Mapeamos los reportes a cada aeródromo
reportes = {icao: "Esperando reporte..." for icao in AERODROMOS}
for metar in datos_raw:
    for icao in AERODROMOS:
        if icao in metar:
            reportes[icao] = metar

# Mostramos en 2 columnas
cols = st.columns(2)

for i, icao in enumerate(AERODROMOS):
    metar_texto = reportes[icao]
    
    with cols[i % 2]:
        # Detección de ráfagas para la etiqueta
        status = "⚠️ RAFAGAS" if "G" in metar_texto else "✅ NORMAL"
        
        with st.expander(f"📍 {icao} - {status}", expanded=True):
            if "Esperando" in metar_texto:
                st.info(f"Buscando reporte de {icao}...")
            else:
                st.success(f"**{metar_texto}**")
                if "G" in metar_texto:
                    st.warning("Alerta: Se detectó viento con ráfagas.")

st.divider()
st.caption("Vigilancia OVM - Datos vía CheckWX API (Ciclo de 15 min)")
