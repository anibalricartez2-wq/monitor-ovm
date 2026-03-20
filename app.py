import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN DE PÁGINA Y TEMA ---
st.set_page_config(
    page_title="Monitor FIR SAVC", 
    page_icon="✈️", 
    layout="wide",
    initial_sidebar_state="collapsed" # Empieza cerrado para ganar espacio
)

# CSS "RESCATE TOTAL": Asegura que la flecha sea visible y el fondo sea oscuro
st.markdown("""
    <style>
    /* 1. OCULTAR EL HEADER ORIGINAL (DONDE ESTÁ EL MENÚ DE CÓDIGO) */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    
    /* 2. CREAR UN BOTÓN FLOTANTE PARA EL MENÚ (FLECHA) */
    /* Esto hace que la flecha sea un círculo gris arriba a la izquierda */
    [data-testid="stSidebarCollapsedControl"] {
        display: flex !important;
        position: fixed !important;
        top: 20px !important;
        left: 20px !important;
        z-index: 9999999 !important;
        background-color: #262730 !important;
        border: 1px solid #464b5d !important;
        border-radius: 50% !important;
        width: 45px !important;
        height: 45px !important;
        justify-content: center !important;
        align-items: center !important;
        color: white !important;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.5) !important;
    }

    /* 3. FORZAR FONDO OSCURO SIEMPRE (MODO NOCHE) */
    .stApp {
        background-color: #0e1117 !important;
        color: #fafafa !important;
    }

    /* Ajuste de márgenes para no tapar el título */
    .block-container { 
        padding-top: 4rem !important; 
    }
    
    /* Estética de las tarjetas de aeródromos */
    .stExpander { 
        border: 1px solid #30363d !important; 
        background-color: #161b22 !important; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BARRA LATERAL (CONTROL) ---
with st.sidebar:
    st.header("⚙️ Panel de Control")
    st.info("El sistema está configurado según el Manual de Enmiendas TAF del SMN.")
    
    st.divider()
    with st.expander("🔍 Criterios Activos", expanded=False):
        st.write("**Viento:** Ráfagas ≥ 10kt.")
        st.write("**Visibilidad:** ≤ 3000m.")
        st.write("**Techo:** BKN/OVC ≤ 1000ft.")
        st.write("**Fenómenos:** Todos los del PDF.")
    
    st.divider()
    st.caption("📍 Comodoro Rivadavia - Argentina")

# --- 3. LÓGICA DE DATOS ---
API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

st_autorefresh(interval=1800000, key="refresh_v7_final")

if 'historial' not in st.session_state:
    st.session_state.historial = pd.DataFrame(columns=["Fecha_Hora", "OACI", "METAR", "Alerta"])

def analizar_enmienda(metar_txt):
    alertas = []
    iconos_lista = []
    
    if re.search(r'G(\d{2})', metar_txt):
        alertas.append("RAFAGAS")
        iconos_lista.append("⚠️")
    
    if "TS" in metar_txt:
        alertas.append("TORMENTA")
        iconos_lista.append("⛈️")
        
    vis_match = re.search(r' (\d{4}) ', metar_txt)
    if vis_match and int(vis_match.group(1)) <= 3000:
        alertas.append("BAJA VIS.")
        iconos_lista.append("🌫️")

    if any(f in metar_txt for f in ["RA", "DZ", "SN", "FG", "BR", "VA", "PL", "GR"]):
        if "BAJA VIS." not in alertas:
            alertas.append("FENOMENO")
            iconos_lista.append("🌧️")
            
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
st.write(f"Vigilancia Operativa | Actualizado: **{ahora}**")

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
        Desarrollado por <b>Gemini AI</b> & <b>ANIBAL RICARTEZ</b><br>
        <i>Criterios de Enmienda TAF - SMN. SISTEMA EN PRUEBA</i>
    </div>
    """, 
    unsafe_allow_html=True
)
