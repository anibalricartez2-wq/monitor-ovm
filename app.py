import streamlit as st
import requests
import re
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

# Aeródromos del FIR SAVC
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

if 'historial_alertas' not in st.session_state:
    st.session_state.historial_alertas = []

hide_st_style = """<style>.stDeployButton {display:none;} footer {visibility: hidden;} .block-container {padding-top: 1.5rem;}</style>"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# Refresco cada 15 min
st_autorefresh(interval=900000, key="datarefresh")

# --- 2. LÓGICA DE OBTENCIÓN DIRECTA (SMN ARGENTINA) ---
def get_smn_data():
    """Obtiene METARs directamente del servidor del SMN."""
    try:
        # Fuente oficial de texto plano del SMN
        url = "https://www.smn.gob.ar/adjuntos/metar.txt"
        response = requests.get(url, timeout=15)
        return response.text
    except:
        return ""

def extraer_reporte(icao, bloque_texto):
    """Busca el reporte específico de un OACI en el bloque del SMN."""
    lineas = bloque_texto.split('\n')
    for linea in lineas:
        if linea.startswith(icao):
            return linea.strip()
    return "Sin datos"

def diff_angular(d1, d2):
    diff = abs(d1 - d2)
    return diff if diff <= 180 else 360 - diff

def parse_viento(texto):
    if not texto or "Sin datos" in texto: return None, None, None
    if "00000KT" in texto: return 0, 0, 0
    match = re.search(r'(\d{3})(\d{2,3})(G\d{2,3})?KT', texto)
    if match:
        return int(match.group(1)), int(match.group(2)), (int(match.group(3)[1:]) if match.group(3) else 0)
    return None, None, None

def auditar(icao, metar):
    """
    Nota: Al usar la fuente directa del SMN, solo tenemos el METAR.
    Para auditar contra el TAF, necesitaríamos otra fuente o cargarlo manual.
    Por ahora, mostramos el reporte real para que la oficina no esté a ciegas.
    """
    return []

# --- 3. INTERFAZ ---
st.title("🖥️ Vigilancia FIR SAVC (Directo SMN)")

if st.session_state.historial_alertas:
    with st.expander("📊 Registro de Desvíos", expanded=False):
        df_log = pd.DataFrame(st.session_state.historial_alertas)
        st.table(df_log.tail(5))
        if st.button("🗑️ Limpiar"):
            st.session_state.historial_alertas = []; st.rerun()

st.write(f"Sincronizado con SMN: **{datetime.now().strftime('%H:%M:%S')}**")

# Botón de actualización manual
if st.button("🔄 Refrescar Datos"):
    st.rerun()

# Obtener bloque completo del SMN una sola vez
bloque_smn = get_smn_data()

cols = st.columns(2)

for i, icao in enumerate(AERODROMOS):
    metar = extraer_reporte(icao, bloque_smn)
    
    with cols[i % 2]:
        with st.expander(f"📍 {icao}", expanded=True):
            if metar != "Sin datos":
                if "SPECI" in metar:
                    st.warning(f"🔔 {metar}")
                else:
                    st.success(f"✅ {metar}")
            else:
                st.error(f"❌ {icao}: No reportado por SMN")

st.info("ℹ️ Esta versión conecta directo al SMN. Solo muestra METAR/SPECI actual.")