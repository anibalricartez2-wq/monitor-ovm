import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

# JS: Script "Fantasma" que borra rastros de edición cada segundo
components.html("""
    <script>
    function cleanInterface() {
        const toHide = [
            '[data-testid="stHeaderActionElements"]', 
            '#MainMenu', 
            '.stDeployButton',
            'header'
        ];
        toHide.forEach(s => {
            const el = window.parent.document.querySelectorAll(s);
            el.forEach(e => e.style.display = 'none');
        });
    }
    setInterval(cleanInterface, 1000);
    </script>
    """, height=0)

# CSS: Rescate de la flecha de configuración
st.markdown("""
    <style>
    footer {visibility: hidden !important;}
    [data-testid="stSidebarCollapsedControl"] {
        display: flex !important;
        position: fixed !important;
        top: 10px !important;
        left: 10px !important;
        z-index: 1000000 !important;
        background-color: rgba(255, 255, 255, 0.1) !important;
        border-radius: 5px !important;
    }
    .block-container {padding-top: 2rem !important;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Configuración")
    tema = st.selectbox("Modo de Pantalla:", ["Sistema", "Día", "Noche"], index=0)
    st.divider()
    st.info("Actualización: Cada 30 minutos")
    st.caption("🔒 Acceso Restringido - FIR SAVC")

# --- 3. LÓGICA TÉCNICA ---
API_KEY = "8e7917816866402688f805f637eb54d3" # Recomiendo mover esto a Secrets
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

# REFRESH CADA 30 MINUTOS
st_autorefresh(interval=1800000, key="refresh_30m")

if 'historial' not in st.session_state:
    st.session_state.historial = pd.DataFrame(columns=["Fecha_Hora", "OACI", "METAR", "Estado"])

def obtener_datos(icao_list):
    icaos = ",".join(icao_list)
    headers = {"X-API-Key": API_KEY}
    try:
        m_res = requests.get(f"https://api.checkwx.com/metar/{icaos}", headers=headers, timeout=10).json().get('data', [])
        t_res = requests.get(f"https://api.checkwx.com/taf/{icaos}", headers=headers, timeout=10).json().get('data', [])
        return m_res, t_res
    except: return [], []

def analizar_alerta(metar_txt):
    if re.search(r'G\d{2}', metar_txt):
        return "RAFAGAS", "⚠️ ALERTA: Ráfagas."
    return "NORMAL", "✅ Normal."

# --- 4. INTERFAZ ---
st.title("🖥️ Monitor FIR SAVC - Vigilancia Meteorológica")
ahora = datetime.now().strftime('%H:%M:%S')
st.write(f"Última lectura: **{ahora}**")

metars, tafs = obtener_datos(AERODROMOS)
datos = {icao: {"metar": "Sin datos", "taf": "Sin datos"} for icao in AERODROMOS}
for m in metars:
    for icao in AERODROMOS:
        if icao in m: datos[icao]["metar"] = m
for t in tafs:
    for icao in AERODROMOS:
        if icao in t: datos[icao]["taf"] = t

cols = st.columns(2)
for i, icao in enumerate(AERODROMOS):
    info = datos[icao]
    estado, motivo = analizar_alerta(info["metar"])
    with cols[i % 2]:
        with st.expander(f"{icao} - {estado}", expanded=True):
            st.code(info["metar"])
            st.code(info["taf"])
            if "SAV" in info["metar"]:
                nueva = pd.DataFrame([{"Fecha_Hora": ahora, "OACI": icao, "METAR": info["metar"], "Estado": estado}])
                st.session_state.historial = pd.concat([st.session_state.historial, nueva], ignore_index=True).drop_duplicates(subset=["OACI", "METAR"])

st.divider()
st.subheader("📊 Historial de Trazabilidad")
st.dataframe(st.session_state.historial.tail(10), use_container_width=True)
