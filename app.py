import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Monitor FIR SAVC", page_icon="✈️", layout="wide")

# JS: Script para limpiar la interfaz de botones de edición/GitHub
components.html("""
    <script>
    function hideAdmin() {
        const toHide = ['[data-testid="stHeaderActionElements"]', '#MainMenu', '.stDeployButton', 'header'];
        toHide.forEach(s => {
            const el = window.parent.document.querySelectorAll(s);
            el.forEach(e => e.style.display = 'none');
        });
    }
    setInterval(hideAdmin, 1000);
    </script>
    """, height=0)

# CSS: Estética profesional y rescate de la flecha lateral
st.markdown("""
    <style>
    footer {visibility: hidden !important;}
    
    /* Botón de Menú Lateral (Flecha) */
    [data-testid="stSidebarCollapsedControl"] {
        display: flex !important;
        position: fixed !important;
        top: 15px !important;
        left: 15px !important;
        z-index: 1000000 !important;
        background-color: rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
        padding: 5px !important;
    }

    /* Estilo de las tarjetas de aeródromos */
    .stExpander {
        border: 1px solid #30363d !important;
        border-radius: 10px !important;
        background-color: #0d1117 !important;
    }

    .block-container {padding-top: 3rem !important;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. BARRA LATERAL (CONFIGURACIÓN) ---
with st.sidebar:
    st.header("⚙️ Configuración")
    tema = st.selectbox("Modo de Pantalla:", ["Sistema", "Día", "Noche"], index=0)
    st.divider()
    st.info("🔄 Sincronización: Cada 30 min.")
    st.warning("⚠️ Uso exclusivo operativo.")

# --- 3. CONFIGURACIÓN TÉCNICA ---
API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

# REFRESH CADA 30 MINUTOS
st_autorefresh(interval=1800000, key="refresh_30m_final")

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
        return "RAFAGAS", "⚠️"
    if "TS" in metar_txt:
        return "TORMENTA", "⛈️"
    if "FG" in metar_txt or "BR" in metar_txt:
        return "VISIBILIDAD", "🌫️"
    return "NORMAL", "✅"

# --- 4. INTERFAZ PRINCIPAL ---
st.title("🖥️ Monitor de Vigilancia FIR SAVC")
ahora = datetime.now().strftime('%H:%M:%S')
st.caption(f"Última actualización de red: **{ahora}** | Comodoro Rivadavia, Argentina")

metars, tafs = obtener_datos(AERODROMOS)
datos = {icao: {"metar": "Sin datos", "taf": "Sin datos"} for icao in AERODROMOS}
for m in metars:
    for icao in AERODROMOS:
        if icao in m: datos[icao]["metar"] = m
for t in tafs:
    for icao in AERODROMOS:
        if icao in t: datos[icao]["taf"] = t

# Grilla de Aeródromos con Iconos
cols = st.columns(2)
for i, icao in enumerate(AERODROMOS):
    info = datos[icao]
    estado, icono = analizar_alerta(info["metar"])
    
    with cols[i % 2]:
        with st.expander(f"{icono} {icao} - {estado}", expanded=True):
            st.markdown("**METAR**")
            st.code(info["metar"])
            st.markdown("**TAF**")
            st.code(info["taf"])
            
            # Guardar en historial si hay datos reales
            if "SAV" in info["metar"] and "Sin datos" not in info["metar"]:
                nueva = pd.DataFrame([{"Fecha_Hora": ahora, "OACI": icao, "METAR": info["metar"], "Estado": estado}])
                st.session_state.historial = pd.concat([st.session_state.historial, nueva], ignore_index=True).drop_duplicates(subset=["OACI", "METAR"])

st.divider()

# --- 5. HISTORIAL Y CRÉDITOS ---
st.subheader("📊 Historial Operativo de Trazabilidad")
st
