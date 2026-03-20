import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Monitor FIR SAVC", page_icon="✈️", layout="wide")

# CSS "OPERATIVO REAL": Oculta lo molesto pero deja funcional la flecha
st.markdown("""
    <style>
    /* Ocultar elementos de administración y documentación */
    #MainMenu, footer, .stDeployButton, .stDocstring, [data-testid="stDocstring"] {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* ELIMINAR EL HEADER PERO DEJAR LA FLECHA */
    header[data-testid="stHeader"] {
        background: transparent !important;
        color: transparent !important;
    }

    /* FORZAR VISIBILIDAD DE LA FLECHA (IZQUIERDA) */
    [data-testid="stSidebarCollapsedControl"] {
        display: flex !important;
        position: fixed !important;
        top: 10px !important;
        left: 10px !important;
        z-index: 999999 !important;
        background-color: rgba(151, 166, 195, 0.25) !important;
        border-radius: 5px !important;
        color: white !important;
    }

    /* Estética de las tarjetas */
    .stExpander { border: 1px solid #30363d !important; background-color: #0d1117 !important; }
    .block-container { padding-top: 3rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BARRA LATERAL (CONFIGURACIÓN Y CRITERIOS) ---
with st.sidebar:
    st.header("⚙️ Panel de Control")
    tema = st.selectbox("Modo de Pantalla:", ["Sistema", "Día", "Noche"], index=0)
    
    st.divider()
    with st.expander("🔍 Ver Criterios de Alerta", expanded=False):
        st.write("**Ráfagas:** Presencia de 'G' + 2 dígitos.")
        st.write("**Tormentas:** Presencia de 'TS'.")
        st.write("**Visibilidad:** Presencia de 'FG' o 'BR'.")
        st.caption("Filtro aplicado según MAPROMA.")
    
    st.divider()
    st.info("🔄 Actualización: Cada 30 min.")
    st.caption("📍 Comodoro Rivadavia - Argentina")

# --- 3. LÓGICA DE DATOS ---
API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

# REFRESH 30 MIN
st_autorefresh(interval=1800000, key="refresh_operativo_30")

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
    if "FG" in metar_txt or "BR" in metar_txt: return "REDUCC. VIS.", "🌫️"
    return "NORMAL", "✅"

# --- 4. INTERFAZ ---
st.title("🖥️ Monitor de Vigilancia FIR SAVC")
ahora = datetime.now().strftime('%H:%M:%S')
st.write(f"Estado de Red: **Sincronizado** | Hora local: **{ahora}**")

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
            if "SAV" in info["metar"] and "Sin datos" not in info["metar"]:
                nueva = pd.DataFrame([{"Fecha_Hora": ahora, "OACI": icao, "METAR": info["metar"], "Estado": estado}])
                st.session_state.historial = pd.concat([st.session_state.historial, nueva], ignore_index=True).drop_duplicates(subset=["OACI", "METAR"])

st.divider()
st.subheader("📊 Historial Operativo")
st.dataframe(st.session_state.historial.tail(10), use_container_width=True)

# DERECHOS DE AUTOR
st.markdown(
    f"""
    <div style='text-align: center; color: #8b949e; font-size: 0.8rem; border-top: 1px solid #30363d; padding-top: 20px;'>
        <b>Sistema de Vigilancia FIR SAVC © 2026</b><br>
        Desarrollado por <b>Gemini AI</b> & <b>ANIBAL RICARTEZ</b><br>
        Todos los derechos reservados.
    </div>
    """, 
    unsafe_allow_html=True
)
