import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Monitor FIR SAVC", page_icon="✈️", layout="wide")

# CSS "BÚNKER": Oculta todo lo que no sea el contenido, incluyendo documentación inyectada
st.markdown("""
    <style>
    /* Ocultar Menús, Footer y cualquier decoración de Streamlit */
    #MainMenu, footer, .stDeployButton, header {display: none !important; visibility: hidden !important;}
    
    /* Bloquear cualquier inyección de texto de ayuda/documentación al final */
    .stDocstring, [data-testid="stDocstring"] {display: none !important;}

    /* RESCATE DE LA FLECHA LATERAL */
    [data-testid="stSidebarCollapsedControl"] {
        display: flex !important;
        position: fixed !important;
        top: 15px !important;
        left: 15px !important;
        z-index: 1000000 !important;
        background-color: rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
        padding: 5px !important;
        cursor: pointer !important;
    }

    /* Limpieza de fondo y márgenes */
    .main {background-color: #0e1117 !important;}
    .block-container {padding-top: 2rem !important; padding-bottom: 2rem !important;}
    
    /* Estilo de tarjetas */
    .stExpander {border: 1px solid #30363d !important; background-color: #161b22 !important;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. BARRA LATERAL (PANTALLA) ---
with st.sidebar:
    st.header("⚙️ Configuración")
    tema = st.selectbox("Modo de Pantalla:", ["Sistema", "Día", "Noche"], index=0)
    st.divider()
    st.info("🔄 Ciclo de Sincronización: 30 min.")
    st.caption("🔒 Uso Exclusivo Operativo")

# --- 3. LÓGICA DE DATOS ---
API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

# REFRESH CADA 30 MINUTOS
st_autorefresh(interval=1800000, key="refresh_final_30m")

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
    if re.search(r'G\d{2}', metar_txt): return "RAFAGAS", "⚠️"
    if "TS" in metar_txt: return "TORMENTA", "⛈️"
    return "NORMAL", "✅"

# --- 4. INTERFAZ ---
st.title("🖥️ Monitor de Vigilancia FIR SAVC")
ahora = datetime.now().strftime('%H:%M:%S')
st.caption(f"Sincronizado: **{ahora}** | Comodoro Rivadavia")

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
    estado, icono = analizar_alerta(info["metar"])
    with cols[i % 2]:
        with st.expander(f"{icono} {icao} - {estado}", expanded=True):
            st.markdown("**METAR**")
            st.code(info["metar"])
            st.markdown("**TAF**")
            st.code(info["taf"])
            if "SAV" in info["metar"]:
                nueva = pd.DataFrame([{"Fecha_Hora": ahora, "OACI": icao, "METAR": info["metar"], "Estado": estado}])
                st.session_state.historial = pd.concat([st.session_state.historial, nueva], ignore_index=True).drop_duplicates(subset=["OACI", "METAR"])

st.divider()
st.subheader("📊 Historial Operativo")
st.dataframe(st.session_state.historial.tail(10), use_container_width=True)

# DERECHOS DE AUTOR - PIE DE PÁGINA
st.markdown(
    f"""
    <div style='text-align: center; color: #8b949e; font-size: 0.8rem; margin-top: 50px; border-top: 1px solid #30363d; padding-top: 20px;'>
        <b>Monitor Vigilancia FIR SAVC © 2026</b><br>
        Desarrollado por <b>Gemini AI</b> & <b>ANIBAL RICARTEZ</b><br>
        <i>Comodoro Rivadavia, Argentina</i>
    </div>
    """, 
    unsafe_allow_html=True
)
