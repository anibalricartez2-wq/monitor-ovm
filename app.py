import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Monitor FIR SAVC", page_icon="✈️", layout="wide")

# CSS "OPERATIVO TOTAL": Recupera la flecha y mata el menú de código
st.markdown("""
    <style>
    /* 1. Ocultar el Header original, Footer y Documentación */
    header[data-testid="stHeader"], footer, .stDeployButton, .stDocstring { 
        display: none !important; 
        visibility: hidden !important;
    }
    
    /* 2. RESCATAR LA FLECHA (BOTÓN DEL SIDEBAR) */
    /* La sacamos del header y la fijamos en la esquina superior izquierda */
    [data-testid="stSidebarCollapsedControl"] {
        display: flex !important;
        position: fixed !important;
        top: 15px !important;
        left: 15px !important;
        z-index: 9999999 !important;
        background-color: rgba(100, 100, 100, 0.4) !important;
        border-radius: 8px !important;
        padding: 5px !important;
        color: white !important;
        cursor: pointer !important;
    }

    /* 3. Ajuste de la pantalla para que no se corte el título */
    .block-container { 
        padding-top: 3.5rem !important; 
    }

    /* Estética de las tarjetas de aeródromos */
    .stExpander { 
        border: 1px solid #30363d !important; 
        background-color: rgba(13, 17, 23, 0.8) !important; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BARRA LATERAL (CONTROL Y CRITERIOS) ---
with st.sidebar:
    st.header("⚙️ Panel de Control")
    # Aquí puedes cambiar el tema de Sistema/Día/Noche
    tema = st.selectbox("Modo de Pantalla:", ["Sistema", "Día", "Noche"], index=0)
    
    st.divider()
    with st.expander("🔍 Criterios de Enmienda (SMN)", expanded=False):
        st.write("**Viento:** Δ Dir ≥ 60° | Δ Vel ≥ 10kt | Ráfaga Δ ≥ 10kt.")
        st.write("**Visibilidad:** Cruce de 150, 350, 600, 800, 1500 o 3000m.")
        st.write("**Techo (BKN/OVC):** Cruce de 100, 200, 500, 1000 o 1500ft.")
        st.caption("Fuente: Criterios Enmienda TAF - SMN.")
    
    st.divider()
    st.info("🔄 Sincronización: Cada 30 min.")
    st.caption("📍 Comodoro Rivadavia - Argentina")

# --- 3. LÓGICA DE DATOS Y ANÁLISIS ---
API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

# Refresco automático cada 30 minutos
st_autorefresh(interval=1800000, key="refresh_final_v5")

if 'historial' not in st.session_state:
    st.session_state.historial = pd.DataFrame(columns=["Fecha_Hora", "OACI", "METAR", "Alerta"])

def analizar_enmienda(metar_txt):
    alertas = []
    iconos_lista = []
    
    # Viento/Ráfagas
    if re.search(r'G(\d{2})', metar_txt):
        alertas.append("RAFAGAS")
        iconos_lista.append("⚠️")
    
    # Tormentas
    if "TS" in metar_txt:
        alertas.append("TORMENTA")
        iconos_lista.append("⛈️")
        
    # Visibilidad (Umbral 3000m del manual)
    if any(f in metar_txt for f in ["FG", "BR", "DZ", "RA", "SN"]):
        vis_match = re.search(r' (\d{4}) ', metar_txt)
        if vis_match and int(vis_match.group(1)) <= 3000:
            alertas.append("BAJA VIS.")
            iconos_lista.append("🌫️")
            
    # Techo de nubes (Umbral 1000ft del manual)
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
st.write(f"Vigilancia Activa | Actualizado: **{ahora}**")

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
st.subheader("📊 Historial de Trazabilidad (Últimos movimientos)")
st.dataframe(st.session_state.historial.tail(10), use_container_width=True)

# CRÉDITOS FINALES
st.markdown(
    f"""
    <div style='text-align: center; color: #8b949e; font-size: 0.85rem; border-top: 1px solid #30363d; padding-top: 20px; margin-top: 30px;'>
        <b>Sistema de Vigilancia FIR SAVC © 2026</b><br>
        Desarrollado por <b>Gemini AI</b> & <b>RICARTEZ ANIBAL</b><br>
        <i>Basado en Criterios de Enmienda TAF del Servicio Meteorológico Nacional.</i>
    </div>
    """, 
    unsafe_allow_html=True
)
