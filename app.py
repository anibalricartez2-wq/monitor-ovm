import streamlit as st
import requests
import re
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

# Estética original
hide_st_style = """<style>.stDeployButton {display:none;} footer {visibility: hidden;} .block-container {padding-top: 1.5rem;}</style>"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# Refresco cada 10 min
st_autorefresh(interval=600000, key="datarefresh")

# --- 2. LÓGICA DE DATOS (EL MOTOR QUE FUNCIONABA) ---
def obtener_bloque_smn():
    """Llamada al archivo original del SMN usando un puente para evitar bloqueos."""
    url_smn = "https://www.smn.gob.ar/adjuntos/metar.txt"
    # Usamos allorigins para saltar el firewall del SMN que bloquea a Streamlit
    proxy_url = f"https://api.allorigins.win/get?url={url_smn}"
    
    try:
        response = requests.get(proxy_url, timeout=15)
        if response.status_code == 200:
            # Extraemos el contenido del JSON que devuelve el proxy
            return response.json().get('contents', "")
    except Exception as e:
        return f"ERROR_RED: {str(e)}"
    return ""

def extraer_metar(icao, bloque):
    if not bloque or "ERROR_RED" in bloque:
        return "Falla de enlace"
    lineas = bloque.split('\n')
    for linea in lineas:
        if icao.upper() in linea.upper():
            return linea.strip().replace('\r', '')
    return "Sin reporte actual"

# --- 3. INTERFAZ ---
st.title("🖥️ Vigilancia FIR SAVC (Modo Restaurado)")
st.write(f"Última lectura: **{datetime.now().strftime('%H:%M:%S')}**")

if st.button("🔄 Forzar Actualización"):
    st.rerun()

st.divider()

# Traemos el bloque de texto completo una sola vez
datos_crudos = obtener_bloque_smn()

cols = st.columns(2)

for i, icao in enumerate(AERODROMOS):
    metar = extraer_metar(icao, datos_crudos)
    
    with cols[i % 2]:
        with st.expander(f"📍 {icao}", expanded=True):
            if metar == "Falla de enlace":
                st.error("❌ Error de red (Servidor SMN bloqueado)")
            elif metar == "Sin reporte actual":
                st.info("⚪ No hay datos en el archivo del SMN")
            else:
                if "SPECI" in metar:
                    st.warning(f"🔔 {metar}")
                else:
                    st.success(f"✅ {metar}")

# Consola de diagnóstico para tu tranquilidad
with st.expander("🛠️ Consola de Datos Crudos (Diagnóstico)"):
    if datos_crudos:
        st.text_area("Lo que llega del SMN:", datos_crudos[:1000], height=200)
    else:
        st.write("No se recibió información. Verificá la conexión.")
