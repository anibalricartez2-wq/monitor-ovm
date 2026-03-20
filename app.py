import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Monitor FIR SAVC", 
    page_icon="✈️", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS "OPERATIVO TOTAL": Forzamos la aparición del botón y el modo oscuro
st.markdown("""
    <style>
    /* 1. OCULTAR HEADER Y BASURA DE ADMIN */
    header[data-testid="stHeader"], footer, .stDeployButton, .stDocstring { 
        display: none !important; 
    }
    
    /* 2. FORZAR MODO NOCHE DESDE EL CÓDIGO (BACKEND) */
    .stApp {
        background-color: #0e1117 !important;
        color: #fafafa !important;
    }

    /* 3. RESCATE AGRESIVO DEL BOTÓN DEL MENÚ */
    /* Lo convertimos en un botón flotante circular independiente */
    [data-testid="stSidebarCollapsedControl"] {
        display: flex !important;
        position: fixed !important;
        top: 15px !important;
        left: 15px !important;
        z-index: 9999999 !important;
        background-color: #262730 !important;
        border: 2px solid #4f8bf9 !important; /* Color azul para que lo encuentres fácil */
        border-radius: 50% !important;
        width: 50px !important;
        height: 50px !important;
        justify-content: center !important;
        align-items: center !important;
        box-shadow: 0px 0px 15px rgba(0,0,0,0.8) !important;
        cursor: pointer !important;
    }

    /* Ajuste de márgenes para el contenido */
    .block-container { padding-top: 4.5rem !important; }
    .stExpander { border: 1px solid #30363d !important; background-color: #161b22 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BARRA LATERAL (CONTROL Y CRITERIOS) ---
with st.sidebar:
    st.header("⚙️ Configuración")
    st.write("Vigilancia basada en manual SMN.")
    
    st.divider()
    with st.expander("🔍 Criterios de Enmienda", expanded=False):
        st.write("**Viento:** Δ 10kt o G ≥ 10kt.")
        st.write("**Visibilidad:** ≤ 3000m (Puntos d, e, f).")
        st.write("**Techo:** BKN/OVC ≤ 1000ft (Puntos i, j).")
        st.write("**Fenómenos:** RA, DZ, SN, TS, FG, BR, VA.")
    
    st.divider()
    st.caption("📍 Comodoro Rivadavia")

# --- 3. LÓGICA DE DATOS ---
API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

st_autorefresh(interval=1800000, key="refresh_v8_definitivo")

if 'historial' not in st.session_state:
    st.session_state.historial = pd.DataFrame(columns=["Fecha_Hora", "OACI", "METAR", "Alerta"])

def analizar_enmienda(metar_txt):
    alertas = []
    iconos_lista = []
    
    # Viento
    if re.search(r'G(\d{2})', metar_txt):
        alertas.append("RAFAGAS")
        iconos_lista.append("⚠️")
    
    # Tormenta
    if "TS" in metar_txt:
        alertas.append("TORMENTA")
        iconos_lista.append("⛈️")
        
    # Visibilidad (Umbral 3000m)
    vis_match = re.search(r' (\d{4}) ', metar_txt)
    if vis_match and int(vis_match.group(1)) <= 3000:
        alertas.append("BAJA VIS.")
        iconos_lista.append("🌫️")

    # Fenómenos (RA, DZ, etc.)
    if any(f in metar_txt for f in ["RA", "DZ", "SN", "FG", "BR", "VA"]):
        if "BAJA VIS." not in alertas:
            alertas.append("FENOMENO")
            iconos_lista.append("🌧️")
            
    # Techo
    if any(n in metar_txt for n in ["BKN00", "OVC00", "BKN010", "OVC010"]):
        alertas.append("TECHO BAJO")
        iconos_lista.append("☁️")
    
    estado = ", ".join(alertas) if alertas else "NORMAL"
    icon_final = iconos_lista[0] if iconos_lista else "✅"
    return estado, icon_final

def obtener_datos():
    icaos = ",".join(AERODROMOS)
    headers = {"X-API-Key": API_KEY}
    try:
        m = requests.get(f"https://api.checkwx.com/metar/{icaos}", headers=headers).json().get('data', [])
        t = requests.get(f"https://api.checkwx.com/taf/{icaos}", headers=headers).json().get('data', [])
        return m, t
    except: return [], []

# --- 4. INTERFAZ ---
st.title("🖥️ Monitor de Vigilancia FIR SAVC")
ahora = datetime.now().strftime('%H:%M:%S')
st.write(f"Estado: **Operativo** | Actualización: **{ahora}**")

metars, tafs = obtener_datos()
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
    estado, icono = analizar_enmienda(info["metar"])
    with cols[i % 2]:
        with st.expander(f"{icono} {icao} - {estado}", expanded=True):
            st.markdown("**METAR**")
            st.code(info["metar"])
            st.markdown("**TAF**")
            st.code(info["taf"])
            if "SAV" in info["metar"] and "Sin datos" not in info["metar"]:
                nueva = pd.DataFrame([{"Fecha_Hora": ahora, "OACI": icao, "METAR": info["metar"], "Alerta": estado}])
                st.session_state.historial = pd.concat([st.session_state.historial, nueva], ignore_index=True).drop_duplicates(subset=["OACI", "METAR"])

st.divider()
st.subheader("📊 Historial de Trazabilidad")
st.dataframe(st.session_state.historial.tail(10), use_container_width=True)

# CRÉDITOS
st.markdown(
    f"""
    <div style='text-align: center; color: #8b949e; font-size: 0.85rem; border-top: 1px solid #30363d; padding-top: 20px;'>
        <b>Sistema de Vigilancia FIR SAVC © 2026</b><br>
        Desarrollado por <b>Gemini AI</b> & <b>Ferreira</b><br>
        <i>Control de Enmiendas TAF - SMN
