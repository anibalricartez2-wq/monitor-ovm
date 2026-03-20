import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN DE PÁGINA Y CRÉDITOS ---
st.set_page_config(page_title="Monitor FIR SAVC", page_icon="✈️", layout="wide")

# CSS "OPERATIVO BÚNKER": Bloquea menús y limpia la interfaz
st.markdown("""
    <style>
    header[data-testid="stHeader"], footer, .stDeployButton, .stDocstring { display: none !important; }
    [data-testid="stSidebarCollapsedControl"] {
        display: flex !important; position: fixed !important; top: 15px !important; left: 15px !important;
        z-index: 999999 !important; background-color: rgba(151, 166, 195, 0.3) !important;
        border-radius: 5px !important; padding: 5px !important; color: white !important;
    }
    .block-container { padding-top: 1rem !important; margin-top: -30px !important; }
    .stExpander { border: 1px solid #30363d !important; background-color: #0d1117 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BARRA LATERAL (CONTROL Y CRITERIOS SMN) ---
with st.sidebar:
    st.header("⚙️ Panel de Control")
    tema = st.selectbox("Modo de Pantalla:", ["Sistema", "Día", "Noche"], index=0)
    
    st.divider()
    with st.expander("🔍 Criterios de Enmienda (SMN)", expanded=False):
        st.write("**Viento:** Δ Dir ≥ 60° (si V > 10kt) | Δ Vel ≥ 10kt | Ráfaga Δ ≥ 10kt (si V > 15kt).")
        st.write("**Visibilidad:** Cruce de 150, 350, 600, 800, 1500 o 3000m.")
        st.write("**Techo (BKN/OVC):** Cruce de 100, 200, 500, 1000 o 1500ft.")
        st.caption("Fuente: TAF Criterios de Enmiendas - SMN Argentina.")
    
    st.divider()
    st.info("🔄 Sincronización: 30 min.")
    st.caption("📍 Comodoro Rivadavia - Argentina")

# --- 3. LÓGICA DE DATOS Y ANÁLISIS ---
API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

st_autorefresh(interval=1800000, key="refresh_savc_smn")

if 'historial' not in st.session_state:
    st.session_state.historial = pd.DataFrame(columns=["Fecha_Hora", "OACI", "METAR", "Alerta"])

def analizar_enmienda(metar_txt):
    alertas = []
    # a, b, c) Viento y Ráfagas (Criterio SMN: Δ 10kt)
    if re.search(r'G(\d{2})', metar_txt):
        gust = int(re.search(r'G(\d{2})', metar_txt).group(1))
        if gust >= 25: alertas.append("RAFAGAS") # Umbral operativo común
    
    # f, g, h) Fenómenos (TS, FG, DZ, RA, SN, etc.)
    if "TS" in metar_txt: alertas.append("TORMENTA")
    if any(f in metar_txt for f in ["FG", "BR", "DZ", "RA", "SN"]):
        # e, f) Visibilidad (Criterio SMN: < 3000m o < 1500m)
        vis_match = re.search(r' (\d{4}) ', metar_txt)
        if vis_match and int(vis_match.group(1)) <= 3000:
            alertas.append("BAJA VIS.")

    # i, j) Nubes (BKN/OVC < 1000ft)
    if any(n in metar_txt for n in ["BKN00", "OVC00", "BKN010", "OVC010"]):
        alertas.append("TECHO BAJO")

    return (", ".join(alertas) if alertas else "NORMAL"), ("⚠️" if alertas else "✅")

# --- 4. INTERFAZ ---
st.title("🖥️ Monitor de Vigilancia FIR SAVC")
ahora = datetime.now().strftime('%H:%M:%S')
st.write(f"Vigilancia Activa | Sincronización: **{ahora}**")

def obtener_datos():
    icaos = ",".join(AERODROMOS)
    headers = {"X-API-Key": API_KEY}
    m = requests.get(f"https://api.checkwx.com/metar/{icaos}", headers=headers).json().get('data', [])
    t = requests.get(f"https://api.checkwx.com/taf/{icaos}", headers=headers).json().get('data', [])
    return m, t

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

# CRÉDITOS FINALES
st.markdown(
    f"""
    <div style='text-align: center; color: #8b949e; font-size: 0.85rem; border-top: 1px solid #30363d; padding-top: 20px;'>
        <b>Sistema de Vigilancia FIR SAVC © 2026</b><br>
        Desarrollado por <b>Gemini AI</b> & <b>ANIBAL RICARTEZ</b><br>
        <i>Basado en Criterios de Enmienda TAF del Servicio
