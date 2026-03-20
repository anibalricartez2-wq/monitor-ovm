import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Monitor FIR SAVC", layout="wide")

# --- 2. CSS DE RESCATE (FORZADO TOTAL) ---
st.markdown("""
    <style>
    /* Ocultar basura de admin */
    header, footer, .stDeployButton { display: none !important; }

    /* Forzar fondo oscuro */
    .stApp { background-color: #0e1117 !important; color: #fafafa !important; }

    /* BOTÓN FLOTANTE MANUAL (El círculo azul) */
    .boton-menu {
        position: fixed;
        top: 20px;
        left: 20px;
        width: 50px;
        height: 50px;
        background-color: #4f8bf9;
        color: white;
        border-radius: 50%;
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999999;
        cursor: pointer;
        font-size: 24px;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.5);
    }
    
    /* Mostrar la flecha de Streamlit a toda costa */
    [data-testid="stSidebarCollapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        position: fixed !important;
        top: 20px !important;
        left: 20px !important;
        background: #262730 !important;
        border: 2px solid #4f8bf9 !important;
        z-index: 1000000 !important;
        border-radius: 50% !important;
    }

    .block-container { padding-top: 5rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Configuración")
    st.write("Vigilancia FIR SAVC")
    st.divider()
    st.info("Criterios de Enmienda SMN Activos.")
    st.caption("📍 Comodoro Rivadavia")

# --- 4. MOTOR DE DATOS ---
API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

st_autorefresh(interval=1800000, key="refresh_final_smn")

if 'historial' not in st.session_state:
    st.session_state.historial = pd.DataFrame(columns=["Hora", "OACI", "METAR", "Alerta"])

def analizar(metar_txt):
    alertas = []
    iconos = []
    if re.search(r'G(\d{2})', metar_txt): alertas.append("RAFAGAS"); iconos.append("⚠️")
    if "TS" in metar_txt: alertas.append("TORMENTA"); iconos.append("⛈️")
    vis = re.search(r' (\d{4}) ', metar_txt)
    if vis and int(vis.group(1)) <= 3000: alertas.append("BAJA VIS."); iconos.append("🌫️")
    if any(f in metar_txt for f in ["RA", "DZ", "SN", "FG", "BR"]): 
        if "BAJA VIS." not in alertas: alertas.append("FENOMENO"); iconos.append("🌧️")
    if any(n in metar_txt for n in ["BKN00", "OVC00", "BKN010", "OVC010"]): alertas.append("TECHO BAJO"); iconos.append("☁️")
    return (", ".join(alertas) if alertas else "NORMAL"), (iconos[0] if iconos else "✅")

# --- 5. INTERFAZ ---
st.title("🖥️ Monitor de Vigilancia FIR SAVC")
ahora = datetime.now().strftime('%H:%M:%S')
st.write(f"Vigilancia Operativa | **{ahora}**")

# Obtener datos de la API
try:
    headers = {"X-API-Key": API_KEY}
    m_data = requests.get(f"https://api.checkwx.com/metar/{','.join(AERODROMOS)}", headers=headers).json().get('data', [])
    t_data = requests.get(f"https://api.checkwx.com/taf/{','.join(AERODROMOS)}", headers=headers).json().get('data', [])
except: m_data, t_data = [], []

datos = {icao: {"m": "Sin datos", "t": "Sin datos"} for icao in AERODROMOS}
for m in m_data:
    for icao in AERODROMOS:
        if icao in m: datos[icao]["m"] = m
for t in t_data:
    for icao in AERODROMOS:
        if icao in t: datos[icao]["t"] = t

cols = st.columns(2)
for i, icao in enumerate(AERODROMOS):
    info = datos[icao]
    estado, icono = analizar(info["m"])
    with cols[i % 2]:
        with st.expander(f"{icono} {icao} - {estado}", expanded=True):
            st.code(f"METAR: {info['m']}\n\nTAF: {info['t']}")
            if "SAV" in info["m"] and "Sin datos" not in info["m"]:
                nueva = pd.DataFrame([{"Hora": ahora, "OACI": icao, "METAR": info["m"], "Alerta": estado}])
                st.session_state.historial = pd.concat([st.session_state.historial, nueva], ignore_index=True).drop_duplicates(subset=["OACI", "METAR"])

st.divider()
st.subheader("📊 Historial")
st.dataframe(st.session_state.historial.tail(10), use_container_width=True)

# CRÉDITOS SIMPLES (Sin f-strings complejos para evitar SyntaxError)
st.markdown("<br><hr><center><b>Monitor FIR SAVC © 2026</b><br>Ferreira & Gemini AI</center>", unsafe_allow_html=True)
