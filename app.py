import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Monitor FIR SAVC", page_icon="✈️", layout="wide")

# CSS "OPERATIVO FINAL": Bloquea menús de administrador y libera la flecha de configuración
st.markdown("""
    <style>
    /* Ocultar Menús, Footer y Documentación técnica */
    #MainMenu, footer, .stDeployButton, .stDocstring, [data-testid="stDocstring"] {
        display: none !important;
        visibility: hidden !important;
    }

    /* MATAR LOS BOTONES DE CÓDIGO (DERECHA) SIN ROMPER LA FLECHA */
    [data-testid="stHeaderActionElements"] {
        opacity: 0 !important;
        pointer-events: none !important;
        display: none !important;
    }

    /* RESCATE DE LA FLECHA DEL MENÚ LATERAL (IZQUIERDA) */
    [data-testid="stSidebarCollapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        z-index: 1000001 !important;
        background-color: rgba(151, 166, 195, 0.2) !important;
        border-radius: 5px !important;
        padding: 4px !important;
    }

    /* Estética de tarjetas y márgenes */
    .block-container { padding-top: 2.5rem !important; }
    .stExpander { border: 1px solid #30363d !important; background-color: #0d1117 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BARRA LATERAL (CONFIGURACIÓN Y CRITERIOS) ---
with st.sidebar:
    st.header("⚙️ Panel de Control")
    tema = st.selectbox("Modo de Pantalla:", ["Sistema", "Día", "Noche"], index=0)
    
    st.divider()
    with st.expander("🔍 Ver Criterios de Alerta", expanded=False):
        st.write("**Ráfagas:** Detecta 'G' + 2 dígitos.")
        st.write("**Tormentas:** Detecta 'TS' en METAR.")
        st.write("**Visibilidad:** Detecta 'FG' o 'BR'.")
        st.caption("Filtros basados en normativa MAPROMA.")
    
    st.divider()
    st.info("🔄 Sincronización: Cada 30 min.")
    st.caption("📍 Comodoro Rivadavia - Argentina")

# --- 3. LÓGICA DE DATOS ---
API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

# REFRESH CONFIGURADO A 30 MINUTOS
st_autorefresh(interval=1800000, key="refresh_definitivo_savc")

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
    if "FG" in metar_txt or "BR" in metar_txt: return "VISIBILIDAD", "🌫️"
    return "NORMAL", "✅"

# --- 4. INTERFAZ ---
st.title("🖥️ Monitor de Vigilancia FIR SAVC")
ahora = datetime.now().strftime('%H:%M:%S')
st.write(f"Estado: **Operativo** | Actualizado: **{ahora}**")

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
st.subheader("📊 Historial Operativo de Trazabilidad")
st.dataframe(st.session_state.historial.tail(10), use_container_width=True)

# DERECHOS DE AUTOR - CRÉDITOS FINALES
st.markdown(
    f"""
    <div style='text-align: center; color: #8b949e; font-size: 0.85rem; border-top: 1px solid #30363d; padding-top: 20px;'>
        <b>Sistema de Vigilancia FIR SAVC © 2026</b><br>
        Desarrollado por <b>Gemini AI</b> & <b>Ferreira</b><br>
        <i>Comodoro Rivadavia, Argentina. Todos los derechos reservados.</i>
    </div>
    """, 
    unsafe_allow_html=True
)
