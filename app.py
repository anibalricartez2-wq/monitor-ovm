import streamlit as st
import requests
import re
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

# Lista de aeródromos del FIR SAVC
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

# Ocultar menús innecesarios para una interfaz limpia en la oficina
hide_st_style = """
            <style>
            .stDeployButton {display:none;}
            footer {visibility: hidden;}
            .st-emotion-cache-1wbqy5l {display:none;}
            .block-container {padding-top: 1.5rem;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# REFRESCO AUTOMÁTICO: 10 MINUTOS (600.000 ms)
st_autorefresh(interval=600000, key="datarefresh")

# --- 2. LÓGICA DE OBTENCIÓN (TÚNEL DE EMERGENCIA ALLORIGINS) ---
def get_smn_data_emergency():
    """Obtiene los METARs del SMN usando un proxy para evitar bloqueos de SSL/IP."""
    url_base = "https://www.smn.gob.ar/adjuntos/metar.txt"
    # Usamos AllOrigins para que el servidor del SMN no bloquee la petición
    proxy_url = f"https://api.allorigins.win/get?url={url_base}"
    
    try:
        response = requests.get(proxy_url, timeout=20)
        if response.status_code == 200:
            # El proxy devuelve un JSON, el contenido real está en 'contents'
            data = response.json()
            return data.get('contents', "")
    except Exception as e:
        return f"ERROR_DE_CONEXION: {str(e)}"
    return ""

def extraer_reporte(icao, bloque_texto):
    """Busca la línea del aeródromo en el bloque de texto del SMN."""
    if not bloque_texto or "ERROR_DE_CONEXION" in bloque_texto:
        return "Falla de red"
    
    lineas = bloque_texto.split('\n')
    for linea in lineas:
        # Buscamos el OACI (ej. SAVC) ignorando mayúsculas
        if icao.upper() in linea.upper():
            return linea.strip().replace('\r', '')
    return "No reportado"

# --- 3. INTERFAZ DE USUARIO ---
st.title("🖥️ Vigilancia FIR SAVC (Modo Rescate)")

# Fila de información de tiempo
c_info, c_btn = st.columns([4, 1])
with c_info:
    st.write(f"Sincronizado vía Túnel: **{datetime.now().strftime('%H:%M:%S')}**")
with c_btn:
    if st.button("🔄 Refrescar Ahora"):
        st.rerun()

st.divider()

# Obtener datos de la fuente oficial argentina a través del proxy
bloque_smn = get_smn_data_emergency()

# Grilla de 2 columnas para los aeródromos
cols = st.columns(2)

for i, icao in enumerate(AERODROMOS):
    metar = extraer_reporte(icao, bloque_smn)
    
    with cols[i % 2]:
        with st.expander(f"📍 {icao}", expanded=True):
            if metar == "Falla de red":
                st.error("❌ Error: El servidor del SMN no responde.")
            elif metar == "No reportado":
                st.info("⚪ Sin reporte actual en el sistema SMN.")
            else:
                # Resaltamos si es un SPECI
                if "SPECI" in metar:
                    st.warning(f"🔔 {metar}")
                else:
                    st.success(f"✅ {metar}")

# --- SECCIÓN DE DIAGNÓSTICO (Para verificar qué llega) ---
st.divider()
with st.expander("🛠️ Panel de Depuración (Uso técnico)"):
    if bloque_smn and "ERROR" not in bloque_smn:
        st.write("Datos recibidos correctamente del SMN:")
        st.text_area("Muestra de texto crudo:", bloque_smn[:1500], height=200)
    else:
        st.error(f"Detalle del error: {bloque_smn}")
        st.info("Sugerencia: Si el error persiste, puede que el SMN tenga el servicio caído temporalmente.")

st.caption("Esta versión conecta directamente con el SMN Argentino. No requiere API Key.")