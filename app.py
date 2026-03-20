import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Monitor FIR SAVC", page_icon="✈️", layout="wide")

# CSS "OPERATIVO TOTAL": Mantiene la flecha y oculta la basura de admin
st.markdown("""
    <style>
    header[data-testid="stHeader"], footer, .stDeployButton, .stDocstring { display: none !important; visibility: hidden !important; }
    [data-testid="stSidebarCollapsedControl"] {
        display: flex !important; position: fixed !important; top: 15px !important; left: 15px !important;
        z-index: 9999999 !important; background-color: rgba(100, 100, 100, 0.4) !important;
        border-radius: 8px !important; padding: 5px !important; color: white !important;
    }
    .block-container { padding-top: 3.5rem !important; }
    .stExpander { border: 1px solid #30363d !important; background-color: rgba(13, 17, 23, 0.8) !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Panel de Control")
    tema = st.selectbox("Modo de Pantalla:", ["Sistema", "Día", "Noche"], index=0)
    st.divider()
    with st.expander("🔍 Criterios SMN Activos", expanded=False):
        st.write("**Viento:** G ≥ 10kt.")
        st.write("**Visibilidad:** ≤ 3000m.")
        st.write("**Techo:** BKN/OVC ≤ 1000ft.")
        st.write("**Fenómenos:** TS, RA, DZ, SN, FG, BR, VA.")
    st.divider()
    st.info("🔄 Sincronización: 30 min.")
    st.caption("📍 Comodoro Rivadavia - Argentina")

# --- 3. LÓGICA DE ANÁLISIS MEJORADA ---
API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

st_autorefresh(interval=1800000, key="refresh_v6_smn")

if 'historial' not in st.session_state:
    st.session_state.historial = pd.DataFrame(columns=["Fecha_Hora", "OACI", "METAR", "Alerta"])

def analizar_enmienda(metar_txt):
    alertas = []
    iconos_lista = []
    
    # VIENTO (G)
    if re.search(r'G(\d{2})', metar_txt):
        alertas.append("RAFAGAS")
        iconos_lista.append("⚠️")
    
    # TORMENTA (TS)
    if "TS" in metar_txt:
        alertas.append("TORMENTA")
        iconos_lista.append("⛈️")
        
    # VISIBILIDAD (Detecta si es <= 3000)
    vis_match = re.search(r' (\d{4}) ', metar_txt)
    if vis_match:
        if int(vis_match.group(1)) <= 3000:
            alertas.append("BAJA VIS.")
            iconos_lista.append("🌫️")

    # LLUVIA / NIEVE / OTROS (Ajustado para detectar +/- o VCSH)
    # Buscamos RA (Lluvia), DZ (Llovizna), SN (Nieve), FG (Niebla), BR (Neblina), VA (Ceniza)
    if any(f in metar_txt for f in ["RA", "DZ", "SN", "FG", "BR", "VA", "PL", "GR"]):
        if "BAJA VIS." not in alertas: # Para no repetir icono si ya hay visibilidad baja
            alertas.append("FENOMENO")
            iconos_lista.append("🌧️")
            
    # TECHO DE NUBES (BKN/OVC <= 1000ft)
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
st.write(f"Vigilancia Activa | Sincronización: **{ahora}**")

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
        Desarrollado por <b>Gemini AI</b> & <b>RICARTEZ ANIBAL</b><br>
        <i>Basado en Criterios de Enmienda TAF - SMN.</i>
    </div>
    """, 
    unsafe_allow_html=True
)
